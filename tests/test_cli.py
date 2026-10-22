import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pymupdf

from paper_rating.cli import PROMPT, agent_command, main, open_pdf, prepare_run


def make_pdf(path, count):
    with pymupdf.open() as doc:
        for number in range(count):
            doc.new_page().insert_text((50, 50), f'Content on page {number + 1}')
        doc.save(path)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='paper rating tests ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.refs = self.root / 'reference papers'
        self.refs.mkdir()
        make_pdf(self.refs / 'Reference.pdf', 1)
        self.paper = self.root / 'Draft.pdf'
        make_pdf(self.paper, 3)
        self.out = self.root / 'runs'

    def prepare(self, pages=2):
        return prepare_run(self.paper, pages, self.refs, self.out)

    def test_inclusive_crop_and_unchanged_inputs(self):
        before = hashlib.sha256(self.paper.read_bytes()).digest()
        run = self.prepare()
        with open_pdf(run / self.paper.name) as doc:
            self.assertEqual(len(doc), 2)
            self.assertIn('page 2', doc[1].get_text())
        self.assertEqual(hashlib.sha256(self.paper.read_bytes()).digest(), before)
        self.assertTrue((run / 'Reference.pdf').is_symlink())
        self.assertEqual((run / 'Reference.pdf').resolve(), (self.refs / 'Reference.pdf').resolve())
        data = json.loads((run / 'run.json').read_text())
        self.assertEqual(data['draft_pages'], 2)
        for paper in data['papers']:
            assets = run / paper['assets']
            self.assertEqual(len(list(assets.glob('*.png'))), paper['pages'])
            self.assertIn('Content on page 1', (assets / 'text.txt').read_text())
        self.assertEqual((run / 'prompt.txt').read_text(), PROMPT)

    def test_full_paper_and_unique_folders(self):
        first = self.prepare(None)
        second = self.prepare(None)
        self.assertNotEqual(first, second)
        with open_pdf(first / self.paper.name) as doc:
            self.assertEqual(len(doc), 3)

    def test_bad_limits_do_not_create_runs(self):
        for pages in (0, -1, 4):
            with self.subTest(pages=pages), self.assertRaises(ValueError):
                self.prepare(pages)
        self.assertFalse(self.out.exists())

    def test_invalid_reference_does_not_create_run(self):
        (self.refs / 'broken.pdf').write_text('Not a PDF')
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertFalse(self.out.exists())

    def test_collision_keeps_reference(self):
        self.paper = self.root / 'Reference.pdf'
        make_pdf(self.paper, 3)
        run = self.prepare()
        self.assertTrue((run / 'Reference.pdf').is_symlink())
        self.assertFalse((run / 'Reference_draft.pdf').is_symlink())
        with open_pdf(run / 'Reference_draft.pdf') as doc:
            self.assertEqual(len(doc), 2)

    def test_backend_settings(self):
        run = self.prepare()
        codex = agent_command('codex', run, self.refs, 'my-model', 'xhigh')
        self.assertEqual(codex[codex.index('--model') + 1], 'my-model')
        self.assertIn('model_reasoning_effort="xhigh"', codex)
        self.assertEqual(codex[-1], '-')
        self.assertIn('read-only', codex)
        self.assertIn('memories.use_memories=false', codex)
        self.assertIn('project_doc_max_bytes=0', codex)
        self.assertIn('--ignore-user-config', codex)
        self.assertNotIn('resume', codex)
        claude = agent_command('claude', run, self.refs, 'opus', 'max')
        self.assertEqual(claude[claude.index('--effort') + 1], 'max')
        self.assertIn('--no-session-persistence', claude)
        self.assertIn('--safe-mode', claude)
        self.assertIn('--restricted', claude)
        self.assertNotIn('--resume', claude)
        self.assertNotIn('--continue', claude)
        with self.assertRaises(ValueError):
            agent_command('codex', run, self.refs, None, 'max')
        self.assertIn('--ephemeral', codex)
        with self.assertRaises(ValueError):
            agent_command('codex', run, self.refs, None, 'high', sandbox='workspace-write')

    def test_follow_up_commands_persist_then_resume(self):
        run = self.prepare()
        codex = agent_command('codex', run, self.refs, 'm', 'high', session='persist')
        self.assertNotIn('--ephemeral', codex)
        self.assertNotIn('resume', codex)
        resumed = agent_command('codex', run, self.refs, 'm', 'high', resume='T-1', report='followup.md',
                                sandbox='danger-full-access')
        self.assertEqual(resumed[resumed.index('exec') + 1], 'resume')
        self.assertEqual(resumed[-2:], ['T-1', '-'])
        self.assertIn('sandbox_mode="danger-full-access"', resumed)
        for flag in ('--sandbox', '--cd', '--color', '--ephemeral'):  # not accepted by `codex exec resume`
            self.assertNotIn(flag, resumed)
        self.assertEqual(resumed[resumed.index('--output-last-message') + 1], str(run / 'followup.md'))
        claude = agent_command('claude', run, self.refs, 'opus', 'high', session='S-1')
        self.assertEqual(claude[claude.index('--session-id') + 1], 'S-1')
        self.assertNotIn('--no-session-persistence', claude)
        claude_resumed = agent_command('claude', run, self.refs, 'opus', 'high', resume='S-1')
        self.assertEqual(claude_resumed[claude_resumed.index('--resume') + 1], 'S-1')
        self.assertIn('--restricted', claude_resumed)

    def invoke(self, extra):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main([str(self.paper), '--pages', '2', '--references-dir', str(self.refs),
                         '--output-dir', str(self.out), *extra])

    def test_dry_run_never_starts_agent(self):
        with patch('paper_rating.cli.subprocess.Popen') as process:
            self.assertEqual(self.invoke(['--dry-run']), 0)
            process.assert_not_called()
        run = next(self.out.iterdir())
        self.assertEqual(json.loads((run / 'run.json').read_text())['status'], 'prepared')

    def test_default_uses_new_system_temp_directory_every_time(self):
        import shutil
        first = prepare_run(self.paper, 1, self.refs)
        self.addCleanup(shutil.rmtree, first)
        (first / 'review.md').write_text('Old score: 99')
        second = prepare_run(self.paper, 1, self.refs)
        self.addCleanup(shutil.rmtree, second)
        self.assertNotEqual(first, second)
        self.assertEqual(first.parent, Path(tempfile.gettempdir()).resolve())
        self.assertFalse((second / 'review.md').exists())
        self.assertNotIn('Old score', (second / 'AGENTS.md').read_text())

    def stub(self, agent, failure=False):
        executable = self.root / agent
        # Use the same Python environment so the test does not depend on PATH's python.
        import sys
        executable.write_text(f'#!{sys.executable}\n' + '''import json, pathlib, sys
prompt = sys.stdin.read()
pathlib.Path('received-prompt.txt').write_text(prompt)
pathlib.Path('received-args.json').write_text(json.dumps(sys.argv[1:]))
''' + ('''pathlib.Path(sys.argv[sys.argv.index('--output-last-message') + 1]).write_text('| Paper | Overall |\\n| Draft | 88 |\\n')
print(json.dumps({'type': 'turn.completed'}))
''' if agent == 'codex' else f'''print(json.dumps({{'type': 'result', 'is_error': {failure!r}, 'result': '| Paper | Overall |\\n| Draft | 88 |'}}))
'''))
        executable.chmod(0o755)
        return {'PATH': str(self.root) + os.pathsep + os.environ.get('PATH', '')}

    def test_both_backends_end_to_end(self):
        for agent in ('codex', 'claude'):
            with self.subTest(agent=agent), patch.dict(os.environ, self.stub(agent)):
                self.assertEqual(self.invoke(['--agent', agent, '--model', 'test-model', '--effort', 'high']), 0)
                run = next(p for p in self.out.iterdir() if not (p / 'checked').exists())
                self.assertEqual((run / 'received-prompt.txt').read_text(), PROMPT)
                metadata = json.loads((run / 'run.json').read_text())
                self.assertEqual(metadata['status'], 'complete')
                self.assertEqual(metadata['agent'], agent)
                args = json.loads((run / 'received-args.json').read_text())
                self.assertEqual(args[args.index('--model') + 1], 'test-model')
                self.assertIn('88', (run / 'review.md').read_text())
                (run / 'checked').touch()

    def recording_stub(self, agent):
        """Stub that logs every call, so a scoring run and its follow-up can both be checked."""
        executable = self.root / agent
        import sys
        executable.write_text(f'#!{sys.executable}\n' + '''import json, pathlib, sys
args = sys.argv[1:]
calls = pathlib.Path('calls.jsonl')
n = len(calls.read_text().splitlines()) if calls.exists() else 0
with calls.open('a') as f:
    f.write(json.dumps({'args': args, 'prompt': sys.stdin.read()}) + '\\n')
answer = '| Paper | Overall |\\n| Draft | 88 |' if n == 0 else 'Reasons and improvements for the draft'
''' + ('''print(json.dumps({'type': 'thread.started', 'thread_id': 'thread-123'}))
pathlib.Path(args[args.index('--output-last-message') + 1]).write_text(answer + '\\n')
print(json.dumps({'type': 'turn.completed'}))
''' if agent == 'codex' else '''print(json.dumps({'type': 'result', 'is_error': False, 'result': answer}))
'''))
        executable.chmod(0o755)
        return {'PATH': str(self.root) + os.pathsep + os.environ.get('PATH', '')}

    def test_follow_up_continues_the_scoring_session(self):
        for agent in ('codex', 'claude'):
            with self.subTest(agent=agent), patch.dict(os.environ, self.recording_stub(agent)):
                self.assertEqual(self.invoke(['--agent', agent, '--follow-up']), 0)
                run = next(p for p in self.out.iterdir() if not (p / 'checked').exists())
                calls = [json.loads(line) for line in (run / 'calls.jsonl').read_text().splitlines()]
                self.assertEqual(len(calls), 2)
                first, second = calls
                self.assertEqual(first['prompt'], PROMPT)  # the scoring prompt is sent unchanged
                self.assertIn(self.paper.name, second['prompt'])
                metadata = json.loads((run / 'run.json').read_text())
                self.assertEqual(metadata['status'], 'complete')
                self.assertEqual(metadata['followup_status'], 'complete')
                if agent == 'codex':
                    self.assertNotIn('--ephemeral', first['args'])
                    self.assertEqual(second['args'][-2:], ['thread-123', '-'])
                else:
                    session = first['args'][first['args'].index('--session-id') + 1]
                    self.assertEqual(second['args'][second['args'].index('--resume') + 1], session)
                self.assertIn('88', (run / 'review.md').read_text())
                self.assertIn('Reasons and improvements', (run / 'followup.md').read_text())
                (run / 'checked').touch()

    def test_claude_error_result_is_failure(self):
        with patch.dict(os.environ, self.stub('claude', failure=True)):
            self.assertEqual(self.invoke(['--agent', 'claude']), 1)
        run = next(self.out.iterdir())
        self.assertEqual(json.loads((run / 'run.json').read_text())['status'], 'failed')

    def test_agent_exit_failure_keeps_logs(self):
        executable = self.root / 'codex'
        executable.write_text('#!/bin/sh\ncat >/dev/null\necho "Authentication failed" >&2\nexit 7\n')
        executable.chmod(0o755)
        with patch.dict(os.environ, {'PATH': str(self.root) + os.pathsep + os.environ['PATH']}):
            self.assertEqual(self.invoke(['--agent', 'codex']), 7)
        run = next(self.out.iterdir())
        self.assertIn('Authentication failed', (run / 'agent.stderr.log').read_text())
        self.assertEqual(json.loads((run / 'run.json').read_text())['exit_code'], 7)


if __name__ == '__main__':
    unittest.main()
