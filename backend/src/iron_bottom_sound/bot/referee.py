"""Trusted-administrator referee actions with isolated model planning and undo.

The model proposes structured edits; authorization and validation stay here.
Snapshots are private SQLite data and never part of a model context or reply.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
import time

from pydantic import ValidationError

from ..models import GameState, HexCoord, Phase, ShipState, Side


SHIP_IMMUTABLE = {
    'id', 'name', 'side', 'ship_type', 'displacement_band', 'speed_track',
    'speed_damage_track', 'initial_max_speed', 'max_hull', 'torpedo_type',
    'belt_armor', 'primary_armor', 'secondary_armor', 'bridge_armor',
    'aircraft', 'radar', 'vp', 'asset',
}
SHIP_LIFECYCLE_FIELDS = {
    'command_status', 'formation_id', 'reinforcement_turn', 'sunk',
    'sinking_turn', 'sinking_drift_pending', 'withdrawal_edge',
}
SHIP_FIELDS = set(ShipState.model_fields) - SHIP_IMMUTABLE - SHIP_LIFECYCLE_FIELDS
GAME_FIELDS = {
    'turn', 'phase', 'max_turns', 'visibility', 'score', 'hull_damage_taken',
    'winner', 'victory_reason', 'reinforcement_trigger_turn',
    'reinforcement_arrival_turn', 'reinforcement_roll_done', 'reinforcement_available',
}
MOUNT_FIELDS = {'destroyed', 'fired_this_phase'}
LAUNCHER_FIELDS = {'loaded', 'reloads_remaining', 'reload_turns_remaining', 'destroyed'}
WEAPON_FIELDS = {'ammo', 'destroyed'}
PLAN_FIELDS = {'action', 'match_id', 'create', 'changes', 'steps', 'message'}


def _error(code, text):
    from .service import ServiceError
    return ServiceError(code, text)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _headings():
    # Derive compass names from the engine's printed-map geometry contract.
    from ..battle_report import heading_direction
    values = {}
    for number in range(1, 7):
        x, y = heading_direction(number)
        name = ('北' if y < 0 else '南') if abs(x) < 1e-9 else (
            ('东北' if y < 0 else '东南') if x > 0 else ('西北' if y < 0 else '西南'))
        values[str(number)] = {'name': name, 'axial_delta': list(HexCoord.direction_delta(number))}
    return values


class RefereeMixin:
    def _init_referee(self):
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS bot_state_history(
              id INTEGER PRIMARY KEY AUTOINCREMENT, match TEXT NOT NULL,
              room TEXT NOT NULL, before_revision INTEGER NOT NULL,
              before_state TEXT NOT NULL, actor TEXT NOT NULL,
              operation TEXT NOT NULL, created REAL NOT NULL,
              consumed INTEGER NOT NULL DEFAULT 0);
            CREATE INDEX IF NOT EXISTS bot_state_history_match
              ON bot_state_history(room,match,consumed,id);
            CREATE TABLE IF NOT EXISTS bot_referee_calls(
              actor TEXT NOT NULL, request TEXT NOT NULL, room TEXT NOT NULL,
              fingerprint TEXT NOT NULL, status TEXT NOT NULL,
              created REAL NOT NULL, meta TEXT NOT NULL,
              response TEXT, result TEXT, PRIMARY KEY(actor,request));
            CREATE TABLE IF NOT EXISTS bot_referee_audit(
              id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT NOT NULL,
              room TEXT NOT NULL, request TEXT NOT NULL, summary TEXT NOT NULL,
              created REAL NOT NULL, UNIQUE(actor,request));
        ''')

    def _referee_save_history(self, row, state_json, actor, operation):
        before = self.db.execute('SELECT room,revision,state FROM bot_matches WHERE id=?', (row['id'],)).fetchone()
        if before and before['state'] != state_json:
            self.db.execute('INSERT INTO bot_state_history(match,room,before_revision,before_state,actor,operation,created) '
                'VALUES(?,?,?,?,?,?,?)', (row['id'], before['room'], before['revision'], before['state'],
                                         actor or 'system', operation, time.time()))

    def _referee_admin(self, actor, room, admins):
        self._identity(actor, room)
        canonical = self.resolve_actor(actor, room)
        if canonical not in admins:
            raise _error('forbidden', '裁判指令仅限服务器预设的游戏管理员；模型不能授予权限。')
        return canonical

    @staticmethod
    def _referee_validate_plan(value):
        if not isinstance(value, dict) or not PLAN_FIELDS <= set(value) or set(value) - PLAN_FIELDS - {'model','usage'}:
            raise _error('referee_format', '裁判回令结构无效，本次未修改。')
        if 'model' in value and (not isinstance(value['model'], str) or len(value['model']) > 100):
            raise _error('referee_format', '裁判模型元数据无效。')
        if 'usage' in value and (not isinstance(value['usage'], dict) or
                set(value['usage']) - {'prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens'} or
                any(type(v) is not int or not 0 <= v <= 10**9 for v in value['usage'].values())):
            raise _error('referee_format', '裁判用量元数据无效。')
        value = {k:deepcopy(value[k]) for k in PLAN_FIELDS}
        action, match = value['action'], value['match_id']
        if (action not in {'create', 'advance', 'patch', 'undo', 'report', 'clarify'}
                or (match is not None and (not isinstance(match, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', match)))
                or type(value['steps']) is not int or not 1 <= value['steps'] <= 6
                or not isinstance(value['message'], str) or len(value['message']) > 800):
            raise _error('referee_format', '裁判回令字段无效，本次未修改。')
        if action == 'create':
            create = value['create']
            if (not isinstance(create, dict) or set(create) != {'mode','opponent','scenario_id','side','seed'}
                    or create['mode'] not in {'classic','formation'} or create['opponent'] not in {'pve','pvp'}
                    or create['side'] not in {'allies','axis'} or type(create['seed']) is not int
                    or not isinstance(create['scenario_id'], str) or not create['scenario_id']
                    or match is not None or value['changes'] is not None):
                raise _error('referee_format', '新建参数不完整或无效，本次未修改。')
        elif value['create'] is not None:
            raise _error('referee_format', '此动作不得包含新建参数。')
        if action == 'patch':
            changes = value['changes']
            if (not isinstance(changes, dict) or set(changes) != {'ships','game'}
                    or not isinstance(changes['ships'], list) or len(changes['ships']) > 100
                    or not isinstance(changes['game'], dict) or len(changes['game']) > len(GAME_FIELDS)
                    or not (changes['ships'] or changes['game'])):
                raise _error('referee_patch', '请提供完整明确的舰船或进度修正值。')
            for edit in changes['ships']:
                if (not isinstance(edit, dict) or set(edit) != {'ship_id','fields'}
                        or not isinstance(edit['ship_id'], str) or not 1 <= len(edit['ship_id']) <= 128
                        or not isinstance(edit['fields'], dict) or not edit['fields']):
                    raise _error('referee_patch', '舰船修正需要明确目标和完整字段值。')
        elif value['changes'] is not None:
            raise _error('referee_format', '此动作不得包含状态修正字段。')
        return deepcopy(value)

    def _referee_context(self, actor, room, match_id):
        from .llm_commands import _observation
        from .public_view import public_observation
        index = []
        for item in self.db.execute('SELECT id FROM bot_matches WHERE room=? ORDER BY rowid', (room,)).fetchall():
            row, state = self._load(item['id'], room)
            index.append(dict(match_id=row['id'], revision=row['revision'], phase=str(state.phase),
                              turn=state.turn, mode=row['mode'], opponent=row['opponent'], complete=state.phase == Phase.COMPLETE))
        selected = match_id
        if selected is None:
            available = [v for v in index if not v['complete']] or index
            if len(available) == 1:
                selected = available[0]['match_id']
        current = None
        if selected is not None:
            row, state = self._load(selected, room)
            clone = state.model_copy(deep=True)
            clone.submitted_orders = {}
            self.engine.games[state.game_id] = clone
            try:
                side = self._pve_player_side(row) if row['opponent'] == 'pve' else None
                view = self.engine.observe(clone.game_id, side) if side else public_observation(self.engine, clone)
                current = dict(match_id=selected, revision=row['revision'], phase=str(state.phase), turn=state.turn,
                    mode=row['mode'], opponent=row['opponent'], view='player' if side else 'shared', observation=_observation(view))
            finally:
                self.engine.games[state.game_id] = state
        recent = [json.loads(r['summary']) for r in self.db.execute(
            'SELECT summary FROM bot_referee_audit WHERE actor=? AND room=? ORDER BY id DESC LIMIT 3', (actor, room)).fetchall()]
        context = dict(matches=index, current=current, recent_operations=recent,
            catalog=[{k: v[k] for k in ('id','scenario_id','title','name') if k in v} for v in self.catalog()],
            referee_schema=dict(actions=['create','advance','patch','undo','report','clarify'],
                mutable_ship_fields=sorted(SHIP_FIELDS), immutable_ship_fields=sorted(SHIP_IMMUTABLE),
                unsupported_lifecycle_fields=sorted(SHIP_LIFECYCLE_FIELDS),
                mutable_game_fields=sorted(GAME_FIELDS), ship_state_schema=ShipState.model_json_schema(),
                weapon_fields=sorted(WEAPON_FIELDS), gun_mount_fields=sorted(MOUNT_FIELDS),
                torpedo_launcher_fields=sorted(LAUNCHER_FIELDS), headings=_headings(),
                position_example={'label':'P15','axial':HexCoord.from_label('P15').model_dump(mode='json')},
                notes=['舰船ship_id可用已知精确ID或用户明确给出的唯一船名；不猜隐藏船编号。',
                    'position可用印刷格字符串或完整q/r对象，必须在本局地图且非陆地。',
                    '不得清空position或移动已沉没/撤离舰。hull仅允许非沉没舰的正整数且不超过原max_hull。',
                    '沉没、残骸、增援、撤离和编队成员生命周期不能直接修正；需后续成组操作支持。速度不超过原initial_max_speed。',
                    '武器数组按既有id给出运行字段；装填与备用量不得超过原容量，鱼雷总ammo须等于各管loaded之和。',
                    '缺失坐标、数量或其他必要值必须澄清，禁止猜值。steps是1至6个决策阶段。',
                    '本群多局未明确选择时，不得猜选修改目标。undo仅撤销服务启用快照后记录的一步。']))
        return selected, context

    def _referee_claim(self, match_id, actor_id, room, instruction, scope, request, admins):
        if scope not in {'group','c2c'} or not isinstance(instruction, str) or not instruction.strip() or len(instruction) > 1600:
            raise _error('referee_parameters', '请用1600字以内明确描述裁判操作。')
        if not isinstance(request, str) or not 1 <= len(request) <= 200:
            raise _error('request_id', '裁判请求需要唯一消息编号。')
        with self._transaction():
            actor = self._referee_admin(actor_id, room, admins)
            fingerprint = self._fingerprint(dict(match=match_id, room=room, scope=scope,
                instruction_sha256=hashlib.sha256(instruction.encode()).hexdigest()))
            saved = self.db.execute('SELECT * FROM bot_referee_calls WHERE actor=? AND request=?', (actor, request)).fetchone()
            if saved:
                if saved['fingerprint'] != fingerprint:
                    raise _error('idempotency_conflict', '该消息编号已用于另一条裁判指令。')
                if saved['status'] == 'pending':
                    raise _error('referee_pending', '该裁判请求仍在处理或上次已中断，不会重复调用模型；请查询状态或另发新指令。')
                return actor, dict(saved), None
            selected, context = self._referee_context(actor, room, match_id)
            allowed = set()
            if selected:
                _, state = self._load(selected, room)
                observed = context['current']['observation'].get('ships', [])
                visible = {v.get('id') for v in observed} | {v.get('name') for v in observed}
                for sid, ship in state.ships.items():
                    exact_id = re.search(r'(?<![A-Za-z0-9_-])'+re.escape(sid)+r'(?![A-Za-z0-9_-])', instruction)
                    if sid in visible or ship.name in visible or exact_id or ship.name in instruction:
                        allowed.add(sid)
            meta = dict(match_id=selected, revision=context['current']['revision'] if context['current'] else None,
                        allowed_ship_ids=sorted(allowed))
            self.db.execute('INSERT INTO bot_referee_calls VALUES(?,?,?,?,?,?,?,?,?)',
                (actor, request, room, fingerprint, 'pending', time.time(), _json(meta), None, None))
            return actor, dict(meta=_json(meta), response=None, result=None, status='pending'), context

    def _referee_finish(self, actor, room, request, result, summary):
        self.db.execute("UPDATE bot_referee_calls SET status='done',result=? WHERE actor=? AND request=?",
                        (_json(result), actor, request))
        self.db.execute('INSERT OR IGNORE INTO bot_referee_audit(actor,room,request,summary,created) VALUES(?,?,?,?,?)',
                        (actor, room, request, _json(summary), time.time()))
        return result

    @staticmethod
    def _referee_unit(state, selector):
        if selector in state.ships:
            return selector
        found = [key for key, ship in state.ships.items() if ship.name == selector]
        if len(found) != 1:
            raise _error('referee_patch', '目标舰船未明确或名称不唯一，请提供精确船名或ID。')
        return found[0]

    @staticmethod
    def _referee_nested(original, edit, allowed, *, array=False):
        if array:
            if not isinstance(edit, list):
                raise _error('referee_patch', '武器修正须为按既有id索引的数组。')
            values = deepcopy(original)
            ids = {v['id']: v for v in values}
            seen = set()
            for item in edit:
                if (not isinstance(item, dict) or 'id' not in item or item['id'] not in ids
                        or item['id'] in seen or set(item) - allowed - {'id'} or len(item) == 1):
                    raise _error('referee_patch', '武器id、字段或数值不完整；不得修改原武器定义。')
                seen.add(item['id'])
                ids[item['id']].update({k:v for k,v in item.items() if k != 'id'})
            return values
        if original is None or not isinstance(edit, dict) or not edit or set(edit) - allowed:
            raise _error('referee_patch', '只能修正既有武器的运行字段，不得新增武器或修改原容量。')
        return original | edit

    def _referee_patch(self, state, changes):
        payload = state.model_dump(mode='json')
        if set(changes['game']) - GAME_FIELDS:
            raise _error('referee_patch', '请求包含不可修改的游戏身份、来源、RNG或其他受保护字段。')
        payload.update(deepcopy(changes['game']))
        touched = set()
        for edit in changes['ships']:
            sid = self._referee_unit(state, edit['ship_id'])
            if set(edit['fields']) & SHIP_LIFECYCLE_FIELDS:
                raise _error('referee_patch', '沉没、残骸、增援、撤离和编队成员属于关联生命周期，暂不支持直接修改；请使用原引擎流程或撤销。')
            if sid in touched or set(edit['fields']) - SHIP_FIELDS:
                raise _error('referee_patch', '舰船重复修正或包含不可修改的身份、来源和原能力字段。')
            touched.add(sid)
            target = payload['ships'][sid]
            for key, value in edit['fields'].items():
                if key == 'position' and (value is None or state.ships[sid].sunk or state.ships[sid].command_status == 'withdrawn'):
                    raise _error('referee_patch', '不能清空舰船位置，也不能直接移动已沉没或已撤离舰船。')
                if key == 'hull' and (state.ships[sid].sunk or type(value) is not int or value <= 0):
                    raise _error('referee_patch', '舰体修正仅支持非沉没舰的正整数；沉没和复活需要关联生命周期处理，暂不直接修改。')
                if key == 'position' and isinstance(value, str):
                    value = HexCoord.from_label(value).model_dump(mode='json')
                if key == 'position' and value is not None and (not isinstance(value, dict) or set(value) != {'q','r'}):
                    raise _error('referee_patch', '坐标仅允许完整q/r字段，不接受未知坐标字段。')
                if key in {'primary','secondary','torpedo'}:
                    value = self._referee_nested(target[key], value, WEAPON_FIELDS)
                elif key in {'gun_mounts','torpedo_launchers'}:
                    value = self._referee_nested(target[key], value, MOUNT_FIELDS if key == 'gun_mounts' else LAUNCHER_FIELDS, array=True)
                target[key] = deepcopy(value)
        # An old sealed command cannot silently survive a changed state/revision.
        payload['submitted_orders'] = {}
        if 'phase' in changes['game'] or 'turn' in changes['game']:
            payload['sealed_orders'] = {}
        try:
            patched = GameState.model_validate_json(_json(payload), strict=True)
        except (ValidationError, ValueError, TypeError):
            raise _error('referee_patch', '修正类型或必要值不完整，请提供严格合法的数值。') from None
        if not 1 <= patched.turn <= patched.max_turns or patched.max_turns < 1:
            raise _error('referee_patch', '回合必须在本局总回合范围内。')
        for mapping in (patched.visibility, patched.score, patched.hull_damage_taken):
            if set(mapping) != {'allies','axis'} or any(type(v) is not int or v < 0 for v in mapping.values()):
                raise _error('referee_patch', '阵营进度表需要双方完整且非负的整数值。')
        for sid in touched:
            ship, old = patched.ships[sid], state.ships[sid]
            if ship.position is not None and (not self.engine._coord_on_map(ship.position.q, ship.position.r,
                    columns=patched.map_columns, rows=patched.map_rows) or self.engine._terrain_impassable(patched, ship.position)):
                raise _error('referee_patch', '修正坐标必须位于当前地图合法海面。')
            if ship.hull > ship.max_hull or any(not 0 <= x <= len(row) for x,row in zip(ship.speed_damage_crossed, ship.speed_damage_track)):
                raise _error('referee_patch', '舰体或速度损伤值超过原始记录容量。')
            if any(x is not None and x > ship.initial_max_speed for x in (ship.current_speed, ship.previous_speed, ship.forced_speed)):
                raise _error('referee_patch', '运行速度不能超过原始最大MF。')
            if ship.fire_source_attacker is not None and ship.fire_source_attacker not in patched.ships:
                raise _error('referee_patch', '火灾来源舰船引用无效。')
            if ship.formation_id is not None:
                formation = patched.formations.get(ship.formation_id)
                if formation is None or formation.side != ship.side or sid not in formation.ship_ids:
                    raise _error('referee_patch', '编队引用必须与该舰及原编队成员一致。')
            for launcher in ship.torpedo_launchers:
                if launcher.loaded > launcher.torpedoes or launcher.reloads_remaining > launcher.reloads:
                    raise _error('referee_patch', '鱼雷装填或备用装填超过既有发射器容量。')
                if launcher.destroyed and (launcher.loaded or launcher.reloads_remaining or launcher.reload_turns_remaining):
                    raise _error('referee_patch', '毁坏发射器须同时明确清零装填和重装填状态。')
            if ship.torpedo and ship.torpedo.ammo != sum(v.loaded for v in ship.torpedo_launchers):
                raise _error('referee_patch', '鱼雷总弹数须与各发射器loaded一致，请给出完整修正，不猜分配。')
            for key in ('primary','secondary'):
                before, after = getattr(old,key), getattr(ship,key)
                if before and after and after.ammo != before.ammo:
                    raise _error('referee_patch', '该炮弹药没有规范容量字段，不能猜测或新增弹药记账；可修改既有炮位状态。')
        return patched, len(touched), len(changes['game'])

    def _referee_apply(self, actor_id, room, request, plan, meta, admins):
        action = plan['action']
        selected = meta['match_id']
        if action not in {'create','report','clarify'} and (selected is None or plan['match_id'] != selected):
            raise _error('referee_target', '请明确唯一对局ID；裁判不会猜选或改动其他对局。')
        if action == 'create':
            # Original create has its own atomic, persistent idempotency receipt.
            self._referee_admin(actor_id, room, admins)
            value = self.create(actor_id=actor_id, room_id=room, request_id=request+':referee-create', **plan['create'])
            result = {k:value[k] for k in ('match_id','revision','phase')}
            result.update(mutated=True, created=True, text='裁判已新建对局。\n'+
                f"对局 {value['match_id']} · 版本{value['revision']} · {value['phase']}\n创建席位固定为当前管理员；按正常流程继续操作。")
            with self._transaction():
                actor = self._referee_admin(actor_id, room, admins)
                return self._referee_finish(actor, room, request, result, dict(action=action, match_id=value['match_id'], outcome='applied'))
        with self._transaction():
            actor = self._referee_admin(actor_id, room, admins)
            saved = self.db.execute('SELECT result FROM bot_referee_calls WHERE actor=? AND request=?', (actor,request)).fetchone()
            if saved['result'] is not None:
                return json.loads(saved['result'])
            summary = dict(action=action, match_id=selected, outcome='applied')
            base = dict(match_id=selected, mutated=False, created=False)
            if action in {'report','clarify'}:
                summary['outcome'] = 'reported' if action == 'report' else 'clarified'
                result = base | dict(text=plan['message'] or '请明确对局、操作目标和完整修正值。')
                return self._referee_finish(actor, room, request, result, summary)
            row, state = self._load(selected, room)
            if row['revision'] != meta['revision']:
                raise _error('stale_revision', '思考期间对局已变化，本次未修改；请重新查询后再发裁判指令。')
            if action == 'advance':
                completed = 0
                for _ in range(plan['steps']):
                    if state.phase == Phase.COMPLETE:
                        break
                    from ..engine import ORDER_PHASES
                    if state.phase in ORDER_PHASES:
                        for side in Side:
                            if side.value not in state.submitted_orders:
                                batch = self._suggest(row, state, side)
                                valid = self.engine.submit_orders(state.game_id, batch)
                                if not valid.valid:
                                    raise _error('referee_advance', '原引擎未接受双方剩余命令，本次全部回滚。')
                    self._advance_decision(state)
                    row['revision'] += 1
                    completed += 1
                self._save(row,state,actor=actor,operation='referee_advance')
                summary['steps'] = completed
                text = f'裁判已按原引擎推进{completed}个决策阶段；保留原有已封存命令，剩余方由现有状态机生成。'
                mutated = bool(completed)
            elif action == 'patch':
                if any(self._referee_unit(state, edit['ship_id']) not in meta.get('allowed_ship_ids', []) for edit in plan['changes']['ships']):
                    raise _error('referee_target', '修正目标未出现在本次可见观察或用户明确点名中，请提供精确舰名或ID。')
                state, ships, fields = self._referee_patch(state, plan['changes'])
                self.engine.games[state.game_id] = state
                row['revision'] += 1
                self._save(row,state,actor=actor,operation='referee_patch')
                summary.update(targets=[{'ship':e['ship_id'],'fields':sorted(e['fields'])} for e in plan['changes']['ships']],
                               game_fields=sorted(plan['changes']['game']))
                text = f'裁判已修正{ships}艘舰船、{fields}项游戏进度；旧阶段封存已清除，请按新版本下令。'
                mutated = True
            else:
                snapshot = self.db.execute('SELECT * FROM bot_state_history WHERE room=? AND match=? AND consumed=0 ORDER BY id DESC LIMIT 1',
                                           (room,selected)).fetchone()
                if snapshot is None:
                    raise _error('referee_undo', '没有可撤销快照；服务启用前的旧操作没有历史，不会编造。')
                state = GameState.model_validate_json(snapshot['before_state'])
                self.engine.games[state.game_id] = state
                row['revision'] += 1
                self._save(row,state,actor=actor,operation='referee_undo',history=False)
                self.db.execute('UPDATE bot_state_history SET consumed=1 WHERE id=?', (snapshot['id'],))
                text, mutated = '裁判已撤销最近一步可用状态变更，恢复该步之前的状态与RNG快照；席位和权限不回退。', True
                summary['snapshot'] = snapshot['id']
            result = dict(match_id=selected, revision=row['revision'], phase=str(state.phase), mutated=mutated, created=False,
                          text=text+f"\n对局 {selected} · 版本{row['revision']} · {state.phase}")
            return self._referee_finish(actor, room, request, result, summary)

    def referee_run(self, match_id=None, *, actor_id, room_id, instruction, scope='group', request_id, llm, admins):
        actor, saved, context = self._referee_claim(match_id, actor_id, room_id, instruction, scope, request_id, admins)
        if saved['result'] is not None:
            return json.loads(saved['result'])
        meta = json.loads(saved['meta'])
        plan = None
        try:
            if context is not None:
                response = llm.generate(task='referee', context=context, instruction=instruction)
                if len(_json(response).encode()) > 128000:
                    raise _error('referee_format','裁判回令过大，本次未修改。')
                plan = self._referee_validate_plan(response)
                with self._transaction():
                    meta.update({k:response[k] for k in ('model','usage') if k in response})
                    self.db.execute("UPDATE bot_referee_calls SET status='prepared',response=? WHERE actor=? AND request=?",
                                    (_json(plan), actor, request_id))
                    self.db.execute('UPDATE bot_referee_calls SET meta=? WHERE actor=? AND request=?', (_json(meta),actor,request_id))
            else:
                plan = self._referee_validate_plan(json.loads(saved['response']))
            return self._referee_apply(actor_id, room_id, request_id, plan, meta, admins)
        except Exception as exc:
            from .service import ServiceError
            if plan and plan['action'] == 'create':
                # create committed independently. Never cache a false failure after it.
                with self.lock:
                    receipt = self.db.execute('SELECT 1 FROM bot_receipts WHERE actor=? AND request=?',
                        (actor, request_id+':referee-create')).fetchone()
                if receipt:
                    raise _error('referee_recovery', '对局已建立，回执尚待恢复；请重试同一消息，不会重复建局或调用模型。') from None
            if isinstance(exc, ServiceError):
                text = ('指定想定无法建立，本次未新建对局；请从想定目录选择。'
                        if exc.code == 'scenario' else exc.message)
            else:
                text = '裁判请求未完成或修正值无效，本次未修改；请明确完整数值后重试。'
            with self._transaction():
                actor = self._referee_admin(actor_id, room_id, admins)
                result = dict(match_id=meta['match_id'], mutated=False, created=False, text=text)
                summary = dict(action=plan['action'] if plan else 'clarify', match_id=meta['match_id'], outcome='rejected')
                return self._referee_finish(actor, room_id, request_id, result, summary)
