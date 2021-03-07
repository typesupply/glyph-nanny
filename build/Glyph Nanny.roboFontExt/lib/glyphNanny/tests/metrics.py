import defcon
from . import registry
from .wrappers import *

# Ligatures

def testLigatureMetrics(glyph):
    """
    Sometimes ligatures should have the same
    metrics as the glyphs they represent.

    Data structure:

        {
            leftMessage : string
            rightMessage : string
            left : number
            right : number
            width : number
            bounds : (xMin, yMin, xMax, yMax)
        }
    """
    font = wrapFont(glyph.font)
    layer = font.getLayer(glyph.layer.name)
    glyph = layer[glyph.name]
    name = glyph.name
    if "_" not in name:
        return
    base = name
    suffix = None
    if "." in name:
        base, suffix = name.split(".", 1)
    # guess at the ligature parts
    parts = base.split("_")
    leftPart = parts[0]
    rightPart = parts[-1]
    # try snapping on the suffixes
    if suffix:
        if leftPart + "." + suffix in font:
            leftPart += "." + suffix
        if rightPart + "." + suffix in font:
            rightPart += "." + suffix
    # test
    left = glyph.leftMargin
    right = glyph.rightMargin
    report = dict(leftMessage=None, rightMessage=None, left=left, right=right, width=glyph.width, bounds=glyph.bounds)
    if leftPart not in font:
        report["leftMessage"] = "Couldn't find the ligature's left component."
    else:
        expectedLeft = font[leftPart].leftMargin
        if left != expectedLeft:
            report["leftMessage"] = "Left doesn't match the presumed part %s left" % leftPart
    if rightPart not in font:
        report["rightMessage"] = "Couldn't find the ligature's right component."
    else:
        expectedRight = font[rightPart].rightMargin
        if right != expectedRight:
            report["rightMessage"] = "Right doesn't match the presumed part %s right" % rightPart
    if report["leftMessage"] or report["rightMessage"]:
        return report
    return None

registry.registerTest(
    identifier="ligatureMetrics",
    level="metrics",
    title="Ligature Side-Bearings",
    description="The side-bearings don't match the ligature's presumed part metrics.",
    testFunction=testLigatureMetrics,
    defconClass=defcon.Glyph,
    destructiveNotifications=["Glyph.WidthChanged", "Glyph.ContoursChanged", "Glyph.ComponentsChanged"]
)

# Components

def testComponentMetrics(glyph):
    """
    If components are present, check their base margins.

    Data structure:

        {
            leftMessage : string
            rightMessage : string
            left : number
            right : number
            width : number
            bounds : (xMin, yMin, xMax, yMax)
        }
    """
    font = wrapFont(glyph.font)
    layer = font.getLayer(glyph.layer.name)
    glyph = layer[glyph.name]
    components = [c for c in glyph.components if c.baseGlyph in font]
    # no components
    if len(components) == 0:
        return
    boxes = [c.bounds for c in components]
    # a component has no contours
    if None in boxes:
        return
    report = dict(leftMessage=None, rightMessage=None, left=None, right=None, width=glyph.width, box=glyph.bounds)
    problem = False
    if len(components) > 1:
        # filter marks
        nonMarks = []
        markCategories = ("Sk", "Zs", "Lm")
        for component in components:
            baseGlyphName = component.baseGlyph
            category = font.naked().unicodeData.categoryForGlyphName(baseGlyphName, allowPseudoUnicode=True)
            if category not in markCategories:
                nonMarks.append(component)
        if nonMarks:
            components = nonMarks
    # order the components from left to right based on their boxes
    if len(components) > 1:
        leftComponent, rightComponent = _getXMinMaxComponents(components)
    else:
        leftComponent = rightComponent = components[0]
    expectedLeft = _getComponentBaseMargins(font, leftComponent)[0]
    expectedRight = _getComponentBaseMargins(font, rightComponent)[1]
    left = leftComponent.bounds[0]
    right = glyph.width - rightComponent.bounds[2]
    if left != expectedLeft:
        problem = True
        report["leftMessage"] = "%s component left does not match %s left" % (leftComponent.baseGlyph, leftComponent.baseGlyph)
        report["left"] = left
    if right != expectedRight:
        problem = True
        report["rightMessage"] = "%s component right does not match %s right" % (rightComponent.baseGlyph, rightComponent.baseGlyph)
        report["right"] = right
    if problem:
        return report

def _getComponentBaseMargins(font, component):
    baseGlyphName = component.baseGlyph
    baseGlyph = font[baseGlyphName]
    scale = component.scale[0]
    left = baseGlyph.leftMargin * scale
    right = baseGlyph.rightMargin * scale
    return left, right

def _getXMinMaxComponents(components):
    minSide = []
    maxSide = []
    for component in components:
        xMin, yMin, xMax, yMax = component.bounds
        minSide.append((xMin, component))
        maxSide.append((xMax, component))
    o = [
        min(minSide, key=lambda v: (v[0], v[1].baseGlyph))[-1],
        max(maxSide, key=lambda v: (v[0], v[1].baseGlyph))[-1],
    ]
    return o

registry.registerTest(
    identifier="componentMetrics",
    level="metrics",
    title="Component Side-Bearings",
    description="The side-bearings don't match the component's metrics.",
    testFunction=testComponentMetrics,
    defconClass=defcon.Glyph,
    destructiveNotifications=["Glyph.WidthChanged", "Glyph.ContoursChanged", "Glyph.ComponentsChanged"]
)

# Symmetry

def testMetricsSymmetry(glyph):
    """
    Sometimes glyphs are almost symmetrical, but could be.

    Data structure:

        {
            message : string
            left : number
            right : number
            width : number
            bounds : (xMin, yMin, xMax, yMax)
        }
    """
    glyph = wrapGlyph(glyph)
    if glyph.leftMargin == None:
        return
    left = glyph.leftMargin
    right = glyph.rightMargin
    if left is None or right is None:
        return None
    diff = int(round(abs(left - right)))
    if diff == 1:
        message = "The side-bearings are 1 unit from being equal."
    else:
        message = "The side-bearings are %d units from being equal." % diff
    data = dict(left=left, right=right, width=glyph.width, message=message)
    if 0 < diff <= 5:
        return data
    return None

registry.registerTest(
    identifier="metricsSymmetry",
    level="metrics",
    title="Symmetry",
    description="The side-bearings are almost equal.",
    testFunction=testMetricsSymmetry,
    defconClass=defcon.Glyph,
    destructiveNotifications=["Glyph.WidthChanged", "Glyph.ContoursChanged", "Glyph.ComponentsChanged"]
)
