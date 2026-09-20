"""Unit tests for the repaired U1 (PI-mandated four cases)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from value_panel import u1_material


class FakeShip:
    def __init__(self, sid, side, vp, hull, max_hull, sunk=False):
        self.id, self.side, self.vp = sid, side, vp
        self.hull, self.max_hull, self.sunk = hull, max_hull, sunk


class FakeState:
    def __init__(self, ships):
        self.ships = {s.id: s for s in ships}


def _roster(state):
    return {s.id: s.vp for s in state.ships.values()}


def test_no_damage_u1_zero():
    st = FakeState([
        FakeShip("a1", "axis", 10, 100, 100),
        FakeShip("e1", "allies", 10, 100, 100),
    ])
    assert u1_material(st, "axis", _roster(st)) == pytest.approx(0.0, abs=1e-12)


def test_enemy_sunk_u1_positive():
    st = FakeState([
        FakeShip("a1", "axis", 10, 100, 100),
        FakeShip("e1", "allies", 10, 100, 100, sunk=True),
    ])
    # enemy takes full 10 VP damage of 20 total -> +0.5
    assert u1_material(st, "axis", _roster(st)) == pytest.approx(0.5, abs=1e-12)
    assert u1_material(st, "axis", _roster(st)) > 0


def test_own_sunk_u1_negative():
    st = FakeState([
        FakeShip("a1", "axis", 10, 100, 100, sunk=True),
        FakeShip("e1", "allies", 10, 100, 100),
    ])
    assert u1_material(st, "axis", _roster(st)) == pytest.approx(-0.5, abs=1e-12)
    assert u1_material(st, "axis", _roster(st)) < 0


def test_symmetric_damage_u1_zero():
    st = FakeState([
        FakeShip("a1", "axis", 10, 50, 100),
        FakeShip("e1", "allies", 10, 50, 100),
    ])
    assert u1_material(st, "axis", _roster(st)) == pytest.approx(0.0, abs=1e-12)
