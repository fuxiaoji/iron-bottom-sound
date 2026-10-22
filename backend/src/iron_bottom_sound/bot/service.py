"""Transactional, transport-independent matches. Rules remain in the engine."""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from threading import RLock
from typing import Any

from pydantic import ValidationError

from ..battle_report import render_map_image
from ..engine import IronBottomEngine, ORDER_PHASES
from ..tactical import TacticalCommander
from ..models import GameOptions, GameState, OptionalRules, OrderBatch, Phase, Side
from ..realistic_command import RealisticCommander
from .manual_commands import ManualOrdersMixin
from .llm_commands import LLMCommandsMixin


class ServiceError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


class BattleService(ManualOrdersMixin, LLMCommandsMixin):
    """SQLite is the single writer boundary, including across service instances.

    Every operation reloads its state inside a transaction. A failed engine call
    rolls back the match, ready flags, receipt and notifications together.
    ``revision`` names a decision phase, so both seats submit the same revision.
    """

    def __init__(self, db_path: str | Path):
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if str(path) != ':memory:':
            path.touch(mode=0o600, exist_ok=True)
            path.chmod(0o600)
        self.db = sqlite3.connect(str(path), check_same_thread=False, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.lock = RLock()
        self.engine = IronBottomEngine()
        self.db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS bot_matches(
              id TEXT PRIMARY KEY, room TEXT NOT NULL, mode TEXT NOT NULL,
              opponent TEXT NOT NULL, seats TEXT NOT NULL, revision INTEGER NOT NULL,
              state TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS bot_receipts(
              actor TEXT NOT NULL, request TEXT NOT NULL, fingerprint TEXT NOT NULL,
              result TEXT NOT NULL, PRIMARY KEY(actor, request));
            CREATE TABLE IF NOT EXISTS bot_outbox(
              id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL,
              delivered INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS bot_identity_challenges(
              codehash TEXT PRIMARY KEY, c2c_actor TEXT NOT NULL, room TEXT NOT NULL,
              match TEXT NOT NULL, side TEXT NOT NULL, expected_member_actor TEXT NOT NULL,
              expires REAL NOT NULL, consumed INTEGER NOT NULL DEFAULT 0);
            CREATE INDEX IF NOT EXISTS bot_identity_challenges_actor
              ON bot_identity_challenges(c2c_actor, consumed, expires);
            CREATE TABLE IF NOT EXISTS bot_identity_aliases(
              c2c_actor TEXT NOT NULL, room TEXT NOT NULL, memberactor TEXT NOT NULL,
              PRIMARY KEY(c2c_actor, room));
            CREATE TABLE IF NOT EXISTS bot_official_groups(
              app_id TEXT NOT NULL, group_openid TEXT NOT NULL, last_seen REAL NOT NULL,
              PRIMARY KEY(app_id, group_openid));
        ''')
        self._init_manual()
        self._init_llm()
        # DB includes secret orders and QQ seat identities: never serve it as an asset.
        if str(path) != ':memory:':
            path.chmod(0o600)

    def close(self):
        with self.lock:
            self.db.close()

    def record_official_group(self, app_id, group_openid):
        """Private administrator discovery, called only after webhook validation.

        Store no message text, sender identity or orders. Opaque platform group
        IDs cannot be derived from a numeric QQ group number.
        """
        room = 'qqbot:' + app_id + ':' + group_openid
        self._qqbot_context('qqbot:' + app_id + ':member:' + group_openid + ':discovery', room)
        with self._transaction():
            self.db.execute('INSERT INTO bot_official_groups VALUES(?,?,?) '
                            'ON CONFLICT(app_id,group_openid) DO UPDATE SET last_seen=excluded.last_seen',
                            (app_id, group_openid, time.time()))

    @contextmanager
    def _transaction(self):
        with self.lock:
            self.db.execute('BEGIN IMMEDIATE')
            try:
                yield
                self.db.commit()
            except BaseException:
                self.db.rollback()
                raise
            finally:
                self.engine.games.clear()
                self.engine.initial_states.clear()

    @staticmethod
    def _identity(actor_id, room_id):
        if not isinstance(actor_id, str) or not actor_id or len(actor_id) > 160:
            raise ServiceError('identity', '缺少有效玩家身份')
        if actor_id.startswith('qq:') and (not actor_id[3:].isascii() or not actor_id[3:].isdigit()
                or actor_id[3:].startswith('0')):
            raise ServiceError('identity', 'QQ玩家编号必须为规范正整数')
        if not isinstance(room_id, str) or not room_id or len(room_id) > 160:
            raise ServiceError('room', '缺少有效群/房间编号')
        if actor_id.startswith('qqbot:'):
            BattleService._qqbot_context(actor_id, room_id)

    @staticmethod
    def _qqbot_context(actor_id, room_id):
        """Keep app, C2C and group-member identity domains explicitly separate."""
        if not isinstance(actor_id, str) or not isinstance(room_id, str):
            raise ServiceError('identity_link', '官方机器人身份或房间格式错误')
        actor, room = actor_id.split(':'), room_id.split(':')
        if (len(room) != 3 or room[0] != 'qqbot' or
                len(actor) not in {4, 5} or actor[0] != 'qqbot' or
                any(not p or not p.isascii() or any(ord(c) < 33 or ord(c) > 126 for c in p)
                    for p in actor + room)):
            raise ServiceError('identity_link', '官方机器人身份或房间格式错误')
        kind = actor[2]
        if ((kind == 'c2c' and len(actor) != 4) or
                (kind == 'member' and len(actor) != 5) or kind not in {'c2c', 'member'}):
            raise ServiceError('identity_link', '官方机器人身份域错误')
        if actor[1] != room[1] or (kind == 'member' and actor[3] != room[2]):
            raise ServiceError('identity_link', '官方机器人身份不属于此应用或群')
        return kind, actor[1], room[2]

    def resolve_actor(self, actor_id, room_id):
        """Resolve only an explicitly authorized C2C alias in this exact room.

        Callers already inside a match transaction retain the SQLite write lock
        through resolution and the subsequent operation, including across processes.
        """
        self._identity(actor_id, room_id)
        if not actor_id.startswith('qqbot:') or self._qqbot_context(actor_id, room_id)[0] != 'c2c':
            return actor_id
        with self.lock:
            row = self.db.execute('SELECT memberactor FROM bot_identity_aliases WHERE c2c_actor=? AND room=?',
                                  (actor_id, room_id)).fetchone()
            if row is None:
                return actor_id
            member = row['memberactor']
            self._identity(member, room_id)
            if self._qqbot_context(member, room_id)[0] != 'member':
                raise ServiceError('identity_link', '已保存的官方身份绑定无效')
            return member

    def issue_identity_link(self, actor_id, room_id, match_id, side='allies', request_id=None):
        """Privately issue a challenge for an existing, fixed group seat owner.

        The receipt is keyed by the original C2C identity, never its canonical
        member alias. The code must only be returned over that C2C conversation.
        """
        self._identity(actor_id, room_id)
        if not actor_id.startswith('qqbot:') or self._qqbot_context(actor_id, room_id)[0] != 'c2c':
            raise ServiceError('identity_link', '绑定码只能由官方机器人私聊身份申请')
        try:
            side = Side(side).value
        except (ValueError, TypeError):
            raise ServiceError('side', '阵营需为allies或axis') from None
        request_id = request_id if request_id is not None else 'identity-link:' + uuid.uuid4().hex
        with self._transaction():
            fp, cached = self._cached(actor_id, request_id,
                dict(op='issue_identity_link', room=room_id, match=match_id, side=side))
            if cached is not None:
                return cached
            row = self.db.execute('SELECT seats FROM bot_matches WHERE id=? AND room=?',
                                  (match_id, room_id)).fetchone()
            if row is None:
                raise ServiceError('not_found', '此群没有该对局')
            member = json.loads(row['seats']).get(side)
            if not isinstance(member, str) or not member.startswith('qqbot:'):
                raise ServiceError('identity_link', '该席位没有可绑定的官方群成员')
            if self._qqbot_context(member, room_id)[0] != 'member':
                raise ServiceError('identity_link', '该席位没有可绑定的官方群成员')
            alias = self.db.execute('SELECT memberactor FROM bot_identity_aliases WHERE c2c_actor=? AND room=?',
                                    (actor_id, room_id)).fetchone()
            if alias is not None and alias['memberactor'] != member:
                raise ServiceError('identity_link_conflict', '此私聊身份已绑定本群另一位成员，不能覆盖')
            now = time.time()
            active = self.db.execute('SELECT count(*) FROM bot_identity_challenges '
                                    'WHERE c2c_actor=? AND consumed=0 AND expires>?', (actor_id, now)).fetchone()[0]
            if active >= 8:
                raise ServiceError('identity_link_limit', '未过期绑定码已达上限，请稍后重试')
            code = secrets.token_urlsafe(24)
            self.db.execute('INSERT INTO bot_identity_challenges VALUES(?,?,?,?,?,?,?,0)',
                (hashlib.sha256(code.encode()).hexdigest(), actor_id, room_id, match_id, side, member, now + 300))
            return self._receipt(actor_id, request_id, fp, dict(code=code, expires_in=300))

    def claim_identity_link(self, code, actor_id, room_id):
        """Only the authenticated, predetermined group author may consume a code."""
        self._identity(actor_id, room_id)
        if not actor_id.startswith('qqbot:') or self._qqbot_context(actor_id, room_id)[0] != 'member':
            raise ServiceError('identity_link', '绑定确认必须来自官方群成员事件')
        if not isinstance(code, str) or not 1 <= len(code) <= 128:
            raise ServiceError('identity_link', '绑定码无效')
        digest = hashlib.sha256(code.encode()).hexdigest()
        with self._transaction():
            row = self.db.execute('SELECT * FROM bot_identity_challenges WHERE codehash=?', (digest,)).fetchone()
            if row is None or row['room'] != room_id or row['expected_member_actor'] != actor_id:
                raise ServiceError('identity_link', '绑定码或群席位身份不匹配')
            alias = self.db.execute('SELECT memberactor FROM bot_identity_aliases WHERE c2c_actor=? AND room=?',
                                    (row['c2c_actor'], room_id)).fetchone()
            if alias is not None and alias['memberactor'] != actor_id:
                raise ServiceError('identity_link_conflict', '此私聊身份已绑定本群另一位成员，不能覆盖')
            if row['consumed']:
                if alias is not None:
                    return dict(linked=True)
                raise ServiceError('identity_link', '绑定码已使用，绑定记录不可用')
            if row['expires'] <= time.time():
                raise ServiceError('identity_link_expired', '绑定码已过期，请在私聊重新申请')
            match = self.db.execute('SELECT seats FROM bot_matches WHERE id=? AND room=?',
                                    (row['match'], room_id)).fetchone()
            if match is None or json.loads(match['seats']).get(row['side']) != actor_id:
                raise ServiceError('identity_link', '原群席位已变化，请重新申请绑定')
            self.db.execute('INSERT INTO bot_identity_aliases VALUES(?,?,?) ON CONFLICT(c2c_actor,room) DO NOTHING',
                            (row['c2c_actor'], room_id, actor_id))
            self.db.execute('UPDATE bot_identity_challenges SET consumed=1 WHERE codehash=?', (digest,))
            return dict(linked=True)

    @staticmethod
    def _fingerprint(data):
        return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def _cached(self, actor, request_id, data):
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 240:
            raise ServiceError('request_id', '每次操作必须携带唯一请求编号')
        fingerprint = self._fingerprint(data)
        row = self.db.execute('SELECT * FROM bot_receipts WHERE actor=? AND request=?', (actor, request_id)).fetchone()
        if row:
            if row['fingerprint'] != fingerprint:
                raise ServiceError('idempotency_conflict', '请求编号已用于不同操作')
            return fingerprint, json.loads(row['result'])
        return fingerprint, None

    def _receipt(self, actor, request, fingerprint, result):
        self.db.execute('INSERT INTO bot_receipts VALUES(?,?,?,?)',
                        (actor, request, fingerprint, json.dumps(result, ensure_ascii=False)))
        return result

    def _load(self, match_id, room_id, actor_id=None):
        row = self.db.execute('SELECT * FROM bot_matches WHERE id=? AND room=?', (match_id, room_id)).fetchone()
        if row is None:
            raise ServiceError('not_found', '此群没有该对局')
        row = dict(row)
        row['seats'] = json.loads(row['seats'])
        if actor_id is not None and actor_id not in row['seats'].values():
            raise ServiceError('forbidden', '你未加入此对局')
        state = GameState.model_validate_json(row['state'])
        self.engine.games[state.game_id] = state
        return row, state

    def _save(self, row, state):
        self.db.execute('UPDATE bot_matches SET seats=?, revision=?, state=? WHERE id=?',
                        (json.dumps(row['seats']), row['revision'], state.model_dump_json(), row['id']))

    @staticmethod
    def _side(row, actor_id):
        return Side(next(side for side, actor in row['seats'].items() if actor == actor_id))

    def _status(self, row, state, actor):
        side = self._side(row, actor)
        observation = self.engine.observe(state.game_id, side).model_dump(mode='json')
        # Don't disclose the other seat's orders through a neutral report.
        messages = [e['message'] for e in observation.get('recent_events', [])[-8:]
                     if e['type'] not in {'orders_submitted', 'game_created'}]
        summary = f"对局 {row['id']} · 第{state.turn}回合 · {state.phase.value} · 版本 {row['revision']}"
        if messages:
            summary += '\n' + '\n'.join(messages)
        return dict(match_id=row['id'], game_id=state.game_id, revision=row['revision'],
                    turn=state.turn, phase=state.phase.value, side=side.value,
                    mode=row['mode'], opponent=row['opponent'], ready=sorted(state.submitted_orders),
                    started=len(row['seats']) == 2, complete=state.phase == Phase.COMPLETE,
                    observation=observation, summary=summary)

    def catalog(self):
        with self.lock:
            return self.engine.scenarios()

    def create(self, actor_id, room_id, mode='classic', opponent='pve',
               scenario_id='IBS-S-03', side='allies', seed=1, request_id=None):
        self._identity(actor_id, room_id)
        if mode not in {'classic', 'formation'} or opponent not in {'pve', 'pvp'}:
            raise ServiceError('options', '模式需为classic/formation，对手需为pve/pvp')
        try:
            side = Side(side)
        except ValueError:
            raise ServiceError('side', '阵营需为allies或axis') from None
        data = dict(op='create', room=room_id, mode=mode, opponent=opponent,
                    scenario=scenario_id, side=side.value, seed=seed)
        with self._transaction():
            actor_id = self.resolve_actor(actor_id, room_id)
            fp, cached = self._cached(actor_id, request_id, data)
            if cached is not None:
                return cached
            # Bound accidental group spam without restricting finished games.
            existing = self.db.execute('SELECT count(*) FROM bot_matches WHERE room=?', (room_id,)).fetchone()[0]
            if existing >= 100:
                raise ServiceError('room_limit', '该群已达100局上限，请管理员归档数据库')
            try:
                state = self.engine.reset(scenario_id, seed, GameOptions(
                    realistic_command=mode == 'formation', ruleset_version='night-v2',
                    night_recognition=True, optional_rules=OptionalRules(hidden_damage=True)))
            except (KeyError, ValueError) as exc:
                raise ServiceError('scenario', f'无法建立该想定：{exc}') from None
            match_id = uuid.uuid4().hex[:12]
            seats = {side.value: actor_id}
            if opponent == 'pve':
                seats[side.opponent.value] = f'bot:{match_id}'
            row = dict(id=match_id, room=room_id, mode=mode, opponent=opponent, seats=seats, revision=0)
            self.db.execute('INSERT INTO bot_matches VALUES(?,?,?,?,?,?,?)',
                            (match_id, room_id, mode, opponent, json.dumps(seats), 0, state.model_dump_json()))
            result = self._status(row, state, actor_id)
            return self._receipt(actor_id, request_id, fp, result)

    def join(self, match_id, actor_id, room_id, request_id=None):
        self._identity(actor_id, room_id)
        with self._transaction():
            actor_id = self.resolve_actor(actor_id, room_id)
            fp, cached = self._cached(actor_id, request_id, dict(op='join', match=match_id, room=room_id))
            if cached is not None:
                return cached
            row, state = self._load(match_id, room_id)
            if actor_id in row['seats'].values():
                result = self._status(row, state, actor_id)
            else:
                if row['opponent'] != 'pvp' or len(row['seats']) == 2:
                    raise ServiceError('full', '对局席位已满')
                free = next(s.value for s in Side if s.value not in row['seats'])
                row['seats'][free] = actor_id
                self._save(row, state)
                result = self._status(row, state, actor_id)
            return self._receipt(actor_id, request_id, fp, result)

    def matches(self, actor_id, room_id):
        self._identity(actor_id, room_id)
        with self._transaction():
            actor_id = self.resolve_actor(actor_id, room_id)
            result = []
            for item in self.db.execute('SELECT id FROM bot_matches WHERE room=?', (room_id,)).fetchall():
                row, state = self._load(item['id'], room_id)
                if actor_id in row['seats'].values():
                    result.append({k: v for k, v in self._status(row, state, actor_id).items()
                                   if k not in {'observation', 'summary'}})
            return result

    def status(self, match_id, actor_id, room_id):
        self._identity(actor_id, room_id)
        with self._transaction():
            actor_id = self.resolve_actor(actor_id, room_id)
            row, state = self._load(match_id, room_id, actor_id)
            return self._status(row, state, actor_id)

    def public_status(self, match_id, room_id):
        with self._transaction():
            row, state = self._load(match_id, room_id)
            player = self._pve_player_side(row)
            return dict(match_id=match_id, revision=row['revision'], turn=state.turn,
                        phase=state.phase.value, mode=row['mode'], opponent=row['opponent'],
                        ready=sorted(state.submitted_orders), started=len(row['seats']) == 2,
                        complete=state.phase == Phase.COMPLETE,
                        map_view='pve_player' if player is not None else 'shared',
                        view_side=player.value if player is not None else None)

    @staticmethod
    def _pve_player_side(row):
        if row['opponent'] != 'pve':
            return None
        players = [Side(side) for side, actor in row['seats'].items() if not actor.startswith('bot:')]
        if len(players) != 1:
            raise ServiceError('seats', '人机对局的玩家视角无法确定')
        return players[0]

    def public_screenshot(self, match_id, room_id):
        from .public_view import public_png, pve_public_png
        with self._transaction():
            row, state = self._load(match_id, room_id)
            player = self._pve_player_side(row)
            if player is not None:
                return pve_public_png(self.engine, state, player)
            return public_png(self.engine, state)

    def legal(self, match_id, actor_id, room_id):
        self._identity(actor_id, room_id)
        with self._transaction():
            actor_id = self.resolve_actor(actor_id, room_id)
            row, state = self._load(match_id, room_id, actor_id)
            side = self._side(row, actor_id)
            return dict(match_id=match_id, revision=row['revision'], phase=state.phase.value,
                        actions=[a.model_dump(mode='json') for a in self.engine.legal_actions(state.game_id, side)],
                        order_schema=OrderBatch.model_json_schema())

    def _suggest(self, row, state, side):
        commander = RealisticCommander() if row['mode'] == 'formation' else TacticalCommander()
        # Plan on a deep clone, so suggestion cannot mutate saved state or see an
        # opponent's already submitted orders (PVE commits its choice first too).
        source = state
        clone = state.model_copy(deep=True)
        clone.submitted_orders = {}
        self.engine.games[state.game_id] = clone
        try:
            return commander.choose_orders(self.engine, state.game_id, side)
        finally:
            self.engine.games[state.game_id] = source

    def suggest(self, match_id, actor_id, room_id):
        self._identity(actor_id, room_id)
        with self._transaction():
            actor_id = self.resolve_actor(actor_id, room_id)
            row, state = self._load(match_id, room_id, actor_id)
            if state.phase == Phase.COMPLETE:
                raise ServiceError('complete', '对局已结束')
            try:
                batch = self._suggest(row, state, self._side(row, actor_id))
            except ValueError as exc:
                raise ServiceError('suggestion', f'现有策略无法生成方案：{exc}') from None
            return dict(match_id=match_id, revision=row['revision'], phase=state.phase.value,
                        orders=batch.model_dump(mode='json'), policy='offline-state-machine')

    def auto(self, match_id, actor_id, room_id, expected_revision, request_id):
        return self.submit(match_id, actor_id, room_id, {'_auto': True}, expected_revision, request_id)

    def submit(self, match_id, actor_id, room_id, orders, expected_revision, request_id, *, manual_guard=None):
        self._identity(actor_id, room_id)
        with self._transaction():
            actor_id = self.resolve_actor(actor_id, room_id)
            fp, cached = self._cached(actor_id, request_id,
                dict(op='submit', match=match_id, room=room_id, orders=orders, revision=expected_revision))
            if cached is not None:
                return cached
            row, state = self._load(match_id, room_id, actor_id)
            if len(row['seats']) != 2:
                raise ServiceError('waiting', '等待另一位玩家加入')
            if state.phase == Phase.COMPLETE:
                raise ServiceError('complete', '对局已结束')
            if type(expected_revision) is not int or expected_revision < 0:
                raise ServiceError('revision', '阶段版本必须为非负整数')
            if expected_revision != row['revision']:
                raise ServiceError('stale_revision', '阶段版本已变化，请先重新查看态势')
            side = self._side(row, actor_id)
            if side.value in state.submitted_orders:
                raise ServiceError('already_ready', '本阶段已封存命令，等待对手')
            if manual_guard is not None:
                saved = self.db.execute('SELECT selections FROM bot_manual_drafts WHERE actor=? AND room=? '
                    'AND match=? AND revision=? AND phase=?',
                    (actor_id, room_id, match_id, expected_revision, str(state.phase))).fetchone()
                if (manual_guard[0] != str(state.phase) or saved is None
                        or hashlib.sha256(saved['selections'].encode()).hexdigest() != manual_guard[1]):
                    raise ServiceError('manual_stale', '草稿刚刚被修改，请重新查看 /草稿 后再提交；本次未推进。')
            if not isinstance(orders, dict):
                raise ServiceError('orders', '命令必须是OrderBatch JSON对象')
            if orders.get('side', side.value) != side.value or orders.get('phase', state.phase.value) != state.phase.value:
                raise ServiceError('orders', '命令阵营或阶段与当前席位不匹配')
            if orders == {'_auto': True}:
                orders = self._suggest(row, state, side).model_dump(mode='json')
            unknown = set(orders) - set(OrderBatch.model_fields)
            if unknown:
                raise ServiceError('orders', '命令包含未知字段：' + ', '.join(sorted(unknown)))
            try:
                batch = OrderBatch.model_validate({**orders, 'side': side.value, 'phase': state.phase.value})
                # Generate PVE before human submission, on a clone without its plan.
                ai_batch = self._suggest(row, state, side.opponent) if row['opponent'] == 'pve' else None
                if ai_batch is not None:
                    valid = self.engine.submit_orders(state.game_id, ai_batch)
                    if not valid.valid:
                        raise ServiceError('ai_orders', '离线对手方案未通过引擎：' + '; '.join(valid.errors))
                valid = self.engine.submit_orders(state.game_id, batch)
                if not valid.valid:
                    raise ServiceError('invalid_orders', '; '.join(valid.errors))
                advanced = set(state.submitted_orders) == {s.value for s in Side}
                if advanced:
                    self.engine.advance(state.game_id)
                    # Resolve automatic phases; stop at the next player decision.
                    for _ in range(len(Phase)):
                        if state.phase in ORDER_PHASES or state.phase == Phase.COMPLETE:
                            break
                        self.engine.advance(state.game_id)
                    else:
                        raise ServiceError('phase_loop', '引擎未停在下个决策阶段')
                    row['revision'] += 1
                self._save(row, state)
                if advanced:
                    self._enqueue(row, state)
                result = self._status(row, state, actor_id)
                result['advanced'] = advanced
            except ServiceError:
                raise
            except (ValueError, KeyError, ValidationError) as exc:
                raise ServiceError('invalid_orders', str(exc)) from None
            return self._receipt(actor_id, request_id, fp, result)

    def _png(self, state, side):
        stream = BytesIO()
        render_map_image(state, self.engine, side, ship_names=True).save(stream, format='PNG')
        return stream.getvalue()

    def screenshot(self, match_id, actor_id, room_id):
        self._identity(actor_id, room_id)
        with self._transaction():
            actor_id = self.resolve_actor(actor_id, room_id)
            row, state = self._load(match_id, room_id, actor_id)
            return self._png(state, self._side(row, actor_id))

    def _enqueue(self, row, state):
        for side, actor in row['seats'].items():
            if not actor.startswith('qq:'):
                continue
            status = self._status(row, state, actor)
            payload = dict(actor_id=actor, match_id=row['id'], room_id=row['room'],
                           revision=row['revision'], summary=status['summary'],
                           image=base64.b64encode(self._png(state, Side(side))).decode())
            self.db.execute('INSERT INTO bot_outbox(payload) VALUES(?)', (json.dumps(payload, ensure_ascii=False),))
        if row['room'].startswith('qq:'):
            from .public_view import public_observation, public_png
            view = public_observation(self.engine, state)
            messages = [e.message for e in view.recent_events[-8:]]
            summary = f"对局 {row['id']} · 第{state.turn}回合 · {state.phase.value} · 版本 {row['revision']}\n双方共同公开战况"
            if messages:
                summary += '\n' + '\n'.join(messages)
            payload = dict(group_id=row['room'][3:], match_id=row['id'], room_id=row['room'],
                           revision=row['revision'], summary=summary,
                           image=base64.b64encode(public_png(self.engine, state)).decode())
            self.db.execute('INSERT INTO bot_outbox(payload) VALUES(?)', (json.dumps(payload, ensure_ascii=False),))

    def pending_notifications(self, after_id=0):
        with self.lock:
            return [dict(id=r['id'], **json.loads(r['payload'])) for r in
                    self.db.execute('SELECT * FROM bot_outbox WHERE delivered=0 AND id>? ORDER BY id LIMIT 20', (after_id,))]

    def acknowledge_notification(self, notification_id):
        with self.lock, self.db:
            self.db.execute('UPDATE bot_outbox SET delivered=1 WHERE id=?', (notification_id,))
