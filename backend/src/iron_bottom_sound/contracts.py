"""CD-6 research hooks: contract state and the incentive ledger.

Interface only
--------------
The v2.2 plan is explicit: no RL, GNN or Transformer implementation yet, expose
interfaces only.  This module therefore provides **data structures and a
read-only ledger**, plus the validation a future consumer will need.  It
implements no learning rule, no optimiser and no policy update: nothing here
changes a decision.  ``FormationPolicy.act`` already accepts a ``contract_state``
argument, so a future incentive-aware policy has its slot without a signature
change.

Why a ledger rather than a reward function
------------------------------------------
"Reward" would imply a designed objective and a training signal; neither exists at
this stage.  The ledger records what actually happened — a transfer, an
observation of a deviation, a violated agreement — with its turn, its source
message and its reason, so a later researcher can *derive* a reward and defend
it, or discover that the data does not support one.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .models import ContractState, ContractTerm, GameState, LedgerEntry, MissionOrder, Side

RULE_CONTRACT = "IBS-R-CD-07"


def contract_from_order(order: MissionOrder) -> ContractState:
    """Derive a contract proposal from a mission order.

    Structural only: each coordination measure and each risk constraint becomes a
    term, with the formation as obligor and the fleet as beneficiary.  No weight is
    invented — ``weight`` stays 0.0 until a researcher declares one, because an
    unsourced weight is exactly the kind of number this project refuses.
    """
    terms = [
        ContractTerm(
            term_id=f"{order.order_id}-coord-{index}",
            description=measure,
            obligor=order.formation_id,
            beneficiary=order.issued_by,
            measurable="coordination measure stated in the order",
        )
        for index, measure in enumerate(order.coordination_measures)
    ]
    terms.extend(
        ContractTerm(
            term_id=f"{order.order_id}-risk-{index}",
            description=constraint,
            obligor=order.formation_id,
            beneficiary=order.issued_by,
            measurable="risk constraint stated in the order",
        )
        for index, constraint in enumerate(order.risk_constraints)
    )
    return ContractState(
        side=order.side,
        formation_id=order.formation_id,
        order_id=order.order_id,
        terms=terms,
        agreed_turn=order.confirmed_turn,
    )


def validate_contract(contract: ContractState) -> list[str]:
    errors: list[str] = []
    if contract.agreed_turn is None:
        errors.append("a contract is only in force once its order is confirmed")
    for term in contract.terms:
        if not term.description.strip():
            errors.append(f"{term.term_id}: empty description")
        if not term.obligor or not term.beneficiary:
            errors.append(f"{term.term_id}: obligor and beneficiary are required")
        if term.obligor == term.beneficiary:
            errors.append(f"{term.term_id}: obligor and beneficiary must differ")
    return errors


def contract_state(state: GameState, formation_id: str) -> dict[str, Any]:
    """The ``contract_state`` payload a policy receives (empty until declared)."""
    record = _contracts(state).get(formation_id)
    if record is None:
        return {"formation_id": formation_id, "terms": [], "in_force": False}
    return {**record.model_dump(mode="json"), "in_force": record.agreed_turn is not None}


def _contracts(state: GameState) -> dict[str, ContractState]:
    mode = getattr(state, "command_delay", None)
    if mode is None:
        return {}
    return {item.formation_id: item for item in mode.contracts}


def declare_contract(state: GameState, contract: ContractState) -> list[str]:
    """Register a contract; returns the validation errors and refuses to store one."""
    errors = validate_contract(contract)
    if errors:
        return errors
    mode = getattr(state, "command_delay", None)
    if mode is None:
        return ["contracts exist only in command delay mode"]
    existing = [item for item in mode.contracts if item.formation_id != contract.formation_id]
    mode.contracts = existing + [contract]
    return []


def record(state: GameState, entry: LedgerEntry) -> LedgerEntry:
    """Append one observable event to the incentive ledger."""
    mode = getattr(state, "command_delay", None)
    if mode is not None:
        mode.ledger.append(entry)
    return entry


def ledger(state: GameState) -> list[LedgerEntry]:
    mode = getattr(state, "command_delay", None)
    return list(mode.ledger) if mode is not None else []


def ledger_summary(state: GameState) -> dict[str, Any]:
    """Read-only digest: how many entries of each kind, per formation."""
    summary: dict[str, dict[str, int]] = {}
    for entry in ledger(state):
        bucket = summary.setdefault(entry.formation_id, {})
        bucket[entry.kind] = bucket.get(entry.kind, 0) + 1
    return {
        "entries": len(ledger(state)),
        "by_formation": {key: dict(sorted(value.items())) for key, value in sorted(summary.items())},
    }


# Ledger kinds a future incentive study may derive from.  Declared here so the
# vocabulary is fixed before any numbers exist.
LEDGER_KINDS = (
    "order_acknowledged",
    "deviation_reported",
    "coordination_observed",
    "risk_constraint_violated",
    "rendezvous_kept",
    "report_omitted",
)
