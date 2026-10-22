"""Private, persistent manual-order drafts over engine-owned candidate hints.

The menu is a representative command surface, not the whole legal action space.
Selections never submit orders, advance the engine or fill unselected units.
"""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import hashlib
import itertools
import json
import math

from ..models import HexCoord, MovementOrder, OrderBatch, Phase


PAGE_SIZE = 6


def _error(code, message):
    from .service import ServiceError
    return ServiceError(code, message)


def _short(value, size=90):
    text = str(value).replace('\n', ' ').replace('\r', ' ')
    return text if len(text) <= size else text[:size - 1] + '…'


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


class ManualOrdersMixin:
    def _init_manual(self):
        self.db.execute('''CREATE TABLE IF NOT EXISTS bot_manual_drafts(
            actor TEXT NOT NULL, room TEXT NOT NULL, match TEXT NOT NULL,
            revision INTEGER NOT NULL, phase TEXT NOT NULL, selections TEXT NOT NULL,
            PRIMARY KEY(actor,room,match,revision,phase))''')

    def _manual_current(self, match_id, actor_id, room_id, expected_revision=None, *, editable=False):
        self._identity(actor_id, room_id)
        actor = self.resolve_actor(actor_id, room_id)
        row, state = self._load(match_id, room_id, actor)
        side = self._side(row, actor)
        if expected_revision is not None and (type(expected_revision) is not int or expected_revision < 0
                                              or expected_revision != row['revision']):
            raise _error('stale_revision', '草稿版本已变化，请重新发送 /行动 查看当前版本。')
        if editable:
            if state.phase == Phase.COMPLETE:
                raise _error('complete', '对局已结束，不能再选择或提交行动。')
            if side.value in state.submitted_orders:
                raise _error('already_ready', '本阶段已封存，等待对手；请先刷新态势。')
        return actor, row, state, side

    def _manual_read(self, actor, room, match, revision, phase):
        saved = self.db.execute('SELECT selections FROM bot_manual_drafts WHERE actor=? AND room=? '
            'AND match=? AND revision=? AND phase=?', (actor, room, match, revision, str(phase))).fetchone()
        return json.loads(saved['selections']) if saved else {}

    def _manual_write(self, actor, room, match, revision, phase, selections):
        self.db.execute('INSERT INTO bot_manual_drafts VALUES(?,?,?,?,?,?) ON CONFLICT(actor,room,match,revision,phase) '
            'DO UPDATE SET selections=excluded.selections', (actor, room, match, revision, str(phase), _json(selections)))

    def _manual_valid(self, state, side, payload):
        """Authoritative validation on a clone; no original state or RNG changes."""
        original = self.engine.games[state.game_id]
        clone = state.model_copy(deep=True)
        clone.submitted_orders = {}
        self.engine.games[state.game_id] = clone
        try:
            batch = OrderBatch.model_validate({'side': side.value, 'phase': str(state.phase), **payload})
            return self.engine.validate_orders(state.game_id, batch).valid
        finally:
            self.engine.games[state.game_id] = original

    def _manual_catalog(self, row, state, side):
        original = self.engine.games[state.game_id]
        clone = state.model_copy(deep=True)
        clone.submitted_orders = {}
        self.engine.games[state.game_id] = clone
        try:
            observation = self.engine.observe(state.game_id, side).model_dump(mode='json')
            actions = self.engine.legal_actions(state.game_id, side)
            hint = next((a.schema_hint for a in actions if a.kind == 'submit_phase_orders'), {})
            return self._manual_choices(row, clone, side, observation, hint)
        finally:
            self.engine.games[state.game_id] = original

    def _manual_choices(self, row, state, side, observation, hint):
        visible = {s['id']: s for s in observation.get('ships', [])}
        own = {key: value for key, value in visible.items() if value['side'] == side.value}
        formations = {f['id']: f for f in observation.get('formations', []) if f['side'] == side.value}
        groups = OrderedDict()
        identifiers = set()

        def ship_name(identifier):
            return _short(visible.get(identifier, {}).get('name', identifier), 32)

        def add(slot, payload, label, unit_id='', unit_name='', aliases=()):
            identifier = hashlib.sha256(_json({'match': row['id'], 'revision': row['revision'],
                'phase': str(state.phase), 'side': side.value, 'slot': slot, 'payload': payload}).encode()).hexdigest()[:12]
            if identifier in identifiers:
                return
            identifiers.add(identifier)
            value = dict(choice_id=identifier, slot=slot, payload=payload, label=_short(label, 130),
                         unit_id=unit_id, unit_name=_short(unit_name, 40), aliases=list(aliases))
            groups.setdefault(unit_id or '_phase', []).append(value)

        if self._manual_valid(state, side, {}):
            add('_empty', {}, '本阶段不下达行动（已通过引擎空命令校验）', unit_name='整阶段')
        phase = str(state.phase)
        if phase == 'formation_setup':
            layouts = hint.get('suggested_formations', [])
            if layouts:
                names = [f.get('name', f['formation_id']) for f in layouts]
                members = [s for f in layouts for s in f['ship_ids']]
                label = '采用默认编队部署：' + '；'.join(
                    f"{f.get('name',f['formation_id'])}，领舰{ship_name(f['leader_id'])}，{len(f['ship_ids'])}舰，间距{f['spacing']}"
                    for f in layouts)
                add('formation_setup', {'formation_setup': layouts}, label, unit_id='编队部署',
                    unit_name='、'.join(names), aliases=names + members + [ship_name(s) for s in members])
        elif phase == 'movement_planning':
            movement = {item['ship_id']: item for item in hint.get('movement_candidates', []) if item['ship_id'] in own}
            if observation.get('realistic_command'):
                suggested = hint.get('suggested_formation_movement', [])
                for base in suggested:
                    fid = base['formation_id']
                    formation = formations.get(fid, {})
                    name = formation.get('name', fid)
                    leader = formation.get('leader_id')
                    route_candidates = movement.get(leader, {}).get('reachable', [])
                    routes = [dict(base)] + [dict(base, leader_plan=r['plan']) for r in route_candidates if r.get('plan')]
                    for order in routes:
                        trial = [order if item['formation_id'] == fid else item for item in suggested]
                        if not self._manual_valid(state, side, {'formation_movement': trial}):
                            continue
                        plan = order.get('leader_plan', '0')
                        decision = order.get('speed_decision') or {}
                        detach = decision.get('detach_ship_ids', [])
                        warning = '；永久撤队：' + '、'.join(ship_name(s) for s in detach) if detach else ''
                        if decision.get('emergency_stop'):
                            warning += '；整队急停'
                        speed = self.engine.movement_cost(plan, self.engine.movement_commands(
                            MovementOrder(ship_id=leader, plan=plan)))
                        add('formation_movement:' + fid, {'formation_movement': [order]},
                            f'{name}：领舰路径{plan}，{speed}MF{warning}', fid, name,
                            [leader or '', ship_name(leader), *formation.get('ship_ids', [])])
            else:
                for sid, item in movement.items():
                    for route in item.get('reachable', []):
                        plan = route.get('plan')
                        if not plan:
                            continue
                        add('movement:' + sid, {'movement': [{'ship_id': sid, 'plan': plan}]},
                            f"{ship_name(sid)}：{plan} → {route.get('label','目标格')}，{route.get('cost','?')}MF",
                            sid, ship_name(sid))
        elif phase == 'torpedo_planning':
            for item in hint.get('torpedo_candidates', []):
                sid = item['ship_id']
                if sid not in own or item.get('blocked_reason'):
                    continue
                for launcher, position, setting in itertools.product(item.get('launchers', []), item.get('launch_positions', []), item.get('settings', [])):
                    for arc, angle, count in itertools.product(launcher.get('sides', []), launcher.get('angles', []), range(1, launcher.get('loaded', 0) + 1)):
                        order = {'ship_id': sid, 'launcher_id': launcher['launcher_id'], 'launch_at_mf': position['mf'],
                                 'launch_hex': position['hex'], 'launch_side': arc, 'launch_angle': angle,
                                 'setting_index': setting['index'], 'count': count}
                        name = ship_name(sid)
                        label = f"{name}/{launcher['launcher_id']}：MF{position['mf']}在{HexCoord(**position['hex']).label}向{'左舷' if arc=='port' else '右舷'}{angle}发{count}枚，档位{setting['index']}"
                        add('torpedoes:' + sid + ':' + launcher['launcher_id'], {'torpedoes': [order]}, label, sid, name)
        elif phase == 'gunnery':
            for item in hint.get('gunnery_candidates', []):
                sid = item['ship_id']
                if sid not in own or item.get('blocked_reason'):
                    continue
                for target in item.get('targets', []):
                    tid = target['target_id']
                    if tid not in visible:
                        continue
                    for mount in target.get('mount_ids', []):
                        add('gunnery:' + sid + ':' + mount, {'gunnery': [{'ship_id': sid,
                            'mounts': [{'mount_id': mount, 'target_id': tid}]}]},
                            f"{ship_name(sid)}/{mount}：射击{ship_name(tid)}，距离{target.get('range','?')}格", sid, ship_name(sid))
        elif phase == 'reinforcement':
            available = hint.get('reinforcement_candidates', {})
            for item in available.get('ships', []) if available.get('group_available') else []:
                sid = item['ship_id']
                if sid not in own:
                    continue
                entries = item.get('entry_hexes', available.get('entry_hexes', []))
                speed_max = item.get('max_speed', own[sid].get('max_speed'))
                heading = own[sid].get('heading')
                if speed_max is None or heading is None:
                    continue
                for entry, speed in itertools.product(entries, sorted({0, speed_max})):
                    position = HexCoord.from_label(entry) if isinstance(entry, str) else HexCoord(**entry)
                    order = {'ship_id': sid, 'entry_hex': position.model_dump(mode='json'), 'heading': heading, 'speed': speed}
                    add('reinforcements:' + sid, {'reinforcements': [order]},
                        f"{ship_name(sid)}：从{position.label}入场，航向{heading}，{speed}MF", sid, ship_name(sid))
        # Round-robin units so the first global page doesn't hide all other ships.
        return [choice for row_choices in itertools.zip_longest(*groups.values()) for choice in row_choices if choice]

    @staticmethod
    def _manual_payload(selections, side, phase):
        payload = {'side': side.value if hasattr(side, 'value') else side, 'phase': str(phase)}
        guns = OrderedDict()
        for choice in selections.values():
            for field, orders in choice['payload'].items():
                if field == 'gunnery':
                    for order in orders:
                        value = guns.setdefault(order['ship_id'], {'ship_id': order['ship_id'], 'mounts': []})
                        value['mounts'].extend(order['mounts'])
                else:
                    payload.setdefault(field, []).extend(deepcopy(orders))
        if guns:
            payload['gunnery'] = list(guns.values())
        return payload

    def manual_actions(self, match_id, actor_id, room_id, page=1, unit=None):
        if type(page) is not int or page < 1:
            raise _error('manual_page', '页码必须是正整数。')
        with self._transaction():
            actor, row, state, side = self._manual_current(match_id, actor_id, room_id, editable=True)
            choices = self._manual_catalog(row, state, side)
            units = OrderedDict((c['unit_id'], c['unit_name']) for c in choices if c['unit_id'])
            chosen_unit = None
            if unit:
                wanted = str(unit).casefold()
                matches = {c['unit_id'] for c in choices if wanted in {str(v).casefold() for v in
                    [c['unit_id'], c['unit_name'], *c['aliases']]} and c['unit_id']}
                if not matches:
                    raise _error('manual_unit', '未找到本方可选舰船或编队。请先发送 /行动 查看单位索引。')
                chosen_unit = next(iter(matches)) if len(matches) == 1 else None
                if chosen_unit is None:
                    raise _error('manual_unit', '名称对应多个单位，请使用单位ID筛选。')
                choices = [c for c in choices if c['unit_id'] == chosen_unit]
            pages = max(1, math.ceil(len(choices) / PAGE_SIZE))
            if page > pages:
                raise _error('manual_page', f'没有第{page}页，当前共{pages}页。')
            selected = choices[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]
            revision = row['revision']
            lines = [f'手动行动 · 版本{revision} · 第{page}/{pages}页（{len(choices)}个代表选项）',
                     '选择只存草稿；未选单位不会代填。组合合法性以提交时引擎裁决为准。']
            if units and not unit:
                lines.append('单位索引：' + _short('、'.join(units.values()), 170))
                first_unit = next(iter(units))
                lines.append(f'筛选示例：/行动 {match_id} {first_unit} 页1')
            for choice in selected:
                lines.append(choice['choice_id'] + ' ' + choice['label'])
            if not selected:
                lines.append('当前没有可选代表行动；请查看态势或等待阶段更新。')
            if selected:
                lines.append(f"选择示例：/选择 {revision} {selected[0]['choice_id']} {match_id}")
            if page < pages:
                lines.append(f"下一页：/行动 {match_id}" + (f' {chosen_unit}' if chosen_unit else '') + f' 页{page+1}')
            lines.extend([f'查看草稿：/草稿 {match_id}', f'完成后提交：/提交 {revision} {match_id}'])
            text = '\n'.join(lines)
            if len(text) > 1400:
                raise _error('manual_output', '当前选项说明过长，请按单位筛选后重试。')
            return dict(match_id=match_id, revision=revision, phase=str(state.phase), page=page, pages=pages,
                        total=len(choices), unit=chosen_unit, text=text,
                        choices=[{k: c[k] for k in ('choice_id','label','unit_id','unit_name')} for c in selected])

    def _manual_draft_result(self, actor, row, state, side, page=1):
        values = self._manual_read(actor, row['room'], row['id'], row['revision'], state.phase)
        pages = max(1, math.ceil(len(values) / PAGE_SIZE))
        if type(page) is not int or not 1 <= page <= pages:
            raise _error('manual_page', f'草稿页码须在1至{pages}之间。')
        entries = list(values.values())[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]
        sealed = side.value in state.submitted_orders
        status = '本阶段已封存' if sealed else ('本局已结束' if state.phase == Phase.COMPLETE else '尚未提交')
        lines = [f"本方手动草稿 · 版本{row['revision']} · 已选{len(values)}项（{status}） · 第{page}/{pages}页"]
        lines += [f'{i}. {c["label"]}' for i, c in enumerate(entries, (page - 1) * PAGE_SIZE + 1)]
        if not values:
            lines.append('当前版本没有草稿。' if sealed or state.phase == Phase.COMPLETE else
                         '草稿为空；先 /行动 查看选项，选择不会立即推进。')
        if page < pages:
            lines.append(f"下一页：/草稿 {row['id']} 页{page+1}")
        if not sealed and state.phase != Phase.COMPLETE:
            lines += ['未选行动不会由状态机补齐；漏选必需单位时提交会拒绝。',
                      f"提交：/提交 {row['revision']} {row['id']}", f"清空：/清空 {row['revision']} {row['id']}"]
        else:
            lines.append(f"请查询态势：/态势 {row['id']}")
        text = '\n'.join(lines)
        if len(text) > 1400:
            raise _error('manual_output', '草稿说明过长，请联系管理员。')
        return dict(match_id=row['id'], revision=row['revision'], phase=str(state.phase), selection_count=len(values),
                    page=page, pages=pages,
                    selections=[{k: c[k] for k in ('choice_id','label','unit_id','unit_name')} for c in entries], text=text)

    def manual_draft(self, match_id, actor_id, room_id, page=1):
        with self._transaction():
            actor, row, state, side = self._manual_current(match_id, actor_id, room_id)
            return self._manual_draft_result(actor, row, state, side, page)

    def manual_choose(self, match_id, actor_id, room_id, expected_revision, choice_id, request_id):
        self._identity(actor_id, room_id)
        with self._transaction():
            actor = self.resolve_actor(actor_id, room_id)
            fp, cached = self._cached(actor, request_id, dict(op='manual_choose', match=match_id, room=room_id,
                                                           revision=expected_revision, choice=choice_id))
            if cached is not None:
                return cached
            actor, row, state, side = self._manual_current(match_id, actor, room_id, expected_revision, editable=True)
            choice = next((c for c in self._manual_catalog(row, state, side) if c['choice_id'] == choice_id), None)
            if choice is None:
                raise _error('manual_choice', '此选项不属于本方当前阶段，请重新发送 /行动。')
            values = self._manual_read(actor, room_id, match_id, row['revision'], state.phase)
            replaced = values.get(choice['slot'])
            removed = len(values) if choice['slot'] == '_empty' else 0
            if choice['slot'] == '_empty':
                values = {}
            else:
                values.pop('_empty', None)
            values[choice['slot']] = choice
            self._manual_write(actor, room_id, match_id, row['revision'], state.phase, values)
            result = self._manual_draft_result(actor, row, state, side)
            note = '已替换同一单位/武器的旧选择。' if replaced else '已加入本阶段草稿。'
            if removed:
                note = f'已明确选择本阶段不行动，取消此前{removed}项草稿。'
            result['text'] = (f"已选择：{choice['label']}\n{note}尚未提交，也未推进。\n"
                f"草稿共{len(values)}项；查看全部：/草稿 {match_id}\n"
                f"继续选行动：/行动 {match_id}\n完成后提交：/提交 {row['revision']} {match_id}")
            return self._receipt(actor, request_id, fp, result)

    def manual_clear(self, match_id, actor_id, room_id, expected_revision, request_id):
        self._identity(actor_id, room_id)
        with self._transaction():
            actor = self.resolve_actor(actor_id, room_id)
            fp, cached = self._cached(actor, request_id, dict(op='manual_clear', match=match_id, room=room_id, revision=expected_revision))
            if cached is not None:
                return cached
            actor, row, state, side = self._manual_current(match_id, actor, room_id, expected_revision, editable=True)
            self._manual_write(actor, room_id, match_id, row['revision'], state.phase, {})
            return self._receipt(actor, request_id, fp, self._manual_draft_result(actor, row, state, side))

    def manual_submit(self, match_id, actor_id, room_id, expected_revision, request_id):
        if type(expected_revision) is not int or expected_revision < 0:
            raise _error('revision', '必须提供有效版本号，请先查看 /草稿。')
        self._identity(actor_id, room_id)
        # End the read transaction before submit starts its authoritative write;
        # the same RLock spans both calls. submit checks revisions/receipts again.
        with self.lock:
            with self._transaction():
                actor, row, state, side = self._manual_current(match_id, actor_id, room_id)
                saved = self.db.execute('SELECT phase,selections FROM bot_manual_drafts WHERE actor=? AND room=? '
                    'AND match=? AND revision=?', (actor, room_id, match_id, expected_revision)).fetchone()
                if saved is None or not json.loads(saved['selections']):
                    raise _error('manual_empty', '该版本没有已选择的草稿。请先 /行动，再 /选择；空阶段也需明确选择“不行动”。')
                payload = self._manual_payload(json.loads(saved['selections']), side, saved['phase'])
                guard = (saved['phase'], hashlib.sha256(saved['selections'].encode()).hexdigest())
            return self.submit(match_id, actor_id=actor_id, room_id=room_id, orders=payload,
                               expected_revision=expected_revision, request_id=request_id, manual_guard=guard)
