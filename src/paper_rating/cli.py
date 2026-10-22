"""Create a fresh PDF comparison workspace and invoke a headless agent."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid

import pymupdf


PROMPT = Path(__file__).with_name("prompt.txt").read_text(encoding="utf-8")
FOLLOWUP = Path(__file__).with_name("followup.txt").read_text(encoding="utf-8")
EFFORTS = {
    "codex": ("minimal", "low", "medium", "high", "xhigh"),
    "claude": ("low", "medium", "high", "xhigh", "max"),
}
CODEX_SANDBOXES = ("read-only", "danger-full-access")
WORKSPACE_INSTRUCTIONS = "Read AGENTS.md in the current working directory before reviewing the PDFs."


def reference_dir() -> Path:
    """Locate references in either a source checkout or an installed wheel."""
    bundled = Path(__file__).with_name("no_app_pdfs")
    return bundled if bundled.is_dir() else Path(__file__).resolve().parents[2] / "no_app_pdfs"


def pdf_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")


def open_pdf(path: Path) -> pymupdf.Document:
    try:
        doc = pymupdf.open(path)
    except (RuntimeError, ValueError) as exc:
        raise ValueError(f"Cannot read PDF {path}: {exc}") from exc
    if not doc.is_pdf or doc.needs_pass or not len(doc):
        doc.close()
        raise ValueError(f"Expected a nonempty, unencrypted PDF: {path}")
    return doc


def prepare_run(paper: Path, pages: int | None, references: Path, output_root: Path | None = None) -> Path:
    """Copy pages 1..N (inclusive), link references, and prepare readable assets."""
    if not paper.is_file():
        raise ValueError(f"Paper does not exist: {paper}")
    if pages is not None and pages < 1:
        raise ValueError("--pages must be a positive page number")
    if not references.is_dir():
        raise ValueError(f"Reference directory does not exist: {references}")
    refs = pdf_files(references)
    if not refs:
        raise ValueError(f"No reference PDFs in {references}")
    # Validate all inputs before creating a run directory.
    for ref in refs:
        with open_pdf(ref):
            pass
    with open_pdf(paper) as source:
        count = len(source) if pages is None else pages
        if count > len(source):
            raise ValueError(f"--pages {count} exceeds the paper's {len(source)} pages")
        if output_root is not None:
            output_root.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^\w.-]+", "-", paper.stem).strip(".-") or "paper"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run = Path(tempfile.mkdtemp(prefix=f"paper-rating-{stamp}-{slug[:60]}-", dir=output_root)).resolve()
        # Keep the original name unless it would collide with a reference.
        name = paper.name if paper.suffix.lower() == ".pdf" else paper.stem + ".pdf"
        occupied = {p.name.casefold() for p in refs}
        while name.casefold() in occupied:
            name = Path(name).stem + "_draft.pdf"
        with pymupdf.open() as shortened:
            shortened.insert_pdf(source, from_page=0, to_page=count - 1)
            shortened.save(run / name, garbage=4, deflate=True)
    for ref in refs:
        (run / ref.name).symlink_to(ref.resolve())

    instructions = [
        "# PDF review workspace",
        "",
        "Evaluate only the PDFs in this directory. Read every page of every paper.",
        "Do not read prior reviews, other run directories, or external sources.",
        "Do not edit PDFs or their symlink targets. Return the requested table in your final response.",
        "Text extracts and page images below are derived from exactly these PDFs.",
        "Inspect page images to judge Figure 1, figures, tables, and presentation; text alone is insufficient.",
        "",
    ]
    assets = run / "assets"
    inventory = []
    for index, pdf in enumerate(pdf_files(run), 1):
        folder = assets / f"{index:02d}"
        folder.mkdir(parents=True)
        with open_pdf(pdf) as doc:
            text = []
            for number, page in enumerate(doc, 1):
                text.append(f"\n--- Page {number} ---\n{page.get_text(sort=True)}")
                page.get_pixmap(dpi=120, alpha=False).save(folder / f"page-{number:03d}.png")
            (folder / "text.txt").write_text("".join(text), encoding="utf-8")
            entry = {"pdf": pdf.name, "pages": len(doc), "assets": str(folder.relative_to(run))}
            inventory.append(entry)
            instructions.append(f"- {pdf.name}: {len(doc)} pages; text and all page images in {entry['assets']}/")
    instruction_text = "\n".join(instructions) + "\n"
    (run / "AGENTS.md").write_text(instruction_text, encoding="utf-8")
    (run / "CLAUDE.md").write_text(instruction_text, encoding="utf-8")
    (run / "prompt.txt").write_text(PROMPT, encoding="utf-8")
    write_metadata(run, {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "draft": name,
        "draft_pages": count,
        "papers": inventory,
        "status": "prepared",
    })
    return run


def write_metadata(run: Path, updates: dict) -> None:
    path = run / "run.json"
    current = json.loads(path.read_text()) if path.exists() else {}
    current.update(updates)
    path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")


def agent_command(agent: str, run: Path, references: Path, model: str | None, effort: str, *,
                  sandbox: str = "read-only", session: str | None = None, resume: str | None = None,
                  report: str = "review.md") -> list[str]:
    """Build the agent command.

    By default the session is not persisted. `session` persists the scoring session so a
    follow-up can continue it (Claude: the session id to create; Codex: any value, since Codex
    assigns the id). `resume` continues that session with a follow-up prompt.
    """
    if effort not in EFFORTS[agent]:
        raise ValueError(f"{agent} effort must be one of: {', '.join(EFFORTS[agent])}")
    if agent == "codex":
        if sandbox not in CODEX_SANDBOXES:
            raise ValueError(f"codex sandbox must be one of: {', '.join(CODEX_SANDBOXES)}")
        shared = [
            "--skip-git-repo-check", "--json",
            "--output-last-message", str(run / report),
            "--config", f'model_reasoning_effort="{effort}"',
            "--ignore-user-config", "--ignore-rules",
            "--config", "memories.use_memories=false",
            "--config", "project_doc_max_bytes=0",
            "--config", "developer_instructions=" + json.dumps(WORKSPACE_INSTRUCTIONS),
        ]
        if resume:
            # `exec resume` has no --sandbox, --cd or --color; set the sandbox through config and run in `run`.
            command = ["codex", "--ask-for-approval", "never", "exec", "resume",
                       "--config", f'sandbox_mode="{sandbox}"', *shared]
        else:
            command = ["codex", "--ask-for-approval", "never", "exec", "--sandbox", sandbox,
                       *([] if session else ["--ephemeral"]), "--color", "never", "--cd", str(run), *shared]
    else:
        if resume:
            persistence = ["--resume", resume]
        elif session:
            persistence = ["--session-id", session]
        else:
            persistence = ["--no-session-persistence"]
        command = [
            "claude", "--print", "--output-format", "stream-json", "--verbose",
            "--safe-mode", "--restricted",
            "--append-system-prompt", WORKSPACE_INSTRUCTIONS,
            *persistence, "--permission-mode", "dontAsk",
            "--tools", "Read,Glob,Grep", "--allowedTools", "Read,Glob,Grep",
            "--add-dir", str(references.resolve()), "--effort", effort,
            "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
        ]
    if model:
        command.extend(["--model", model])
    if agent == "codex":
        if resume:
            command.append(resume)
        command.append("-")
    return command


def run_agent(agent: str, run: Path, command: list[str], prompt: str = PROMPT, stem: str = "agent",
              report: str = "review.md") -> int:
    """Keep the complete event stream and save the final answer separately.

    The scoring run logs to agent.* and review.md; a follow-up uses stem="followup".
    """
    prefix = "" if stem == "agent" else f"{stem}_"
    write_metadata(run, {f"{prefix}status": "running"})
    result_text = ""
    agent_error = False
    try:
        with (run / f"{stem}.jsonl").open("w", encoding="utf-8") as log, \
                (run / f"{stem}.stderr.log").open("w", encoding="utf-8") as errors:
            process = subprocess.Popen(
                command, cwd=run, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=errors, text=True, encoding="utf-8", errors="replace",
            )
            assert process.stdin is not None and process.stdout is not None
            try:
                process.stdin.write(prompt)
                process.stdin.close()
                for line in process.stdout:
                    log.write(line)
                    log.flush()
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(event, dict):
                        continue
                    if agent == "codex" and event.get("type") == "thread.started" and event.get("thread_id"):
                        write_metadata(run, {f"{prefix}session_id": event["thread_id"]})
                    if agent == "claude" and event.get("type") == "result":
                        result_text = event.get("result", "")
                        agent_error = bool(event.get("is_error"))
                code = process.wait()
            except BaseException:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise
            finally:
                process.stdout.close()
        if agent == "claude" and result_text:
            (run / report).write_text(result_text + "\n", encoding="utf-8")
        path = run / report
        if not code and (agent_error or not path.exists() or not path.read_text().strip()):
            code = 1
        write_metadata(run, {f"{prefix}status": "complete" if code == 0 else "failed", f"{prefix}exit_code": code})
        return code
    except (OSError, KeyboardInterrupt) as exc:
        code = 130 if isinstance(exc, KeyboardInterrupt) else 1
        write_metadata(run, {f"{prefix}status": "interrupted" if code == 130 else "failed", f"{prefix}exit_code": code})
        print(f"Agent stopped: {exc}. Logs are in {run}", file=sys.stderr)
        return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paper", type=Path, help="Draft PDF to compare with the reference papers")
    parser.add_argument("--pages", type=int, help="Keep pages 1 through this page, inclusive (default: all pages)")
    parser.add_argument("--agent", choices=tuple(EFFORTS), default="codex")
    parser.add_argument("--model", help="Model name passed unchanged to the selected agent; default: agent's default model")
    parser.add_argument("--effort", default="high", help="Reasoning effort (default: high); codex: minimal/low/medium/high/xhigh; claude: low/medium/high/xhigh/max")
    parser.add_argument("--output-dir", type=Path, help="Parent for fresh run directories (default: system temporary directory)")
    parser.add_argument("--references-dir", type=Path, default=reference_dir(), help="Override the bundled reference PDF directory")
    parser.add_argument("--dry-run", action="store_true", help="Prepare PDFs, text, images and command without calling an agent")
    parser.add_argument("--follow-up", action="store_true",
                        help="After scoring, ask the same session why the draft ranks where it does and how to improve it")
    parser.add_argument("--codex-sandbox", choices=CODEX_SANDBOXES, default="read-only",
                        help="Codex sandbox (default: read-only); use danger-full-access only where the sandbox cannot start")
    args = parser.parse_args(argv)
    if args.effort not in EFFORTS[args.agent]:
        parser.error(f"{args.agent} effort must be one of: {', '.join(EFFORTS[args.agent])}")
    if not args.dry_run and shutil.which(args.agent) is None:
        parser.error(f"{args.agent} is not installed or not on PATH; install and authenticate its CLI first")
    # Claude takes a session id we choose; Codex assigns one, read from its event stream.
    session = (str(uuid.uuid4()) if args.agent == "claude" else "persist") if args.follow_up else None
    try:
        print("Preparing PDFs, text extracts, and page images...", file=sys.stderr, flush=True)
        run = prepare_run(args.paper.resolve(), args.pages, args.references_dir.resolve(),
                          args.output_dir.resolve() if args.output_dir else None)
        command = agent_command(args.agent, run, args.references_dir, args.model, args.effort,
                                sandbox=args.codex_sandbox, session=session)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    write_metadata(run, {"agent": args.agent, "model": args.model, "effort": args.effort, "command": command,
                         "follow_up": args.follow_up})
    if args.agent == "claude" and session:
        write_metadata(run, {"session_id": session})
    print(f"Run directory: {run}", file=sys.stderr, flush=True)
    print(f"Command: {shlex.join(command)}", file=sys.stderr, flush=True)
    if args.dry_run:
        return 0
    print(f"Review in progress; event log: {run / 'agent.jsonl'}", file=sys.stderr, flush=True)
    code = run_agent(args.agent, run, command)
    if code == 0:
        print((run / "review.md").read_text(encoding="utf-8"))
        print(f"Saved review: {run / 'review.md'}", file=sys.stderr)
    else:
        print(f"{args.agent} failed (exit {code}). See {run / 'agent.stderr.log'} and {run / 'agent.jsonl'}", file=sys.stderr)
    if code == 0 and args.follow_up:
        code = follow_up(args, run)
    return code if code >= 0 else 128 - code


def follow_up(args: argparse.Namespace, run: Path) -> int:
    """Continue the scoring session with the follow-up prompt about the draft."""
    metadata = json.loads((run / "run.json").read_text())
    session = metadata.get("session_id")
    if not session:
        print("Follow-up skipped: the scoring run reported no session id.", file=sys.stderr)
        return 1
    prompt = FOLLOWUP.format(draft=metadata["draft"])
    (run / "followup_prompt.txt").write_text(prompt, encoding="utf-8")
    command = agent_command(args.agent, run, args.references_dir, args.model, args.effort,
                            sandbox=args.codex_sandbox, resume=session, report="followup.md")
    write_metadata(run, {"followup_command": command})
    print(f"Follow-up in progress; event log: {run / 'followup.jsonl'}", file=sys.stderr, flush=True)
    code = run_agent(args.agent, run, command, prompt=prompt, stem="followup", report="followup.md")
    if code == 0:
        print((run / "followup.md").read_text(encoding="utf-8"))
        print(f"Saved follow-up: {run / 'followup.md'}", file=sys.stderr)
    else:
        print(f"{args.agent} follow-up failed (exit {code}). See {run / 'followup.stderr.log'}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
