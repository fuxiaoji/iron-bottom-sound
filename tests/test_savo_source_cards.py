"""S10 PDF17 card cells/arrows and actual reinforcement registration boundaries."""
import hashlib

from iron_bottom_sound import night, savo
from iron_bottom_sound.data import ROOT, read_yaml, STRUCTURED
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import GameOptions, Side, Phase, OrderBatch, ReinforcementOrder, HexCoord, FiringArc
from iron_bottom_sound.ship_records import load_ship_records


def test_savo_card_source_hash_cells_arrows_and_zero_surface_guns():
    source = read_yaml(STRUCTURED / 'ships/extensions/savo-cards.yaml')['source']
    assert source['pdf_pages'] == [17]
    assert hashlib.sha256((ROOT / 'resources/originals/records/ship-record-manual-1.1-zh.pdf').read_bytes()).hexdigest() == source['sha256']
    records = load_ship_records()
    juan, hobart = records['IBS-U-USN-SAN-JUAN'], records['IBS-U-RAN-HOBART']
    assert juan.source_page == hobart.source_page == 17
    assert juan.hull_rows == hobart.hull_rows == (4, 3, 3)
    assert juan.maximum_speed_cycle == (6, 5, 5) and hobart.maximum_speed_cycle == (5, 5, 5)
    assert [g.firepower for g in juan.guns] == [3, 3, 3, 2, 3]
    assert all(g.kind == 'secondary' and g.caliber == 5 for g in juan.guns)
    assert juan.guns[0].arcs == (FiringArc.BOW, FiringArc.PORT)
    assert juan.guns[3].arcs == (FiringArc.STARBOARD,)
    assert FiringArc.STARBOARD not in juan.guns[0].arcs
    assert [g.firepower for g in hobart.guns if g.kind == 'primary'] == [1, 1, 1, 1]
    assert [g.firepower for g in hobart.guns if g.kind == 'secondary'] == [4, 3, 3, 4]
    assert [t.torpedoes for t in juan.torpedo_launchers] == [1, 1]
    assert [t.torpedoes for t in hobart.torpedo_launchers] == [2, 2]
    assert all(t.reloads == 0 and set(t.arcs) == {FiringArc.PORT, FiringArc.STARBOARD}
               for r in (juan, hobart) for t in r.torpedo_launchers)
    assert juan.armour.model_dump() == dict(primary=1, secondary=1, belt=3, bridge=2)
    assert hobart.armour.model_dump() == dict(primary=1, secondary=None, belt=3, bridge=None)
    assert juan.vp == 8 and hobart.vp == 10 and juan.radar and hobart.radar
    # Dedicated S10 card must not silently replace a generic/old-save identity.
    assert records['IBS-U-USN-UNNAMED-T01-R25'].guns != juan.guns


def test_registered_eastern_cards_enter_with_source_stats_and_hull_ii(monkeypatch):
    engine = IronBottomEngine()
    state = engine.reset('IBS-S-10', options=GameOptions(ruleset_version='night-v2'))
    blockers = {b['id'] for b in state.scenario_state['rule_blockers']}
    assert 'IBS-Q-026' not in blockers and {'IBS-Q-024', 'IBS-Q-025'} <= blockers
    assert 'IBS-U-USN-HULL-II' in night.config(state)['savo']['reinforcement_groups']['tulagi']['ships']
    assert 'IBS-U-USN-HULL-I' not in state.ships
    assert state.ships['IBS-U-USN-SAN-JUAN'].primary.firepower == 0
    assert state.ships['IBS-U-RAN-HOBART'].primary.firepower == 4
    # Explicit synthetic timing fixture: source blockers remain recorded.
    state.turn, state.phase = 2, Phase.REINFORCEMENT
    state.land_hexes.clear()  # Isolate R20/R21 from the still-blocked overlay.
    monkeypatch.setattr(engine, '_roll_2d6', lambda _: (3, [1, 2]))
    savo.prepare(engine, state)
    rows = savo.candidates(engine, state, Side.ALLIES)
    eastern = [row for row in rows if row['group'] == 'eastern']
    assert len(eastern) == 4 and all(row['asset'] for row in eastern)
    orders = [ReinforcementOrder(ship_id=row['ship_id'], entry_hex=HexCoord.from_label(f'HH{index+3}'), heading=6, speed=0)
              for index, row in enumerate(eastern)]
    for row in rows:
        if row['group'] != 'eastern':
            orders.append(ReinforcementOrder(ship_id=row['ship_id'], entry_hex=HexCoord.from_label(row['entry_hexes'][0]), heading=6, speed=0))
    batch = OrderBatch(side=Side.ALLIES, phase=state.phase, reinforcements=orders)
    assert not savo.validate(engine, state, batch)
    state.sealed_orders[f'{state.turn}:{state.phase.value}'] = {'allies': batch}
    savo.resolve(engine, state)
    assert all(state.ships[row['ship_id']].position for row in eastern)
    assert 'eastern' in state.scenario_state['savo_arrived_groups']
    assert any(e.type == 'scenario_ship_entered' and e.payload['ship_id'] == 'IBS-U-RAN-HOBART' for e in state.events)
