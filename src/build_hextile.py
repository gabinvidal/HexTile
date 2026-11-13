# Builds the HexTile gizmo (a BlinkScript inside a Group) from HexTile.blink and
# exports it as HexTile.gizmo, next to this folder. Needs NukeX (it compiles the kernel).
#   Script Editor : exec(open(r'<repo>/src/build_hextile.py').read())
#   Terminal      : Nuke -t --nukex <repo>/src/build_hextile.py
import os
import nuke

VERSION = '1.0'
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:  # exec() from the Script Editor: set HEXTILE_SRC or edit this line
    HERE = os.environ.get('HEXTILE_SRC', os.path.join(os.path.expanduser('~'), '.nuke', 'plugins', 'HexTile', 'dev'))
KERNEL_PATH = os.path.join(HERE, 'HexTile.blink')
GIZMO_PATH = os.environ.get('HEXTILE_GIZMO', os.path.join(os.path.dirname(HERE), 'HexTile.gizmo'))

INFO = (
    "<b>HexTile</b> &nbsp; hexagonal tiling<br><br>"
    "Like the native <b>Tile</b> node, on a grid of hexagons.<br><br>"
    "&bull; <b>orientation</b> : pointy top (offset rows) or flat top (offset columns).<br>"
    "&bull; <b>fit</b> : <i>Fill</i> keeps the image aspect and crops it, <i>Stretch</i> squeezes it into the hexagon.<br>"
    "&bull; <b>columns / rows</b> : number of cells. With <i>regular hexagons</i> on, rows follows columns "
    "so the hexagons stay regular.<br>"
    "&bull; <b>mirror</b> : flips every other column / row.<br>"
    "&bull; <b>seam falloff</b> : 0 = sharp (antialiased) seams, 1 = blend across the whole cell.<br>"
    "&bull; <b>gap</b> : empty space between the hexagons (alpha 0).<br>"
    "&bull; <b>content scale / grid offset</b> : zoom of the image inside each cell, offset of the grid in pixels.<br><br>"
    "BlinkScript : runs on the GPU when available."
)
ABOUT = (
    "<b>HexTile</b> &nbsp; v%s<br>Hexagonal tiling with soft seams.<br><br>"
    "Created by <b>Gabin Vidal</b> &#8212; 2026<br>"
    "<a href='https://www.linkedin.com/in/gabinvidal' style='color:#6c9fff;'>linkedin.com/in/gabinvidal</a>"
) % VERSION

KNOB_CHANGED = (
    "n = nuke.thisNode()\n"
    "k = nuke.thisKnob()\n"
    "if k.name() in ('regular', 'showPanel'):\n"
    "    n['rows'].setEnabled(not n['regular'].value())\n"
)


def _param(blink, name):
    """BlinkScript param knob: '<Kernel>_<param>' depending on the Nuke version."""
    for k in blink.knobs():
        if k == name or k.endswith('_' + name):
            return blink[k]
    raise RuntimeError('Blink param not found: %s (knobs: %s)' % (name, sorted(blink.knobs())))


def build():
    for n in nuke.selectedNodes():
        n.setSelected(False)
    g = nuke.nodes.Group(name='HexTile')
    g['tile_color'].setValue(0xc9a24bff)
    g['help'].setValue("HexTile - hexagonal tiling (like the native Tile node) with soft seams.")
    g.begin()
    src = nuke.nodes.Input(name='src', xpos=0, ypos=-200)
    mask = nuke.nodes.Input(name='mask', xpos=200, ypos=40)
    mask['number'].setValue(1)

    crop = nuke.nodes.Crop(name='toFormat', xpos=0, ypos=-130)
    crop.setInput(0, src)
    crop['box'].setExpression('0', 0)
    crop['box'].setExpression('0', 1)
    crop['box'].setExpression('input.width', 2)
    crop['box'].setExpression('input.height', 3)
    crop['intersect'].setValue(False)
    crop['crop'].setValue(True)

    blink = nuke.nodes.BlinkScript(name='HexTileBlink', xpos=0, ypos=-60)
    blink.setInput(0, crop)
    # kernelSource.setValue + recompile does not rebuild the params in -t mode:
    # load from file, then detach the file so the source stays embedded.
    blink['kernelSourceFile'].setValue(KERNEL_PATH.replace('\\', '/'))
    blink['reloadKernelSourceFile'].execute()
    blink['kernelSourceFile'].setValue('')

    merge = nuke.nodes.MergeExpression(name='Match', xpos=0, ypos=40)
    merge.setInput(0, src)      # B = original
    merge.setInput(1, blink)    # A = tiled
    merge.setInput(2, mask)
    for i, c in enumerate('rgba'):
        merge['expr%d' % i].setValue('A' + c)
    out = nuke.nodes.Output(name='Output1', xpos=0, ypos=110)
    out.setInput(0, merge)
    g.end()

    # ---- user knobs -------------------------------------------------------
    k = nuke.Tab_Knob('hextile_tab', 'Hex Tile'); g.addKnob(k)
    k = nuke.Enumeration_Knob('orientation', 'orientation', ['Pointy Top', 'Flat Top'])
    k.setTooltip("Pointy Top: offset rows. Flat Top: offset columns."); g.addKnob(k)
    k = nuke.Enumeration_Knob('fit', 'fit', ['Stretch', 'Fill'])
    k.setValue('Fill'); k.clearFlag(nuke.STARTLINE)
    k.setTooltip("Fill: keeps the aspect of the image and crops it to the hexagon. Stretch: squeezes the image into the bounding box of the hexagon.")
    g.addKnob(k)
    g.addKnob(nuke.Text_Knob('div1', ''))
    k = nuke.Double_Knob('columns', 'columns'); k.setRange(1, 20); k.setValue(4); g.addKnob(k)
    k = nuke.Boolean_Knob('mirror_cols', 'mirror'); k.clearFlag(nuke.STARTLINE)
    k.setTooltip('Flips every other column horizontally.'); g.addKnob(k)
    k = nuke.Double_Knob('rows', 'rows'); k.setRange(1, 20); k.setValue(4); k.setEnabled(False); g.addKnob(k)
    k = nuke.Boolean_Knob('mirror_rows', 'mirror'); k.clearFlag(nuke.STARTLINE)
    k.setTooltip('Flips every other row vertically.'); g.addKnob(k)
    k = nuke.Boolean_Knob('regular', 'regular hexagons'); k.setValue(True); k.setFlag(nuke.STARTLINE)
    k.setTooltip("Rows follows columns so the hexagons stay regular. Uncheck to set rows by hand (stretched hexagons)."); g.addKnob(k)
    g.addKnob(nuke.Text_Knob('div2', ''))
    k = nuke.Double_Knob('falloff', 'seam falloff'); k.setRange(0, 1); k.setValue(0)
    k.setTooltip("Transition between cells. 0 = sharp (antialiased) seams, 1 = blend across the whole cell."); g.addKnob(k)
    k = nuke.Double_Knob('gap', 'gap'); k.setRange(0, 1); k.setValue(0)
    k.setTooltip("Empty space (black, alpha 0) between the hexagons."); g.addKnob(k)
    g.addKnob(nuke.Text_Knob('div3', ''))
    k = nuke.Double_Knob('content_scale', 'content scale'); k.setRange(0.1, 4); k.setValue(1)
    k.setTooltip("Zoom of the image inside each cell. Below 1 the image repeats (wrap)."); g.addKnob(k)
    k = nuke.XY_Knob('grid_offset', 'grid offset'); k.setTooltip('Offset of the grid, in pixels.'); g.addKnob(k)
    g.addKnob(nuke.Text_Knob('mask_div', ''))
    for name, label, flag in (('maskChannelMask', 'mask', True), ('invert_mask', 'invert', False),
                              ('fringe', 'fringe', False), ('mix', 'mix', True)):
        k = nuke.Link_Knob(name, label)
        k.makeLink(merge.name(), name)
        if not flag:
            k.clearFlag(nuke.STARTLINE)
        g.addKnob(k)
    g.addKnob(nuke.Tab_Knob('info_tab', 'Info'))
    k = nuke.Text_Knob('info', '', INFO); g.addKnob(k)
    g.addKnob(nuke.Tab_Knob('about_tab', 'About'))
    k = nuke.Text_Knob('about_info', '', ABOUT); g.addKnob(k)
    g['knobChanged'].setValue(KNOB_CHANGED)

    # ---- links Blink params -> group knobs ---------------------------------
    _param(blink, 'fmt').setExpression('input.width', 0)
    _param(blink, 'fmt').setExpression('input.height', 1)
    _param(blink, 'columns').setExpression('parent.columns')
    _param(blink, 'rows').setExpression('parent.rows')
    _param(blink, 'regular').setExpression('parent.regular')
    _param(blink, 'orientation').setExpression('parent.orientation')
    _param(blink, 'fit').setExpression('parent.fit')
    _param(blink, 'mirrorCols').setExpression('parent.mirror_cols')
    _param(blink, 'mirrorRows').setExpression('parent.mirror_rows')
    _param(blink, 'falloff').setExpression('parent.falloff')
    _param(blink, 'gap').setExpression('parent.gap')
    _param(blink, 'scale').setExpression('parent.content_scale')
    _param(blink, 'offset').setExpression('parent.grid_offset.x', 0)
    _param(blink, 'offset').setExpression('parent.grid_offset.y', 1)
    return g


def export(g, path=GIZMO_PATH):
    for n in nuke.allNodes():
        n.setSelected(False)
    g.setSelected(True)
    tmp = path + '.tmp'
    nuke.nodeCopy(tmp)
    txt = open(tmp).read()
    os.remove(tmp)
    # no 'version' header (like AutoGrade): older Nuke versions load it without a warning
    lines = [l for l in txt.splitlines() if not l.startswith(('set cut_paste_input', 'push $cut_paste_input', 'version '))]
    txt = '\n'.join(lines) + '\n'
    txt = txt.replace('Group {', 'Gizmo {', 1)
    txt = txt.replace('\n selected true', '', 1)
    import re
    txt = re.sub(r'\n (xpos|ypos) -?\d+', '', txt, count=2)
    with open(path, 'w') as f:
        f.write(txt)
    print('[HexTile] gizmo written:', path)


if __name__ in ('__main__', '__job__', 'builtins'):
    export(build())
