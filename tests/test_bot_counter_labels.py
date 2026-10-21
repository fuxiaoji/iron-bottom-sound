"""The chat map names units without revealing unidentified contacts."""
from types import SimpleNamespace
from PIL import Image, ImageDraw
import pytest

from iron_bottom_sound import battle_report as br
from iron_bottom_sound.models import HexCoord, PublicShip, Side


@pytest.mark.parametrize('identified,expected,forbidden', [
    (True, ['克什', '米尔'], ['e1']),
    (False, ['敌舰'], ['克什', '米尔', 'e1']),
])
def test_named_counter_uses_only_identified_label(monkeypatch, identified, expected, forbidden):
    ship = PublicShip(id='test', name='克什米尔', side=Side.ALLIES, identified=identified,
                      ship_type='DD', position=HexCoord.from_label('C3'), heading=1,
                      current_speed=2, hull=None, max_hull=None, vp=0,
                      fire_markers=0, fired=False, sunk=False, asset=None)
    draw = ImageDraw.Draw(Image.new('RGB', (300, 300)))
    shown = []
    original = draw.text
    def text(xy, value, *args, **kwargs):
        shown.append(value)
        return original(xy, value, *args, **kwargs)
    monkeypatch.setattr(draw, 'text', text)
    br._draw_ships(draw, SimpleNamespace(ships=[ship]), {'test': 'e1'}, ship_names=True)
    assert all(value in shown for value in expected)
    assert all(value not in shown for value in forbidden)


def test_cjk_legend_wrap_keeps_text_and_pixel_bound():
    draw = ImageDraw.Draw(Image.new('RGB', (500, 500)))
    font = br._cjk_font(14)
    text = '舰名克什米尔 JAVELIN 航向1=东北 2=东南 ' * 12
    lines = br._wrap_text(draw, text, font, 200)
    assert ''.join(lines) == text
    assert all(draw.textlength(line, font=font) <= 200 for line in lines)
