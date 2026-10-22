"""Seat-bound LLM commands; model I/O never holds the game/SQLite lock."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import time

from ..models import OrderBatch, Phase
from .qq_guidance import status_text


def _error(code, message):
    from .service import ServiceError
    return ServiceError(code, message)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _strict_fields(value, schema, definitions):
    if '$ref' in schema:
        schema = definitions[schema['$ref'].split('/')[-1]]
    for branch in schema.get('anyOf', []):
        if value is None and branch.get('type') == 'null':
            return
        if branch.get('type') != 'null':
            _strict_fields(value, branch, definitions)
    if isinstance(value, dict) and 'properties' in schema:
        if set(value) - set(schema['properties']):
            raise ValueError('unknown order field')
        for key, item in value.items():
            _strict_fields(item, schema['properties'][key], definitions)
    if isinstance(value, list) and 'items' in schema:
        for item in value:
            _strict_fields(item, schema['items'], definitions)


def _observation(view):
    """Explicit contract; no world objects, identity, raw events or future fields."""
    source = view.model_dump(mode='json')
    metadata = ('scenario_id', 'scenario_title', 'turn', 'max_turns', 'phase',
                'visibility', 'map_columns', 'map_rows', 'printed_columns', 'printed_rows',
                'realistic_command', 'command_delay_mode', 'score', 'winner',
                'enabled_optional_rules', 'rule_blockers')
    ship_fields = ('id', 'name', 'side', 'ship_type', 'identified', 'position', 'heading',
                   'current_speed', 'max_speed', 'min_legal_speed', 'max_legal_speed',
                   'hull', 'max_hull', 'fire_markers', 'fired', 'sunk', 'formation_id',
                   'command_status', 'turn_limit_degrees', 'forced_straight_turns',
                   'forced_circle_turns', 'forced_turn_side', 'forced_speed')
    result = {key: source[key] for key in metadata}
    result['ships'] = []
    for ship in source['ships']:
        item = {key: ship[key] for key in ship_fields}
        if ship['side'] == source['side']:
            item.update({key: ship[key] for key in ('gun_mounts', 'torpedo_launchers')})
        if not ship['identified']:
            item.update(name='敌舰', ship_type='unknown')
        result['ships'].append(item)
    formation_fields = ('id', 'name', 'side', 'ship_ids', 'leader_id', 'flagship_id',
                        'reserve_flagship_id', 'spacing', 'heading', 'speed', 'status',
                        'disruption_turn', 'locked_heading', 'locked_speed', 'guide_trail')
    result['formations'] = [{key: f[key] for key in formation_fields}
                            for f in source['formations'] if f['side'] == source['side']]
    result['markers'] = [{key: m[key] for key in ('kind', 'position', 'heading')}
                         for m in source['markers']]
    result['torpedo_tracks'] = [{key: t[key] for key in
        ('side', 'position', 'heading', 'speed_cycle', 'range_remaining', 'distance_travelled', 'salvo_size')}
        for t in source['torpedo_tracks']]
    result['wrecks'] = [{'position': w['position']} for w in source['wrecks']]
    # Only public-result messages from observe(); payloads/commands/dice omitted.
    result['recent_events'] = [{key: e[key] for key in ('turn', 'phase', 'type', 'message')}
        for e in source['recent_events'][-12:]
        if e['type'] not in {'orders_submitted', 'game_created'}
        and not e['type'].startswith(('command_', 'formation_agent_', 'mission_order'))
        and not e['payload'].get('secret_side') and not e['payload'].get('debug_only')]
    return result


class LLMCommandsMixin:
    def _init_llm(self):
        self.db.execute('''CREATE TABLE IF NOT EXISTS bot_llm_calls(
            actor TEXT NOT NULL, request TEXT NOT NULL, room TEXT NOT NULL,
            fingerprint TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL,
            meta TEXT NOT NULL, response TEXT, result TEXT,
            PRIMARY KEY(actor,request))''')

    def llm_matches(self, actor_id, room_id, *, public=False):
        self._identity(actor_id, room_id)
        if not public:
            return self.matches(actor_id, room_id)
        with self._transaction():
            result = []
            for item in self.db.execute('SELECT id FROM bot_matches WHERE room=?', (room_id,)).fetchall():
                row, state = self._load(item['id'], room_id)
                result.append(dict(match_id=row['id'], complete=state.phase == Phase.COMPLETE))
            return result

    def _llm_snapshot(self, row, state, actor, task, scope):
        from .public_view import public_observation
        public = scope == 'group' and task == 'report' and row['opponent'] == 'pvp'
        if public:
            side = None
        elif scope == 'group' and task == 'report':
            side = self._pve_player_side(row)
        else:
            side = self._side(row, actor)
        clone = state.model_copy(deep=True)
        clone.submitted_orders = {}
        self.engine.games[state.game_id] = clone
        try:
            view = public_observation(self.engine, clone) if public else self.engine.observe(clone.game_id, side)
            context = dict(revision=row['revision'], phase=str(state.phase), turn=state.turn,
                mode=row['mode'], opponent=row['opponent'], side=side.value if side else None,
                view='shared' if public else 'player', observation=_observation(view))
            if task == 'orders':
                context['legal_actions'] = [a.model_dump(mode='json') for a in self.engine.legal_actions(clone.game_id, side)]
                context['order_schema'] = OrderBatch.model_json_schema()
            return deepcopy(context)
        finally:
            self.engine.games[state.game_id] = state

    def _llm_claim(self, match_id, actor_id, room_id, task, instruction, scope, request_id):
        self._identity(actor_id, room_id)
        if task not in {'report', 'orders'} or scope not in {'group', 'c2c'}:
            raise _error('llm_parameters', 'LLM指令类型无效。')
        if not isinstance(instruction, str) or len(instruction) > 1600 or (task == 'orders' and not instruction.strip()):
            raise _error('llm_parameters', '请用1600字以内描述本阶段的命令。')
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 200:
            raise _error('request_id', 'LLM请求需要唯一消息编号。')
        with self._transaction():
            actor = self.resolve_actor(actor_id, room_id)
            fingerprint = self._fingerprint(dict(match=match_id, room=room_id, task=task,
                scope=scope, instruction_sha256=hashlib.sha256(instruction.encode()).hexdigest()))
            saved = self.db.execute('SELECT * FROM bot_llm_calls WHERE actor=? AND request=?', (actor, request_id)).fetchone()
            if saved:
                if saved['fingerprint'] != fingerprint:
                    raise _error('idempotency_conflict', '请求编号已用于不同LLM操作。')
                if saved['status'] == 'pending':
                    raise _error('llm_pending', '这条LLM请求正在处理或上次处理已中断，不会重复调用模型；稍后查询战况，必要时发送一条新指令。')
                return actor, dict(saved), None
            row, state = self._load(match_id, room_id, actor if task == 'orders' or scope == 'c2c' else None)
            if task == 'orders':
                side = self._side(row, actor)
                if len(row['seats']) != 2:
                    raise _error('waiting', '等待另一位玩家加入。')
                if state.phase == Phase.COMPLETE:
                    raise _error('complete', '对局已结束，不能继续下令。')
                if side.value in state.submitted_orders:
                    raise _error('already_ready', '你本阶段已封存命令，请等待对手并刷新态势。')
            now = time.time()
            active = self.db.execute("SELECT count(*) FROM bot_llm_calls WHERE room=? AND status='pending' AND created>?", (room_id, now-120)).fetchone()[0]
            recent = self.db.execute('SELECT count(*) FROM bot_llm_calls WHERE actor=? AND room=? AND created>?', (actor, room_id, now-60)).fetchone()[0]
            if active >= 2 or recent >= 6:
                raise _error('llm_rate', 'LLM请求较多，请稍后再试；本次没有调用模型。')
            context = self._llm_snapshot(row, state, actor, task, scope)
            meta = {key: value for key, value in context.items() if key not in {'observation', 'legal_actions', 'order_schema'}}
            meta.update(match_id=match_id, scope=scope, task=task)
            self.db.execute('INSERT INTO bot_llm_calls VALUES(?,?,?,?,?,?,?,?,?)',
                (actor, request_id, room_id, fingerprint, 'pending', now, _json(meta), None, None))
            saved = dict(status='pending', meta=_json(meta), fingerprint=fingerprint, response=None, result=None)
            return actor, saved, context

    def _llm_finish(self, actor, request_id, value):
        with self._transaction():
            saved = self.db.execute('SELECT result FROM bot_llm_calls WHERE actor=? AND request=?', (actor, request_id)).fetchone()
            if saved['result'] is not None:
                return json.loads(saved['result'])
            self.db.execute("UPDATE bot_llm_calls SET status='done', result=? WHERE actor=? AND request=?",
                (_json(value), actor, request_id))
            return value

    def llm_run(self, match_id, actor_id, room_id, task, instruction='', scope='group', request_id=None, llm=None):
        actor, saved, context = self._llm_claim(match_id, actor_id, room_id, task, instruction, scope, request_id)
        if saved['result'] is not None:
            return json.loads(saved['result'])
        meta = json.loads(saved['meta'])
        base = dict(match_id=match_id, revision=meta['revision'], phase=meta['phase'],
            opponent=meta['opponent'], submitted=False)
        if context is not None:
            try:
                response = llm.generate(task=task, context=context, instruction=instruction)
                if not isinstance(response, dict) or len(_json(response).encode()) > 128000:
                    raise ValueError('invalid model response')
                with self._transaction():
                    self.db.execute("UPDATE bot_llm_calls SET status='prepared',response=? WHERE actor=? AND request=?",
                        (_json(response), actor, request_id))
            except Exception as exc:
                from .llm_client import BotLLMError
                message = exc.message if isinstance(exc, BotLLMError) else 'LLM请求未完成，未执行命令；请稍后重试。'
                return self._llm_finish(actor, request_id, base | dict(text=message))
        else:
            response = json.loads(saved['response'])
        if task == 'report':
            report, advice = response.get('report'), response.get('advice')
            if (not isinstance(report, str) or not 1 <= len(report) <= 1000 or not isinstance(advice, list)
                    or len(advice) > 3 or any(not isinstance(a, str) or len(a)>200 for a in advice)
                    or len(report)+sum(map(len, advice)) > 1360):
                return self._llm_finish(actor, request_id, base | dict(text='LLM战报格式无效，本次未作任何操作。'))
            label = '双方公共视角' if meta['view'] == 'shared' else '玩家受限视角'
            text = f"LLM参谋 · 版本{meta['revision']} · {meta['phase']} · {label}\n{report}"
            if advice:
                text += '\n建议：\n'+'\n'.join(f'{i}. {item}' for i,item in enumerate(advice, 1))
            text += '\n以上为模型判断，未下达命令。'
            return self._llm_finish(actor, request_id, base | dict(text=text))
        orders, clarification = response.get('orders'), response.get('clarification', '')
        if not isinstance(orders, dict) or clarification:
            detail = ('请明确本阶段要让哪些舰船做什么，或私聊查看本方态势后重述。'
                if scope == 'group' and meta['opponent'] == 'pvp' else
                (clarification[:600] if isinstance(clarification, str) else '请明确舰船、动作与目标。'))
            return self._llm_finish(actor, request_id, base | dict(text='需要澄清，尚未执行：\n'+detail))
        try:
            schema = OrderBatch.model_json_schema()
            _strict_fields(orders, schema, schema['$defs'])
            if orders.get('side', meta['side']) != meta['side'] or orders.get('phase', meta['phase']) != meta['phase']:
                raise ValueError('identity/phase mismatch')
            confirmation = orders.get('confirmation')
            if confirmation is not None and (not isinstance(confirmation, dict) or 'ready' not in confirmation):
                raise ValueError('implicit confirmation')
            explicit = any(isinstance(value, list) and value for key,value in orders.items()
                           if key not in {'side', 'phase', 'confirmation'})
            if not explicit and (not isinstance(confirmation, dict) or confirmation.get('ready') is not True):
                raise ValueError('no explicit action or confirmation')
            OrderBatch.model_validate(orders | dict(side=meta['side'], phase=meta['phase']))
        except (ValueError, TypeError, RecursionError):
            return self._llm_finish(actor, request_id, base | dict(text='LLM回令字段或格式无效，未执行命令；请明确当前阶段的动作后重述。'))
        try:
            result = self.submit(match_id, actor_id=actor_id, room_id=room_id, orders=orders,
                expected_revision=meta['revision'], request_id=request_id+':llm-submit')
        except Exception as exc:
            from .service import ServiceError
            if not isinstance(exc, ServiceError):
                raise
            message = ('思考期间阶段已变化，本次命令未执行。请刷新战况后重新下令。'
                       if exc.code in {'stale_revision', 'already_ready'} else
                       '原引擎未接受这批命令，本次未执行。请明确本阶段的舰船、动作与目标后重述，或使用私聊手动指令。')
            return self._llm_finish(actor, request_id, base | dict(text=message))
        text = 'LLM已转译并通过原引擎校验。\n'+status_text(result)
        if scope == 'group' and meta['opponent'] == 'pvp':
            text += '\n本方订单已封存；群回执不展开私有战术。'
        else:
            fields = {'movement':'逐舰机动','formation_movement':'编队机动','formation_setup':'编队部署',
                'gunnery':'炮击','torpedoes':'雷击','reinforcements':'增援','contacts':'接触部署',
                'smoke':'烟幕','illumination':'照明','searchlights':'探照灯'}
            parts = [f'{label}{len(orders[key])}项' for key,label in fields.items() if isinstance(orders.get(key),list) and orders[key]]
            text += '\n已提交：'+('、'.join(parts) if parts else '本阶段确认/不行动')
            text += '\n战况：\n'+result.get('summary','')[:700]
        text += '\n本次只提交一个决策阶段。继续用 /参谋 或 /战况 查询。'
        value = {key: result[key] for key in ('match_id','revision','phase','turn','opponent','advanced')}
        value.update(text=text, submitted=True)
        return self._llm_finish(actor, request_id, value)
