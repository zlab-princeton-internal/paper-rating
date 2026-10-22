# Paper Writing Self-Review

*By [Zhuang Liu](https://liuzhuang13.github.io/)*

**Related**: [Writing Guide](https://github.com/zlab-princeton-internal/writing-guide) · [Figure Guide](https://github.com/zlab-princeton-internal/figure-guide) · [AI Paper Checking](https://github.com/zlab-princeton-internal/ai-paper-checking) · [Peer Review System](https://github.com/zlab-princeton-internal/peer-review)

> This guide is intended for [Zhuang Liu](https://liuzhuang13.github.io/)'s group members. Others are welcome to adopt or adapt it for their own use.

AI-based writing quality check for your draft, comparing against a set of reference papers.

This evaluates **writing and presentation only** — not impact, novelty, or technical contribution. Run it when your draft is mostly complete, before submission.

## How to use

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and install and authenticate either [Codex CLI](https://developers.openai.com/codex/cli/) or [Claude Code](https://code.claude.com/docs/en/quickstart). Run from this repository:

```bash
uv run paper_rating /path/to/paper.pdf --pages 12 --agent codex --model YOUR_MODEL --effort high
uv run paper_rating /path/to/paper.pdf --pages 12 --agent claude --model opus --effort high
```

`uv` installs the Python dependencies automatically. `--pages 12` keeps pages 1 through 12, inclusive, in a new PDF; the original is untouched. Omit `--pages` to use the whole draft. A page limit beyond the end of the draft is an error.

Add `--follow-up` to ask, after scoring, why your draft is ranked where it is and how it could score higher:

```bash
uv run paper_rating /path/to/paper.pdf --pages 12 --agent codex --model YOUR_MODEL --effort high --follow-up
```

The scoring prompt is sent unchanged. Once the table is done, the same session receives the follow-up prompt (stored in `src/paper_rating/followup.txt`), which names your draft and asks for page-cited reasons per category and a prioritized list of changes. Its answer is saved to `followup.md` and printed after the table. The follow-up never re-scores.

`--agent` defaults to `codex`, and `--effort` defaults to `high`. Omit `--model` to use the agent's default model. Model names are passed directly to the agent. Codex accepts `minimal`, `low`, `medium`, `high`, and `xhigh`; Claude accepts `low`, `medium`, `high`, `xhigh`, and `max`. The chosen model must support the requested effort.

Each invocation creates a brand-new temporary directory outside the repository, containing:

- The shortened draft and symlinks to all 11 PDFs in `no_app_pdfs/`.
- `assets/`: text extracts and page images for every page of every PDF, allowing either agent to inspect figures and layout.
- `prompt.txt`, `AGENTS.md`, and `CLAUDE.md`: the scoring prompt and instructions to read the complete papers and inspect the images.
- `run.json`: the paper inventory, settings, exact agent command, and completion status.
- `agent.jsonl` and `agent.stderr.log`: the agent's event stream and diagnostics.
- `review.md`: the final response, also printed to the terminal when the agent succeeds.
- With `--follow-up`: `followup_prompt.txt`, `followup.jsonl`, `followup.stderr.log`, and `followup.md`.

The wrapper launches one new subprocess in that directory: `codex exec` or `claude -p`. Every evaluation starts with fresh context; neither backend resumes a previous conversation. Without `--follow-up`, no resumable session is persisted. With it, the scoring session is persisted so that a second subprocess (`codex exec resume` or `claude -p --resume`) can continue that same session, and only that one. Codex disables memory injection and automatic AGENTS.md loading, ignores user config, and receives only the generated review instructions. Claude uses safe mode to disable automatic memory and instruction loading and receives those same instructions explicitly. Existing CLI authentication is retained.

Codex uses a read-only sandbox. On machines where its sandbox cannot start (for example, `bwrap: Can't mkdir parents ...` when `/tmp` is a private mount), `--codex-sandbox danger-full-access` runs Codex unsandboxed; use it only where that is acceptable. Claude's restricted mode confines Read, Glob, and Grep to the run and reference directories. The instructions exclude prior reviews and external sources. The wrapper cannot guarantee that an agent actually reads every page or produces valid scores; inspect its event log when auditing a result.

Prepare everything and inspect the command without calling an agent:

```bash
uv run paper_rating paper.pdf --pages 12 --agent codex --dry-run
```

The temporary directory is retained so you can inspect the result; its path is printed to the terminal. Use `--output-dir /path/to/runs` to choose a different parent for newly created directories or `--references-dir /path/to/pdfs` to replace the reference set. A directory is never reused, even with `--output-dir`. The reference directory must contain at least one readable PDF. Symlinks point to the reference files, so keep that directory available while reviewing a run.

## The prompt

The command sends this prompt verbatim (stored in `src/paper_rating/prompt.txt`):

```text
Score the writing quality of every PDF in this folder. Writing and presentation only, not impact.

Read each paper in full and score each one independently. Rate 0-100 on:
- Overall
- Title
- Abstract
- Figure 1
- Figures and tables
- Introduction
- Method description
- Experiment design

Output a comparison table sorted by Overall (highest first).

Do not penalize needed complexity, newer papers are more complex by nature.
```

You can also upload the PDFs to a new chat with a reasoning model and paste this prompt manually.

## Reference papers

The bundled copies omit appendices and retain bibliographies. See `no_app_pdfs/sources.json` for preparation details and page counts.

| Paper | Type | arXiv |
|-------|------|-------|
| ConvNeXt | Method | https://arxiv.org/abs/2201.03545 |
| DenseNet | Method | https://arxiv.org/abs/1608.06993 |
| Transformers without Normalization | Method | https://arxiv.org/abs/2503.10622 |
| Wanda | Method | https://arxiv.org/abs/2306.11695 |
| MAE | Method | https://arxiv.org/abs/2111.06377 |
| Deconstructing Denoising Diffusion | Empirical study | https://arxiv.org/abs/2401.14404 |
| A Decade's Battle on Dataset Bias | Empirical study | https://arxiv.org/abs/2403.08632 |
| Massive Activations in LLMs | Empirical study | https://arxiv.org/abs/2402.17762 |
| Eyes Wide Shut | Benchmark | https://arxiv.org/abs/2401.06209 |
| Thinking in Space | Benchmark | https://arxiv.org/abs/2412.14171 |
| Vero | Method | https://arxiv.org/abs/2604.04917 |

## After scoring

- Find your draft in the output table. Pay attention to **same-type** reference papers (method vs method, empirical vs empirical, benchmark vs benchmark). **Aim to bring your draft at least up to the average score of the same-type reference papers.**
- Use the saved response to ask follow-up questions about the scores in a separate session. How to actually improve the paper is up to you.
- **Do not let the AI directly edit your paper and re-score in the same session.** The AI will optimize against its own biases and the score becomes meaningless (overfitting).
- **Every re-scoring must be in a brand-new session** with no access to prior history or previous scores. Run the command again to prepare a fresh workspace.

## Development

```bash
uv run python -m unittest discover -s tests -v
```

The tests use generated PDFs and stub agent executables; they do not call models. Headless backend behavior follows the [Codex non-interactive documentation](https://developers.openai.com/codex/noninteractive/) and [Claude Code headless documentation](https://code.claude.com/docs/en/headless).
