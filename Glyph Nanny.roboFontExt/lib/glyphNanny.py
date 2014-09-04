import os
import re
import math
from fontTools.misc.bezierTools import splitCubicAtT
from fontTools.agl import AGL2UV
from fontTools.pens.cocoaPen import CocoaPen
from robofab.pens.digestPen import DigestPointPen
from AppKit import *
import vanilla
from vanilla import dialogs
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.roboFont import CurrentFont, AllFonts
from mojo.roboFont import version as roboFontVersion
from mojo.UI import UpdateCurrentGlyphView
from mojo.events import addObserver, removeObserver
from mojo.extensions import getExtensionDefault, setExtensionDefault, getExtensionDefaultColor, setExtensionDefaultColor
from lib.tools import bezierTools

DEBUG = False

# --------
# Defaults
# --------

defaultKeyStub = "com.typesupply.GlyphNanny."
defaultKeyObserverVisibility = defaultKeyStub + "displayReportInGlyphView"
defaultKeyTestStates = defaultKeyStub + "testStates"
defaultKeyColorInform = defaultKeyStub + "colorInform"
defaultKeyColorReview = defaultKeyStub + "colorReview"
defaultKeyColorRemove = defaultKeyStub + "colorRemove"
defaultKeyColorInsert = defaultKeyStub + "colorInsert"

def registerGlyphNannyDefaults():
    defaults = {
        defaultKeyObserverVisibility : False,
        defaultKeyTestStates : {}
    }
    for key in sorted(testRegistry.keys()):
        defaults[defaultKeyTestStates][key] = True

    try:
        from mojo.extensions import registerExtensionsDefaults
    except ImportError:
        def registerExtensionsDefaults(d):
            for k, v in d.items():
                e = getExtensionDefault(k, fallback="__fallback__")
                if e == "__fallback__":
                    setExtensionDefault(k, v)

    registerExtensionsDefaults(defaults)

    # handle nested
    nested = getExtensionDefault(defaultKeyTestStates)
    for key, default in defaults[defaultKeyTestStates].items():
        if key not in nested:
            nested[key] = default
            setExtensionDefault(defaultKeyTestStates, nested)

# ----------------
# Drawing Observer
# ----------------

def registerGlyphNannyObserver(observer):
    addObserver(observer, "drawReport", "drawBackground")
    addObserver(observer, "drawReport", "drawInactive")

def unregisterGlyphNannyObserver(observer):
    removeObserver(observer, "drawBackground")
    removeObserver(observer, "drawInactive")


class GlyphNannyObserver(object):

    def drawReport(self, info):
        # skip if the user doesn't want to see the report
        display = getExtensionDefault(defaultKeyObserverVisibility)
        if not display:
            return
        # make sure there is something to be tested
        glyph = info["glyph"]
        if glyph is None:
            return
        # get the report
        font = glyph.getParent()
        testStates = getExtensionDefault(defaultKeyTestStates)
        if roboFontVersion > "1.5.1":
            testStates = dictToTuple(testStates)
            report = glyph.getRepresentation("com.typesupply.GlyphNanny.Report", testStates=testStates)
        else:
            report = getGlyphReport(font, glyph, testStates)
        # draw the report
        scale = info["scale"]
        for key in drawingOrder:
            data = report.get(key)
            if data:
                drawingFunction = testRegistry[key]["drawingFunction"]
                if drawingFunction is not None:
                    drawingFunction(data, scale, glyph)
        drawTextReport(report, scale, glyph)


# ------------
# Prefs Window
# ------------

class GlyphNannyPrefsWindow(object):

    def __init__(self):
        self.testStateControlToIdentifier = {}
        self.colorControlToKey = {}

        self.w = vanilla.Window((264, 425), "Glyph Nanny Preferences")

        # global visibility
        state = getExtensionDefault(defaultKeyObserverVisibility)
        self.w.displayLiveReportTitle = vanilla.TextBox((15, 15, 150, 17), "Live report display is:")
        self.w.displayLiveReportRadioGroup = vanilla.RadioGroup((159, 15, -15, 17), ["On", "Off"], isVertical=False, callback=self.displayLiveReportRadioGroupCallback)
        self.w.displayLiveReportRadioGroup.set(not state)

        # test states
        _buildGlyphTestTabs(self, 50)

        # colors
        colors = [
            ("Information", colorInform(), defaultKeyColorInform),
            ("Review Something", colorReview(), defaultKeyColorReview),
            ("Insert Something", colorInsert(), defaultKeyColorInsert),
            ("Remove Something", colorRemove(), defaultKeyColorRemove)
        ]
        top = 290
        for title, color, key in colors:
            control = vanilla.ColorWell((15, top, 70, 25), color=color, callback=self.noteColorColorWellCallback)
            self.colorControlToKey[control] = key
            setattr(self.w, "colorWell_" + title, control)
            control = vanilla.TextBox((90, top + 3, -15, 17), title)
            setattr(self.w, "colorTitle_" + title, control)
            top += 32

        self.w.open()

    def displayLiveReportRadioGroupCallback(self, sender):
        state = not sender.get()
        setExtensionDefault(defaultKeyObserverVisibility, state)
        UpdateCurrentGlyphView()

    def testStateTabSelectorCallback(self, sender):
        tab = sender.get()
        self.w.testStateBox.testStateTabs.set(tab)

    def testStateCheckBoxCallback(self, sender):
        identifier = self.testStateControlToIdentifier[sender]
        state = sender.get()
        defaults = getExtensionDefault(defaultKeyTestStates)
        defaults[identifier] = state
        setExtensionDefault(defaultKeyTestStates, defaults)
        UpdateCurrentGlyphView()

    def noteColorColorWellCallback(self, sender):
        color = sender.get()
        key = self.colorControlToKey[sender]
        setExtensionDefaultColor(key, color)
        UpdateCurrentGlyphView()


def _buildGlyphTestTabs(controller, viewTop):
    groupTitles = ["Glyph Tests", "Metrics Tests", "Contour Tests", "Segment Tests", "Point Tests"]
    controller.w.testStateBox = vanilla.Box((15, viewTop + 10, -15, 210))
    tabs = controller.w.testStateBox.testStateTabs = vanilla.Tabs((0, 5, 0, 0), groupTitles, showTabs=False)
    groups = [
        ("glyph", tabs[0]),
        ("metrics", tabs[1]),
        ("contour", tabs[2]),
        ("segment", tabs[3]),
        ("point", tabs[4]),
    ]
    for group, tab in groups:
        top = 15
        for identifier in reportOrder:
           for testIdentifier, testData in testRegistry.items():
               if testIdentifier != identifier:
                   continue
               if testData["level"] != group:
                   continue
               state = getExtensionDefault(defaultKeyTestStates)[identifier]
               control = vanilla.CheckBox((15, top, -15, 22), testData["title"], value=state, callback=controller.testStateCheckBoxCallback)
               top += 25
               controller.testStateControlToIdentifier[control] = identifier
               setattr(tab, "testStateCheckBox_" + identifier, control)
    controller.w.testStateTabSelector = vanilla.PopUpButton((72, viewTop, 120, 20), groupTitles, callback=controller.testStateTabSelectorCallback)


# --------------
# Prefs Shortcut
# --------------

def toggleObserverVisibility():
    state = not getExtensionDefault(defaultKeyObserverVisibility)
    setExtensionDefault(defaultKeyObserverVisibility, state)
    UpdateCurrentGlyphView()


# ----------------
# Test Font Window
# ----------------

class GlyphNannyTestFontsWindow(BaseWindowController):

    def __init__(self):
        self.testStateControlToIdentifier = {}
        self.w = vanilla.Window((264, 315), "Glyph Nanny")
        # test states
        _buildGlyphTestTabs(self, 15)
        # test buttons
        self.w.testCurrentButton = vanilla.Button((15, 250, -15, 20), "Test Current Font", callback=self.testCurrentButtonCallback)
        self.w.testAllButton = vanilla.Button((15, 280, -15, 20), "Test All Open Fonts", callback=self.testAllButtonCallback)

        self.w.open()

    def testStateTabSelectorCallback(self, sender):
        tab = sender.get()
        self.w.testStateBox.testStateTabs.set(tab)

    def testStateCheckBoxCallback(self, sender):
        pass

    def getTestStates(self):
        testStates = {}
        for control, identifier in self.testStateControlToIdentifier.items():
            testStates[identifier] = control.get()
        return testStates

    def testCurrentButtonCallback(self, sender):
        font = CurrentFont()
        if font is None:
            dialogs.message("There is no font to test.", "Open a font and try again.")
            return
        testStates = self.getTestStates()
        results = getFontReport(font, testStates, format=True)
        print results

    def testAllButtonCallback(self, sender):
        fonts = AllFonts()
        if not fonts:
            dialogs.message("There are no fonts to test.", "Open a font and try again.")
            return
        testStates = self.getTestStates()
        for font in fonts:
            results = getFontReport(font, testStates, format=True)
            print results
            print


# ------
# Colors
# ------

# Informative: Blue
def colorInform():
    color = getExtensionDefaultColor(defaultKeyColorInform)
    if color is None:
        color = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0.7, 0.3)
    return color

# Insert Something: Green
def colorInsert():
    color = getExtensionDefaultColor(defaultKeyColorInsert)
    if color is None:
        color = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 1, 0, 0.75)
    return color

# Remove Something: Red
def colorRemove():
    color = getExtensionDefaultColor(defaultKeyColorInsert)
    if color is None:
        color = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0, 0, 0.5)
    return color

# Review Something: Yellow-Orange
def colorReview():
    color = getExtensionDefaultColor(defaultKeyColorInsert)
    if color is None:
        color = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0.7, 0, 0.7)
    return color


# ------
# Orders
# ------

reportOrder = """
unicodeValue
contourCount
componentMetrics
ligatureMetrics
metricsSymmetry
strayPoints
smallContours
openContours
duplicateContours
extremePoints
unnecessaryPoints
unnecessaryHandles
overlappingPoints
pointsNearVerticalMetrics
complexCurves
crossedHandles
unevenHandles
straightLines
unsmoothSmooths
""".strip().splitlines()

drawingOrder = """
unicodeValue
contourCount
componentMetrics
ligatureMetrics
metricsSymmetry
smallContours
pointsNearVerticalMetrics
complexCurves
crossedHandles
unsmoothSmooths
straightLines
duplicateContours
openContours
extremePoints
strayPoints
unnecessaryPoints
unnecessaryHandles
unevenHandles
overlappingPoints
""".strip().splitlines()


# ---------
# Reporters
# ---------

# Font

def getFontReport(font, testStates, format=False):
    """
    Get a report about all glyphs in the font.

    testStates should be a dict of the test names
    and a boolean indicating if they should be
    executed or not.
    """
    results = {}
    for name in font.glyphOrder:
        glyph = font[name]
        report = getGlyphReport(font, glyph, testStates)
        results[name] = report
    if format:
        path = font.path
        if path is None:
            path = "Unsaved Font"
        else:
            path = os.path.basename(path)
        path = ("-" * len(path)) + "\n" + path + "\n" + ("-" * len(path))
        all = [path]
        for name in font.glyphOrder:
            report = results[name]
            l = []
            for key in reportOrder:
                data = testRegistry[key]
                description = data["description"]
                value = report.get(key)
                if value:
                    l.append(description)
            if l:
                l.insert(0, "-" * len(name))
                l.insert(0, name)
                all.append("\n".join(l))
        results = "\n\n".join(all)
    return results

# Glyph

def getGlyphReport(font, glyph, testStates):
    """
    Get a report about the glyph.

    testStates should be a dict of the test names
    and a boolean indicating if they should be
    executed or not.
    """
    report = {}
    for key, data in testRegistry.items():
        testFunction = data["testFunction"]
        if testStates.get(key, True):
            report[key] = testFunction(glyph)
        else:
            report[key] = None
    return report

# Factory

def dictToTuple(d):
    t = []
    for k, v in sorted(d.items()):
        t.append((k, v))
    return tuple(t)

def tupleToDict(t):
    d = {}
    for k, v in t:
        d[k] = v
    return d

def GlyphNannyReportFactory(glyph, font, testStates=None):
    """
    Representation factory for retrieving a report.
    """
    glyph = RGlyph(glyph)
    font = glyph.getParent()
    d = tupleToDict(testStates)
    return getGlyphReport(font, glyph, d)

def _registerFactory():
    # always register if debugging
    # otherwise only register if it isn't registered
    from defcon import addRepresentationFactory, removeRepresentationFactory
    from defcon.objects import glyph as _xxxHackGlyph
    if DEBUG:
        if "com.typesupply.GlyphNanny.Report" in _xxxHackGlyph._representationFactories:
            for font in AllFonts():
                for glyph in font:
                    glyph.naked().destroyAllRepresentations()
            removeRepresentationFactory("com.typesupply.GlyphNanny.Report")
        addRepresentationFactory("com.typesupply.GlyphNanny.Report", GlyphNannyReportFactory)
    else:
        if "com.typesupply.GlyphNanny.Report" not in _xxxHackGlyph._representationFactories:
            addRepresentationFactory("com.typesupply.GlyphNanny.Report", GlyphNannyReportFactory)

# -------------
# Test Registry
# -------------

testRegistry = {}

def registerTest(identifier=None, level=None, title=None, description=None, testFunction=None, drawingFunction=None):
    testRegistry[identifier] = dict(
        level=level,
        description=description,
        title=title,
        testFunction=testFunction,
        drawingFunction=drawingFunction
    )


# -----------------
# Glyph Level Tests
# -----------------

def drawTextReport(report, scale, glyph):
    text = []
    r = report.get("unicodeValue")
    if r:
        text += r
    r = report.get("contourCount")
    if r:
        text += r
    if text:
        text = "\n".join(text)
        x = 50
        y = 50
        drawString((x, y), text, 16, scale, colorInform(), alignment="left")

# Unicode Value

uniNamePattern = re.compile(
    "uni"
    "([0-9A-Fa-f]{4})"
    "$"
)

def testUnicodeValue(glyph):
    """
    A Unicode value should appear only once per font.
    """
    report = []
    font = glyph.getParent()
    uni = glyph.unicode
    name = glyph.name
    # test for uniXXXX name
    m = uniNamePattern.match(name)
    if m is not None:
        uniFromName = m.group(1)
        uniFromName = int(uniFromName, 16)
        if uni != uniFromName:
            report.append("The Unicode value for this glyph does not match its name.")
    # test against AGLFN
    else:
        expectedUni = AGL2UV.get(name)
        if expectedUni != uni:
            report.append("The Unicode value for this glyph may not be correct.")
    # look for duplicates
    if uni is not None:
        duplicates = []
        for name in sorted(font.keys()):
            if name == glyph.name:
                continue
            other = font[name]
            if other.unicode == uni:
                duplicates.append(name)
        if duplicates:
            report.append("The Unicode for this glyph is also used by: %s." % " ".join(duplicates))
    return report

registerTest(
    identifier="unicodeValue",
    level="glyph",
    title="Unicode Value",
    description="Unicode value may have problems.",
    testFunction=testUnicodeValue,
    drawingFunction=None
)


# Contour Count

def testContourCount(glyph):
    """
    There shouldn't be too many overlapping contours.
    """
    report = []
    count = len(glyph)
    test = glyph.copy()
    test.removeOverlap()
    if count - len(test) > 2:
        report.append("This glyph has a unusally high number of overlapping contours.")
    return report

registerTest(
    identifier="contourCount",
    level="glyph",
    title="Contour Count",
    description="There are an unusual number of contours.",
    testFunction=testContourCount,
    drawingFunction=None
)


# -------------------
# Metrics Level Tests
# -------------------

# Ligatures

def testLigatureMetrics(glyph):
    """
    Sometimes ligatures should have the same
    metrics as the glyphs they represent.
    """
    font = glyph.getParent()
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
    report = dict(leftMessage=None, rightMessage=None, left=left, right=right, width=glyph.width, box=glyph.box)
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

def drawLigatureMetrics(data, scale, glyph):
    xMin, yMin, xMax, yMax = data["box"]
    h = (yMax - yMin) / 2.0
    y = yMax - h + (20 * scale)
    _drawSideBearingsReport(data, scale, y, colorReview())

def _drawSideBearingsReport(data, scale, textPosition, color):
    left = data["left"]
    right = data["right"]
    width = data["width"]
    leftMessage = data["leftMessage"]
    rightMessage = data["rightMessage"]
    xMin, yMin, xMax, yMax = data["box"]
    h = (yMax - yMin) / 2.0
    y = textPosition
    path = NSBezierPath.bezierPath()
    if leftMessage:
        path.moveToPoint_((0, y))
        path.lineToPoint_((left, y))
        path.moveToPoint_((left, yMin))
        path.lineToPoint_((left, yMax))
        x = min((0, left)) - (5 * scale)
        drawString((x, y), leftMessage, 10, scale, color, alignment="right")
    if rightMessage:
        right = width - right
        path.moveToPoint_((width, y))
        path.lineToPoint_((right, y))
        path.moveToPoint_((right, yMin))
        path.lineToPoint_((right, yMax))
        x = max((width, right)) + (5 * scale)
        drawString((x, y), rightMessage, 10, scale, color, alignment="left")
    color.set()
    path.setLineWidth_(scale)
    path.stroke()

registerTest(
    identifier="ligatureMetrics",
    level="metrics",
    title="Ligature Side-Bearings",
    description="The side-bearings don't match the ligature's presumed part metrics.",
    testFunction=testLigatureMetrics,
    drawingFunction=drawLigatureMetrics
)

# Components

def testComponentMetrics(glyph):
    """
    If components are present, check their base margins.
    """
    font = glyph.getParent()
    components = [c for c in glyph.components if c.baseGlyph in font]
    # no components
    if len(components) == 0:
        return
    report = dict(leftMessage=None, rightMessage=None, left=None, right=None, width=glyph.width, box=glyph.box)
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
    left = leftComponent.box[0]
    right = glyph.width - rightComponent.box[2]
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
        xMin, yMin, xMax, yMax = component.box
        minSide.append((xMin, component))
        maxSide.append((xMax, component))
    o = [
        min(minSide)[-1],
        max(maxSide)[-1],
    ]
    return o

def drawComponentMetrics(data, scale, glyph):
    xMin, yMin, xMax, yMax = data["box"]
    h = (yMax - yMin) / 2.0
    y = yMax - h - (20 * scale)
    _drawSideBearingsReport(data, scale, y, colorReview())

registerTest(
    identifier="componentMetrics",
    level="metrics",
    title="Component Side-Bearings",
    description="The side-bearings don't match the component's metrics.",
    testFunction=testComponentMetrics,
    drawingFunction=drawComponentMetrics
)

# Symmetry

def testMetricsSymmetry(glyph):
    """
    Sometimes glyphs are almost symmetrical, but could be.
    """
    left = glyph.leftMargin
    right = glyph.rightMargin
    diff = int(round(abs(left - right)))
    if diff == 1:
        message = "The side-bearings are 1 unit from being equal."
    else:
        message = "The side-bearings are %d units from being equal." % diff
    data = dict(left=left, right=right, width=glyph.width, message=message)
    if 0 < diff <= 5:
        return data
    return None

def drawMetricsSymmetry(data, scale, glyph):
    color = colorReview()
    left = data["left"]
    right = data["right"]
    width = data["width"]
    message = data["message"]
    y = -20
    x = left + (((width - right) - left) / 2.0)
    path = NSBezierPath.bezierPath()
    path.moveToPoint_((min((0, left)), y))
    path.lineToPoint_((max((width, width - right)), y))
    path.moveToPoint_((0, 0))
    path.lineToPoint_((0, y * 2))
    path.moveToPoint_((left, 0))
    path.lineToPoint_((left, y * 2))
    path.moveToPoint_((width - right, 0))
    path.lineToPoint_((width - right, y * 2))
    path.moveToPoint_((width, 0))
    path.lineToPoint_((width, y * 2))
    path.setLineWidth_(scale)
    color.set()
    path.stroke()
    drawString((x, y), message, 10, scale, color, backgroundColor=NSColor.whiteColor())

registerTest(
    identifier="metricsSymmetry",
    level="metrics",
    title="Symmetry",
    description="The side-bearings are almost equal.",
    testFunction=testMetricsSymmetry,
    drawingFunction=drawMetricsSymmetry
)


# -------------------
# Contour Level Tests
# -------------------

# Duplicate Contours

def testDuplicateContours(glyph):
    """
    Contours shouldn't be duplicated on each other.
    """
    contours = {}
    for index, contour in enumerate(glyph):
        contour = contour.copy()
        contour.autoStartSegment()
        pen = DigestPointPen()
        contour.drawPoints(pen)
        digest = pen.getDigest()
        if digest not in contours:
            contours[digest] = []
        contours[digest].append(index)
    duplicateContours = []
    for digest, indexes in contours.items():
        if len(indexes) > 1:
            duplicateContours.append(indexes[0])
    return duplicateContours

def drawDuplicateContours(contours, scale, glyph):
    font = glyph.getParent()
    color = colorRemove()
    color.set()
    for contourIndex in contours:
        contour = glyph[contourIndex]
        pen = CocoaPen(font)
        contour.draw(pen)
        path = pen.path
        path.setLineWidth_(5 * scale)
        path.stroke()
        xMin, yMin, xMax, yMax = contour.box
        mid = calcMid((xMin, yMin), (xMax, yMin))
        x, y = mid
        drawString((x, y - (10 * scale)), "Duplicate Contour", 10, scale, color)

registerTest(
    identifier="duplicateContours",
    level="contour",
    title="Duplicate Contours",
    description="One or more contours are duplicated.",
    testFunction=testDuplicateContours,
    drawingFunction=drawDuplicateContours
)

# Small Contours

def testForSmallContours(glyph):
    """
    Contours should not have an area less than or equal to 4 units.
    """
    smallContours = {}
    for index, contour in enumerate(glyph):
        box = contour.box
        if not box:
            continue
        xMin, yMin, xMax, yMax = box
        w = xMax - xMin
        h = yMin - yMax
        area = abs(w * h)
        if area <= 4:
            smallContours[index] = contour.box
    return smallContours

def drawSmallContours(contours, scale, glyph):
    color = colorRemove()
    color.set()
    for contourIndex, box in contours.items():
        xMin, yMin, xMax, yMax = box
        w = xMax - xMin
        h = yMax - yMin
        r = ((xMin, yMin), (w, h))
        r = NSInsetRect(r, -5 * scale, -5 * scale)
        NSRectFillUsingOperation(r, NSCompositeSourceOver)
        x = xMin + (w / 2)
        y = yMin - (10 * scale)
        drawString((x, y), "Tiny Contour", 10, scale, color)

registerTest(
    identifier="smallContours",
    level="contour",
    title="Small Contours",
    description="One or more contours are suspiciously small.",
    testFunction=testForSmallContours,
    drawingFunction=drawSmallContours
)

# Open Contours

def testForOpenContours(glyph):
    """
    Contours should be closed.
    """
    openContours = {}
    for index, contour in enumerate(glyph):
        if not contour.open:
            continue
        start = contour[0].onCurve
        start = (start.x, start.y)
        end = contour[-1].onCurve
        end = (end.x, end.y)
        if start != end:
            openContours[index] = (start, end)
    return openContours

def drawOpenContours(contours, scale, glyph):
    color = colorInsert()
    color.set()
    for contourIndex, points in contours.items():
        start, end = points
        mid = calcMid(start, end)
        path = NSBezierPath.bezierPath()
        path.moveToPoint_(start)
        path.lineToPoint_(end)
        path.setLineWidth_(scale)
        path.setLineDash_count_phase_([4], 1, 0.0)
        path.stroke()
        drawString(mid, "Open Contour", 10, scale, color, backgroundColor=NSColor.whiteColor())

registerTest(
    identifier="openContours",
    level="contour",
    title="Open Contours",
    description="One or more contours are not properly closed.",
    testFunction=testForOpenContours,
    drawingFunction=drawOpenContours
)

# Extreme Points

def testForExtremePoints(glyph):
    """
    Points should be at the extrema.
    """
    pointsAtExtrema = {}
    for index, contour in enumerate(glyph):
        dummy = glyph.copy()
        dummy.clear()
        dummy.appendContour(contour)
        dummy.extremePoints()
        testPoints = _getOnCurves(dummy[0])
        points = _getOnCurves(contour)
        if points != testPoints:
            pointsAtExtrema[index] = testPoints - points
    return pointsAtExtrema

def drawExtremePoints(contours, scale, glyph):
    color = colorInsert()
    path = NSBezierPath.bezierPath()
    d = 16 * scale
    h = d / 2.0
    o = 3 * scale
    for contourIndex, points in contours.items():
        for (x, y) in points:
            r = ((x - h, y - h), (d, d))
            path.appendBezierPathWithOvalInRect_(r)
            path.moveToPoint_((x - h + o, y))
            path.lineToPoint_((x + h - o, y))
            path.moveToPoint_((x, y - h + o))
            path.lineToPoint_((x, y + h - o))
            drawString((x, y - (16 * scale)), "Insert Point", 10, scale, color)
    color.set()
    path.setLineWidth_(scale)
    path.stroke()

registerTest(
    identifier="extremePoints",
    level="contour",
    title="Extreme Points",
    description="One or more curves need an extreme point.",
    testFunction=testForExtremePoints,
    drawingFunction=drawExtremePoints
)


# -------------------
# Segment Level Tests
# -------------------

def testForStraightLines(glyph):
    """
    Lines shouldn't be just shy of vertical or horizontal.
    """
    straightLines = {}
    for index, contour in enumerate(glyph):
        prev = _unwrapPoint(contour[-1].onCurve)
        for segment in contour:
            point = _unwrapPoint(segment.onCurve)
            if segment.type == "line":
                x = abs(prev[0] - point[0])
                y = abs(prev[1] - point[1])
                if x > 0 and x <= 5:
                    if index not in straightLines:
                        straightLines[index] = set()
                    straightLines[index].add((prev, point))
                if y > 0 and y <= 5:
                    if index not in straightLines:
                        straightLines[index] = set()
                    straightLines[index].add((prev, point))
            prev = point
    return straightLines

def drawStraightLines(contours, scale, glyph):
    color = colorReview()
    color.set()
    for contourIndex, segments in contours.items():
        for segment in segments:
            xs = []
            ys = []
            for (x, y) in segment:
                xs.append(x)
                ys.append(y)
            xMin = min(xs)
            xMax = max(xs)
            yMin = min(ys)
            yMax = max(ys)
            w = xMax - xMin
            h = yMax - yMin
            r = ((xMin, yMin), (w, h))
            r = NSInsetRect(r, -2 * scale, -2 * scale)
            NSRectFillUsingOperation(r, NSCompositeSourceOver)

registerTest(
    identifier="straightLines",
    level="segment",
    title="Straight Lines",
    description="One or more lines is a few units from being horizontal or vertical.",
    testFunction=testForStraightLines,
    drawingFunction=drawStraightLines
)

# Segments Near Vertical Metrics

def testForSegmentsNearVerticalMetrics(glyph):
    """
    Points shouldn't be just off a vertical metric.
    """
    font = glyph.getParent()
    verticalMetrics = {
        0 : set()
    }
    for attr in "descender xHeight capHeight ascender".split(" "):
        value = getattr(font.info, attr)
        verticalMetrics[value] = set()
    for contour in glyph:
        sequence = None
        # test the last segment to start the sequence
        pt = _unwrapPoint(contour[-1].onCurve)
        near, currentMetric = _testPointNearVerticalMetrics(pt, verticalMetrics)
        if near:
            sequence = set()
        # test them all
        for segment in contour:
            pt = _unwrapPoint(segment.onCurve)
            near, metric = _testPointNearVerticalMetrics(pt, verticalMetrics)
            # hit on the same metric as the previous point
            if near and sequence is not None and metric == currentMetric:
                sequence.add(pt)
            else:
                # existing sequence, note it if needed, clear it
                if sequence:
                    if len(sequence) > 1:
                        verticalMetrics[currentMetric] |= sequence
                sequence = None
                currentMetric = None
                # hit, make a new sequence
                if near:
                    sequence = set()
                    currentMetric = metric
                    sequence.add(pt)
    for verticalMetric, points in verticalMetrics.items():
        if not points:
            del verticalMetrics[verticalMetric]
    return verticalMetrics

def _testPointNearVerticalMetrics(pt, verticalMetrics):
    y = pt[1]
    for v in verticalMetrics:
        d = abs(v - y)
        if d != 0 and d <= 5:
            return True, v
    return False, None

def drawSegmentsNearVericalMetrics(verticalMetrics, scale, glyph):
    color = colorReview()
    path = NSBezierPath.bezierPath()
    for verticalMetric, points in verticalMetrics.items():
        xMin = None
        xMax = None
        for (x, y) in points:
            path.moveToPoint_((x, y))
            path.lineToPoint_((x, verticalMetric))
            if xMin is None:
                xMin = x
            elif xMin > x:
                xMin = x
            if xMax is None:
                xMax = x
            elif xMax < x:
                xMax = x
        path.moveToPoint_((xMin, verticalMetric))
        path.lineToPoint_((xMax, verticalMetric))
    color.set()
    path.setLineWidth_(4 * scale)
    path.stroke()

registerTest(
    identifier="pointsNearVerticalMetrics",
    level="segment",
    title="Near Vertical Metrics",
    description="Two or more points are just off a vertical metric.",
    testFunction=testForSegmentsNearVerticalMetrics,
    drawingFunction=drawSegmentsNearVericalMetrics
)

# Unsmooth Smooths

def testUnsmoothSmooths(glyph):
    """
    Smooth segments should have bcps in the right places.
    """
    unsmoothSmooths = {}
    for index, contour in enumerate(glyph):
        prev = contour[-1]
        for segment in contour:
            if prev.type == "curve" and segment.type == "curve":
                if prev.smooth:
                    angle1 = _calcAngle(prev.offCurve[1], prev.onCurve, r=0)
                    angle2 = _calcAngle(prev.onCurve, segment.offCurve[0], r=0)
                    if angle1 != angle2:
                        if index not in unsmoothSmooths:
                            unsmoothSmooths[index] = []
                        pt1 = _unwrapPoint(prev.offCurve[1])
                        pt2 = _unwrapPoint(prev.onCurve)
                        pt3 = _unwrapPoint(segment.offCurve[0])
                        unsmoothSmooths[index].append((pt1, pt2, pt3))
            prev = segment
    return unsmoothSmooths

def drawUnsmoothSmooths(contours, scale, glyph):
    color = colorReview()
    color.set()
    for contourIndex, points in contours.items():
        path = NSBezierPath.bezierPath()
        for pt1, pt2, pt3 in points:
            path.moveToPoint_(pt1)
            path.lineToPoint_(pt3)
        path.setLineWidth_(2 * scale)
        path.stroke()
        x, y = pt2
        drawString((x, y - (10 * scale)), "Unsmooth Smooth", 10, scale, color, backgroundColor=NSColor.whiteColor())

registerTest(
    identifier="unsmoothSmooths",
    level="segment",
    title="Unsmooth Smooths",
    description="One or more smooth points do not have handles that are properly placed.",
    testFunction=testUnsmoothSmooths,
    drawingFunction=drawUnsmoothSmooths
)

# Complex Curves

def testForComplexCurves(glyph):
    """
    S curves are suspicious.
    """
    impliedS = {}
    for index, contour in enumerate(glyph):
        prev = _unwrapPoint(contour[-1].onCurve)
        for segment in contour:
            if segment.type == "curve":
                pt0 = prev
                pt1, pt2 = [_unwrapPoint(p) for p in segment.offCurve]
                pt3 = _unwrapPoint(segment.onCurve)
                line1 = (pt0, pt3)
                line2 = (pt1, pt2)
                if _intersectLines(line1, line2):
                    if index not in impliedS:
                        impliedS[index] = []
                    impliedS[index].append((prev, pt1, pt2, pt3))
            prev = _unwrapPoint(segment.onCurve)
    return impliedS

def drawComplexCurves(contours, scale, glyph):
    color = colorReview()
    color.set()
    for contourIndex, segments in contours.items():
        for segment in segments:
            pt0, pt1, pt2, pt3 = segment
            path = NSBezierPath.bezierPath()
            path.moveToPoint_(pt0)
            path.curveToPoint_controlPoint1_controlPoint2_(pt3, pt1, pt2)
            path.setLineWidth_(3 * scale)
            path.setLineCapStyle_(NSRoundLineCapStyle)
            path.stroke()
            mid = splitCubicAtT(pt0, pt1, pt2, pt3, 0.5)[0][-1]
            drawString(mid, "Complex Curve", 10, scale, color, backgroundColor=NSColor.whiteColor())

registerTest(
    identifier="complexCurves",
    level="segment",
    title="Complex Curves",
    description="One or more curves is suspiciously complex.",
    testFunction=testForComplexCurves,
    drawingFunction=drawComplexCurves
)

# Crossed Handles

def testForCrossedHandles(glyph):
    """
    Handles shouldn't intersect.
    """
    crossedHandles = {}
    for index, contour in enumerate(glyph):
        pt0 = _unwrapPoint(contour[-1].onCurve)
        for segment in contour:
            pt3 = _unwrapPoint(segment.onCurve)
            if segment.type == "curve":
                pt1, pt2 = [_unwrapPoint(p) for p in segment.offCurve]
                # direct intersection
                direct = _intersectLines((pt0, pt1), (pt2, pt3))
                if direct:
                    if index not in crossedHandles:
                        crossedHandles[index] = []
                    crossedHandles[index].append(dict(points=(pt0, pt1, pt2, pt3), intersection=direct))
                # indirect intersection
                else:
                    while 1:
                        # bcp1 = ray, bcp2 = segment
                        angle = _calcAngle(pt0, pt1)
                        if angle in (0, 180.0):
                            t1 = (pt0[0] + 1000, pt0[1])
                            t2 = (pt0[0] - 1000, pt0[1])
                        else:
                            yOffset = _getAngleOffset(angle, 1000)
                            t1 = (pt0[0] + 1000, pt0[1] + yOffset)
                            t2 = (pt0[0] - 1000, pt0[1] - yOffset)
                        indirect = _intersectLines((t1, t2), (pt2, pt3))
                        if indirect:
                            if index not in crossedHandles:
                                crossedHandles[index] = []
                            crossedHandles[index].append(dict(points=(pt0, indirect, pt2, pt3), intersection=indirect))
                            break
                        # bcp1 = segment, bcp2 = ray
                        angle = _calcAngle(pt3, pt2)
                        if angle in (90.0, 270.0):
                            t1 = (pt3[0], pt3[1] + 1000)
                            t2 = (pt3[0], pt3[1] - 1000)
                        else:
                            yOffset = _getAngleOffset(angle, 1000)
                            t1 = (pt3[0] + 1000, pt3[1] + yOffset)
                            t2 = (pt3[0] - 1000, pt3[1] - yOffset)
                        indirect = _intersectLines((t1, t2), (pt0, pt1))
                        if indirect:
                            if index not in crossedHandles:
                                crossedHandles[index] = []
                            crossedHandles[index].append(dict(points=(pt0, pt1, indirect, pt3), intersection=indirect))
                            break
                        break
            pt0 = pt3
    return crossedHandles

def drawCrossedHandles(contours, scale, glyph):
    d = 10 * scale
    h = d / 2.0
    color = colorReview()
    color.set()
    for contourIndex, segments in contours.items():
        for segment in segments:
            pt1, pt2, pt3, pt4 = segment["points"]
            pt5 = segment["intersection"]
            path1 = NSBezierPath.bezierPath()
            path2 = NSBezierPath.bezierPath()
            path1.moveToPoint_(pt1)
            path1.lineToPoint_(pt2)
            path1.moveToPoint_(pt3)
            path1.lineToPoint_(pt4)
            x, y = pt5
            r = ((x - h, y - h), (d, d))
            path2.appendBezierPathWithOvalInRect_(r)
            path1.setLineWidth_(3 * scale)
            path1.setLineCapStyle_(NSRoundLineCapStyle)
            path1.stroke()
            path2.fill()
            drawString((x, y - (12 * scale)), "Crossed Handles", 10, scale, color, backgroundColor=NSColor.whiteColor())

registerTest(
    identifier="crossedHandles",
    level="segment",
    title="Crossed Handles",
    description="One or more curves contain crossed handles.",
    testFunction=testForCrossedHandles,
    drawingFunction=drawCrossedHandles
)

# Unnecessary Handles

def testForUnnecessaryHandles(glyph):
    """
    Handles shouldn't be used if they aren't doing anything.
    """
    unnecessaryHandles = {}
    for index, contour in enumerate(glyph):
        prevPoint = contour[-1].onCurve
        for segment in contour:
            if segment.type == "curve":
                pt0 = prevPoint
                pt1, pt2 = segment.offCurve
                pt3 = segment.onCurve
                lineAngle = _calcAngle(pt0, pt3, 0)
                bcpAngle1 = bcpAngle2 = None
                if (pt0.x, pt0.y) != (pt1.x, pt1.y):
                    bcpAngle1 = _calcAngle(pt0, pt1, 0)
                if (pt2.x, pt2.y) != (pt3.x, pt3.y):
                    bcpAngle2 = _calcAngle(pt2, pt3, 0)
                if bcpAngle1 == lineAngle and bcpAngle2 == lineAngle:
                    if index not in unnecessaryHandles:
                        unnecessaryHandles[index] = []
                    unnecessaryHandles[index].append((_unwrapPoint(pt1), _unwrapPoint(pt2)))
            prevPoint = segment.onCurve
    return unnecessaryHandles

def drawUnnecessaryHandles(contours, scale, glyph):
    color = colorRemove()
    color.set()
    d = 10 * scale
    h = d / 2.0
    for contourIndex, points in contours.items():
        for bcp1, bcp2 in points:
            # line
            path1 = NSBezierPath.bezierPath()
            path1.moveToPoint_(bcp1)
            path1.lineToPoint_(bcp2)
            path1.setLineWidth_(3 * scale)
            path1.stroke()
            # dots
            path2 = NSBezierPath.bezierPath()
            for (x, y) in (bcp1, bcp2):
                r = ((x - h, y - h), (d, d))
                path2.appendBezierPathWithOvalInRect_(r)
            path2.setLineWidth_(scale)
            path2.stroke()
            # text
            mid = calcMid(bcp1, bcp2)
            drawString(mid, "Unnecessary Handles", 10, scale, color, backgroundColor=NSColor.whiteColor())

registerTest(
    identifier="unnecessaryHandles",
    level="segment",
    title="Unnecessary Handles",
    description="One or more curves has unnecessary handles.",
    testFunction=testForUnnecessaryHandles,
    drawingFunction=drawUnnecessaryHandles
)

# Uneven Handles

def testForUnevenHandles(glyph):
    """
    Handles should share the workload as evenly as possible.
    """
    unevenHandles = {}
    for index, contour in enumerate(glyph):
        prevPoint = contour[-1].onCurve
        for segment in contour:
            if segment.type == "curve":
                # create perpendicular lines off
                # of each off curve
                pt0 = _unwrapPoint(prevPoint)
                pt1, pt2 = [_unwrapPoint(pt) for pt in segment.offCurve]
                pt3 = _unwrapPoint(segment.onCurve)
                angle1 = _calcAngle(pt0, pt1) - 90
                line1 = _createLineThroughPoint(pt0, angle1)
                angle2 = _calcAngle(pt2, pt3) - 90
                line2 = _createLineThroughPoint(pt3, angle2)
                # find the intersection of these lines
                intersection = _intersectLines(line1, line2)
                if intersection is not None:
                    # draw a line between the off curves and the intersection
                    # and find out where these lines intersect the curve
                    segmentIntersection1 = _getSegmentIntersection(pt1, intersection, (pt0, pt1, pt2, pt3))
                    segmentIntersection2 = _getSegmentIntersection(pt2, intersection, (pt0, pt1, pt2, pt3))
                    if segmentIntersection1 is not None and segmentIntersection2 is not None:
                        # assemble the off curves and their intersetions into lines
                        line1 = (pt1, segmentIntersection1)
                        line2 = (pt2, segmentIntersection2)
                        # measure and compare these
                        length1, length2 = sorted((_getLineLength(*line1), _getLineLength(*line2)))
                        # if they are not both very short
                        # calculate the ratio
                        if length1 >= 3 and length2 >= 3:
                            r = length2 / float(length1)
                            # if outside acceptable range, flag
                            if r > 1.5:
                                if index not in unevenHandles:
                                    unevenHandles[index] = []
                                unevenHandles[index].append((line1, line2))
            prevPoint = segment.onCurve
    return unevenHandles

def drawUnevenHandles(contours, scale, glyph):
    color = colorReview()
    color.set()
    for index, segments in contours.items():
        for line1, line2 in segments:
            path1 = NSBezierPath.bezierPath()
            path2 = NSBezierPath.bezierPath()
            path1.moveToPoint_(line1[0])
            path1.lineToPoint_(line1[1])
            path1.moveToPoint_(line2[0])
            path1.lineToPoint_(line2[1])
            mid1 = calcMid(*line1)
            mid2 = calcMid(*line2)
            path2.moveToPoint_(mid1)
            path2.lineToPoint_(mid2)
            path1.setLineWidth_(3 * scale)
            path2.setLineWidth_(scale)
            path1.stroke()
            path2.stroke()
            mid = calcMid(mid1, mid2)
            drawString(mid, "Uneven Handles", 10, scale, color, backgroundColor=NSColor.whiteColor())

registerTest(
    identifier="unevenHandles",
    level="segment",
    title="Uneven Handles",
    description="One or more curves has uneven handles.",
    testFunction=testForUnevenHandles,
    drawingFunction=drawUnevenHandles
)

# -----------------
# Point Level Tests
# -----------------

# Stray Points

def testForStrayPoints(glyph):
    """
    There should be no stray points.
    """
    strayPoints = {}
    for index, contour in enumerate(glyph):
        if len(contour) == 1:
            pt = contour[0].onCurve
            pt = (pt.x, pt.y)
            strayPoints[index] = pt
    return strayPoints

def drawStrayPoints(contours, scale, glyph):
    color = colorRemove()
    path = NSBezierPath.bezierPath()
    d = 20 * scale
    h = d / 2.0
    for contourIndex, (x, y) in contours.items():
        r = ((x - h, y - h), (d, d))
        path.appendBezierPathWithOvalInRect_(r)
        drawString((x, y - d), "Stray Point", 10, scale, color)
    color.set()
    path.setLineWidth_(scale)
    path.stroke()

registerTest(
    identifier="strayPoints",
    level="point",
    title="Stray Points",
    description="One or more stray points are present.",
    testFunction=testForStrayPoints,
    drawingFunction=drawStrayPoints
)

# Unnecessary Points

def testForUnnecessaryPoints(glyph):
    """
    Consecutive segments shouldn't have the same angle.
    """
    unnecessaryPoints = {}
    for index, contour in enumerate(glyph):
        for segmentIndex, segment in enumerate(contour):
            if segment.type == "line":
                prevSegment = contour[segmentIndex - 1]
                nextSegment = contour[(segmentIndex + 1) % len(contour)]
                if nextSegment.type == "line":
                    thisAngle = _calcAngle(prevSegment.onCurve, segment.onCurve)
                    nextAngle = _calcAngle(segment.onCurve, nextSegment.onCurve)
                    if thisAngle == nextAngle:
                        if index not in unnecessaryPoints:
                            unnecessaryPoints[index] = []
                        unnecessaryPoints[index].append(_unwrapPoint(segment.onCurve))
    return unnecessaryPoints

def drawUnnecessaryPoints(contours, scale, glyph):
    color = colorRemove()
    path = NSBezierPath.bezierPath()
    for contourIndex, points in contours.items():
        for pt in points:
            drawDeleteMark(pt, scale, path)
            x, y = pt
            drawString((x, y - (10 * scale)), "Unnecessary Point", 10, scale, color)
    color.set()
    path.setLineWidth_(2 * scale)
    path.stroke()

registerTest(
    identifier="unnecessaryPoints",
    level="point",
    title="Unnecessary Points",
    description="One or more unnecessary points are present in lines.",
    testFunction=testForUnnecessaryPoints,
    drawingFunction=drawUnnecessaryPoints
)

# Overlapping Points

def testForOverlappingPoints(glyph):
    """
    Consequtive points should not overlap.
    """
    overlappingPoints = {}
    for index, contour in enumerate(glyph):
        if len(contour) == 1:
            continue
        prev = _unwrapPoint(contour[-1].onCurve)
        for segment in contour:
            point = _unwrapPoint(segment.onCurve)
            if point == prev:
                if index not in overlappingPoints:
                    overlappingPoints[index] = set()
                overlappingPoints[index].add(point)
            prev = point
    return overlappingPoints

def drawOverlappingPoints(contours, scale, glyph):
    color = colorRemove()
    path = NSBezierPath.bezierPath()
    d = 10 * scale
    h = d / 2.0
    q = h / 2.0
    for contourIndex, points in contours.items():
        for (x, y) in points:
            r = ((x - d + q, y - q), (d, d))
            path.appendBezierPathWithOvalInRect_(r)
            r = ((x - q, y - d + q), (d, d))
            path.appendBezierPathWithOvalInRect_(r)
            drawString((x, y - (12 * scale)), "Overlapping Points", 10, scale, color)
    color.set()
    path.fill()

registerTest(
    identifier="overlappingPoints",
    level="point",
    title="Overlapping Points",
    description="Two or more points are overlapping.",
    testFunction=testForOverlappingPoints,
    drawingFunction=drawOverlappingPoints
)


# --------------
# Test Utilities
# --------------

def _getOnCurves(contour):
    points = set()
    for segement in contour:
        pt = segement.onCurve
        points.add((pt.x, pt.y))
    return points

def _unwrapPoint(pt):
    return pt.x, pt.y

def _intersectLines((a1, a2), (b1, b2)):
    # adapted from: http://www.kevlindev.com/gui/math/intersection/Intersection.js
    ua_t = (b2[0] - b1[0]) * (a1[1] - b1[1]) - (b2[1] - b1[1]) * (a1[0] - b1[0]);
    ub_t = (a2[0] - a1[0]) * (a1[1] - b1[1]) - (a2[1] - a1[1]) * (a1[0] - b1[0]);
    u_b  = (b2[1] - b1[1]) * (a2[0] - a1[0]) - (b2[0] - b1[0]) * (a2[1] - a1[1]);
    if u_b != 0:
        ua = ua_t / u_b;
        ub = ub_t / u_b;
        if 0 <= ua and ua <= 1 and 0 <= ub and ub <= 1:
            return a1[0] + ua * (a2[0] - a1[0]), a1[1] + ua * (a2[1] - a1[1])
        else:
            return None
    else:
        return None

def _calcAngle(point1, point2, r=None):
    if not isinstance(point1, tuple):
        point1 = _unwrapPoint(point1)
    if not isinstance(point2, tuple):
        point2 = _unwrapPoint(point2)
    width = point2[0] - point1[0]
    height = point2[1] - point1[1]
    angle = round(math.atan2(height, width) * 180 / math.pi, 3)
    if r is not None:
        angle = round(angle, r)
    return angle

def _getAngleOffset(angle, distance):
    A = 90
    B = angle
    C = 180 - (A + B)
    if C == 0:
        return 0
    c = distance
    A = math.radians(A)
    B = math.radians(B)
    C = math.radians(C)
    b = (c * math.sin(B)) / math.sin(C)
    return b

def _createLineThroughPoint(pt, angle):
    angle = math.radians(angle)
    length = 100000
    x1 = math.cos(angle) * -length + pt[0]
    y1 = math.sin(angle) * -length + pt[1]
    x2 = math.cos(angle) * length + pt[0]
    y2 = math.sin(angle) * length + pt[1]
    return (x1, y1), (x2, y2)

def _getLineLength(pt1, pt2):
    return math.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])

def _getAreaOfTriangle(pt1, pt2, pt3):
    a = _getLineLength(pt1, pt2)
    b = _getLineLength(pt2, pt3)
    c = _getLineLength(pt3, pt1)
    s = (a + b + c) / 2.0
    area = math.sqrt(s * (s - a) * (s - b) * (s - c))
    return area

def _getSegmentIntersection(bcp, intersection, curve):
    pt0, pt1, pt2, pt3 = curve
    intersection = bezierTools.intersectCubicLine(pt0, pt1, pt2, pt3, bcp, intersection)
    if intersection:
        point = intersection.points[0]
        return point.x, point.y
    return None

# -----------------
# Drawing Utilities
# -----------------

def drawDeleteMark(pt, scale, path):
    h = 6 * scale
    x, y = pt
    x1 = x - h
    x2 = x + h
    y1 = y - h
    y2 = y + h
    path.moveToPoint_((x1, y1))
    path.lineToPoint_((x2, y2))
    path.moveToPoint_((x1, y2))
    path.lineToPoint_((x2, y1))

def drawString(pt, text, size, scale, color, alignment="center", backgroundColor=None):
    attributes = attributes = {
        NSFontAttributeName : NSFont.fontWithName_size_("Lucida Grande", size * scale),
        NSForegroundColorAttributeName : color
    }
    if backgroundColor is not None:
        text = " " + text + " "
        attributes[NSBackgroundColorAttributeName] = backgroundColor
    text = NSAttributedString.alloc().initWithString_attributes_(text, attributes)
    x, y = pt
    if alignment == "center":
        width, height = text.size()
        x -= width / 2.0
        y -= height / 2.0
    elif alignment == "right":
        width, height = text.size()
        x -= width
    text.drawAtPoint_((x, y))

def calcMid(pt1, pt2):
    x1, y1 = pt1
    x2, y2 = pt2
    x = x1 - ((x1 - x2) / 2)
    y = y1 - ((y1 - y2) / 2)
    return x, y


if __name__ == "__main__":
    # register the factory
    if roboFontVersion > "1.5.1":
        _registerFactory()
    # sanity check to make sure that the tests are consistently registered
    assert set(reportOrder) == set(testRegistry.keys())
    assert set(drawingOrder) == set(testRegistry.keys())
    # register the defaults
    registerGlyphNannyDefaults()
    # boot the observer
    glyphNannyObserver = GlyphNannyObserver()
    # if debugging, kill any instances of this observer that are already running
    if DEBUG:
        from lib.eventTools.eventManager import allObservers
        for event, observer in allObservers():
            if observer.__class__.__name__ == "GlyphNannyObserver":
                unregisterGlyphNannyObserver(observer)
    # register it
    registerGlyphNannyObserver(glyphNannyObserver)
    # if debugging, show the windows
    if DEBUG:
        GlyphNannyPrefsWindow()
        GlyphNannyTestFontsWindow()
