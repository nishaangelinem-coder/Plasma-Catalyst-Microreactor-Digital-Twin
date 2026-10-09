# KLayout batch script: render GDS to PNG (run: klayout -zz -r render_klayout.py)
import pya, os
here = os.path.dirname(os.path.abspath(__file__))
lv = pya.LayoutView()
lv.load_layout(os.path.join(here, 'circulator_driver_top.gds'), True)
lv.max_hier()
colors = {1: 0x80A0FF, 2: 0x00C000, 3: 0xFF0000, 4: 0xA0A000, 5: 0xA000A0, 6: 0x303030, 7: 0x0000FF, 8: 0x404040,
          9: 0xFF00FF, 10: 0x404040, 11: 0x00FFFF, 12: 0x404040, 13: 0xFFA000, 15: 0xFF8080, 21: 0x80FF80, 30: 0xFFFF00,
          22: 0x404040, 23: 0xC0C0C0, 40: 0xA0A0A0, 63: 0xFFFFFF, 64: 0xFFFFFF}
it = lv.begin_layers()
while not it.at_end():
    lp = it.current()
    c = colors.get(lp.source_layer, 0x808080)
    lp.fill_color = c; lp.frame_color = c
    lp.dither_pattern = 1 if lp.source_layer in (40, 64, 63) else 5
    lp.visible = True
    it.next()
lv.set_config('background-color', '#000000')
lv.zoom_fit()
lv.save_image(os.path.join(here, '..', 'figures', 'fig_layout_top.png'), 2400, 2400)
# zoom on one channel
lv.zoom_box(pya.DBox(110, 380, 330, 500))
lv.save_image(os.path.join(here, '..', 'figures', 'fig_layout_channel.png'), 2400, 960)
lv.zoom_box(pya.DBox(118, 425, 165, 448))
lv.save_image(os.path.join(here, '..', 'figures', 'fig_layout_driver_zoom.png'), 2400, 1070)
print('rendered')
