"""Opt-in live GPT-6 Luna smoke test through the user's saved Codex login.

No API key is read/copied. Only ordinary side-filtered game prompts reach Luna.
Codex tools/session persistence are disabled; private reasoning is discarded.
This verifies the game pipeline using a CLI bridge, not the public HTTP API.
"""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend' / 'src'))
OUTPUT = ROOT / 'artifacts' / 'night-20261013' / 'luna-live'
OUTPUT.mkdir(parents=True, exist_ok=True)
workdir = Path(tempfile.mkdtemp(prefix='ibs-luna-live-'))
os.environ['IBS_DB_PATH'] = os.environ.get('IBS_LUNA_RESUME_DB', str(workdir / 'games.sqlite3'))
os.environ['IBS_REPORTS_DIR'] = str(workdir / 'reports')

import httpx
from fastapi.testclient import TestClient
from iron_bottom_sound import api, ai_memory
from iron_bottom_sound.engine import IronBottomEngine, ORDER_PHASES
from iron_bottom_sound.llm import OpenAICompatibleCommander
from iron_bottom_sound.models import GameOptions, Side, Phase
from iron_bottom_sound.realistic_command import RealisticCommander
from iron_bottom_sound.savegame import build_save_bundle, validate_save_bundle


class LunaCLIClient:
    """Minimal real transport for the existing JSON parsing/validation adapter."""
    calls = 0
    budget = 10
    receipts = []

    def post(self, url, *, headers, json):
        if self.calls >= self.budget:
            raise httpx.ReadTimeout('Live-call budget exhausted')
        self.calls += 1
        prompt = '\n\n'.join(m['content'] for m in json['messages'])
        environment = os.environ.copy()
        for scheme, proxy in urllib.request.getproxies().items():
            if scheme in ('http', 'https'):
                environment.setdefault(scheme.upper() + '_PROXY', proxy)
        command = [shutil.which('codex'), 'exec', '--model', 'gpt-6-luna',
                   '--ignore-user-config', '--ephemeral', '--skip-git-repo-check',
                   '--sandbox', 'read-only', '--disable', 'shell_tool', '--disable', 'multi_agent',
                   '-c', 'model_reasoning_effort="low"', '--json', '--cd', str(workdir), '-']
        started = time.monotonic()
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, text=True, encoding='utf-8',
                                   errors='replace', env=environment)
        events = queue.Queue()
        def collect():
            for line in process.stdout:
                try:
                    event = __import__('json').loads(line)
                except ValueError:
                    continue
                if event.get('type') == 'item.completed' and event.get('item', {}).get('type') == 'agent_message':
                    events.put(('final', event['item']['text']))
                elif event.get('type') == 'turn.completed':
                    events.put(('usage', event.get('usage', {})))
                # No reasoning, commentary, tool events or auth output are retained.
        threading.Thread(target=collect, daemon=True).start()
        process.stdin.write(prompt)
        process.stdin.close()
        final, usage = '', {}
        try:
            while time.monotonic() - started < 120:
                try:
                    kind, value = events.get(timeout=1)
                    if kind == 'final': final = value
                    elif kind == 'usage': usage = value
                except queue.Empty:
                    if process.poll() is not None: break
            if process.poll() is None:
                raise httpx.ReadTimeout('Luna CLI exceeded 120 seconds')
            if process.returncode or not final:
                raise httpx.ReadTimeout('Luna CLI returned no final JSON')
        finally:
            if process.poll() is None: process.kill()
            process.wait()
        receipt = {'call': self.calls, 'model': 'gpt-6-luna',
                   'elapsed_seconds': round(time.monotonic() - started, 2), 'usage': usage}
        self.receipts.append(receipt)
        print(__import__('json').dumps(receipt), flush=True)
        request = httpx.Request('POST', 'https://cli-bridge.invalid/chat/completions')
        return httpx.Response(200, request=request, json={
            'id': f'codex-cli-luna-{self.calls}',
            'choices': [{'message': {'content': final}}],
            'usage': {'prompt_tokens': usage.get('input_tokens', 0),
                      'completion_tokens': usage.get('output_tokens', 0)},
        })


def main():
    transport = LunaCLIClient()
    commander = OpenAICompatibleCommander(model='gpt-6-luna', api_key='cli-bridge-no-api-credential',
                                         supports_thinking=False, client=transport)
    api.llm_commander_factory = lambda **kwargs: commander
    api.engine = engine = IronBottomEngine()
    client = TestClient(api.app)
    counterpart = RealisticCommander()
    report = {'model': 'gpt-6-luna', 'route': 'Codex CLI saved login; live output, game API validation',
              'public_http_api_tested': False, 'private_reasoning_retained': False, 'games': []}
    try:
        resume = os.environ.get('IBS_LUNA_RESUME_GAME')
        if resume:
            transport.budget = 2
        for realistic, steps in (((True, 2),) if resume else ((False, 4), (True, 4))):
            if resume:
                state = api.repository.load(resume)
                engine.games[state.game_id] = state
            else:
                state = engine.reset('IBS-S-03', seed=13, options=GameOptions(
                    ruleset_version='night-v2', mode='llm', realistic_command=realistic))
            item = {'mode': 'realistic' if realistic else 'classic', 'game_id': state.game_id, 'decisions': []}
            report['games'].append(item)
            for _ in range(steps):
                if 'axis' not in state.submitted_orders:
                    _, batch, _ = counterpart.choose_plan(engine, state.game_id, Side.AXIS)
                    assert engine.submit_orders(state.game_id, batch).valid
                prompt_memory = ai_memory.prompt_memory(state, Side.ALLIES)
                response = client.post(f'/games/{state.game_id}/llm-opponent',
                                       headers={'X-Player-Side': 'axis'},
                                       json={'api_key': 'cli-bridge-no-api-credential'})
                assert response.status_code == 200, response.text
                assert commander.last_trace['prompt']['same_game_memory'] == prompt_memory
                item['decisions'].append({'turn': state.turn, 'phase': state.phase.value,
                                          'accepted': True, 'attempts': len(commander.last_trace['attempts']),
                                          'memory_revision': state.ai_memory['allies']['revision']})
                print(json.dumps(item['decisions'][-1]), flush=True)
                engine.advance(state.game_id)
                while state.phase not in ORDER_PHASES and state.phase != Phase.COMPLETE:
                    engine.advance(state.game_id)
                api.repository.save(state)
            assert engine.replay(state.game_id).model_dump() == state.model_dump()
            loaded, _ = validate_save_bundle(build_save_bundle(api.repository, state))
            assert loaded.ai_memory == state.ai_memory
            debug = client.get(f'/games/{state.game_id}/ai-debug?debug=true&side=allies')
            assert debug.status_code == 200, debug.text
            assert 'ai_memory' not in engine.observe(state.game_id, Side.AXIS).model_dump()
            item.update(replay_equal=True, saved_memory_equal=True, debug_available=True)
            (OUTPUT / (('resume-' if resume else '') + item['mode'] + '-debug.json')).write_text(
                json.dumps(debug.json(), ensure_ascii=False, indent=2), encoding='utf-8')
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed', error=ai_memory.sanitize(str(error)))
    finally:
        report['receipts'] = transport.receipts
        report['total_live_calls'] = transport.calls
        (OUTPUT / ('resume-result.json' if os.environ.get('IBS_LUNA_RESUME_GAME') else 'result.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        api.repository.close()
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
