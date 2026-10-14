"""Thread/task-local adjudication tables selected by the explicit game state.

Leaf helpers without a state inherit their caller's context. Direct state-based
entry points set/reset a ContextVar, never a process-global mutable RuleData.
"""
from contextvars import ContextVar
from functools import wraps
import inspect

active_state = ContextVar("ibs_rules_state", default=None)


def pack(value):
    if isinstance(value, dict):
        return {"$map": [[k, pack(v)] for k,v in value.items()]}
    if isinstance(value, (list, tuple)):
        return [pack(v) for v in value]
    return value


def unpack(value):
    if isinstance(value, dict) and set(value) == {"$map"}:
        return {k: unpack(v) for k,v in value["$map"]}
    if isinstance(value, list):
        return [unpack(v) for v in value]
    return value


def bind_engine(cls):
    for name, method in list(vars(cls).items()):
        if not inspect.isfunction(method):
            continue
        parameters = list(inspect.signature(method).parameters)
        key = "state" if "state" in parameters else ("game_id" if "game_id" in parameters else None)
        if key is None:
            continue
        index = parameters.index(key)
        def wrap(fn, index, key):
            @wraps(fn)
            def scoped(*args, **kwargs):
                value = kwargs.get(key, args[index] if len(args) > index else None)
                state = value if key == "state" else args[0].games.get(value)
                if state is None or active_state.get() is state:
                    return fn(*args, **kwargs)
                token = active_state.set(state)
                try:
                    return fn(*args, **kwargs)
                finally:
                    active_state.reset(token)
            return scoped
        setattr(cls, name, wrap(method, index, key))
    return cls
