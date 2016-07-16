import os
import re
import math
import base64
from fontTools.misc import bezierTools as ftBezierTools
from fontTools.misc import arrayTools as ftArrayTools
from fontTools.agl import AGL2UV
from fontTools.pens.cocoaPen import CocoaPen
from fontTools.pens.transformPen import TransformPen
from robofab.pens.digestPen import DigestPointPen
from AppKit import *
import vanilla
from vanilla import dialogs
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.roboFont import CurrentFont, AllFonts
from mojo.roboFont import version as roboFontVersion
from mojo.UI import UpdateCurrentGlyphView, HTMLView
from mojo.events import addObserver, removeObserver
from mojo.extensions import getExtensionDefault, setExtensionDefault, setExtensionDefaultColor
from lib.tools import bezierTools as rfBezierTools

from defaultManager import defaults, defaultKeyObserverVisibility, defaultKeyTitleVisibility, defaultKeyTestStates, defaultKeyColorInform, defaultKeyColorReview, defaultKeyColorRemove, defaultKeyColorInsert

DEBUG = False

# --------
# Defaults
# --------

generalLineWidth = 1
highlightLineWidth = 4
textSize = 10
textVerticalOffset = 10


def registerGlyphNannyDefaults():
    storage = {
        defaultKeyObserverVisibility : False,
        defaultKeyTitleVisibility : True,
        defaultKeyTestStates : {}
    }
    for key in sorted(testRegistry.keys()):
        storage[defaultKeyTestStates][key] = True
    try:
        from mojo.extensions import registerExtensionsDefaults
    except ImportError:
        def registerExtensionsDefaults(d):
            for k, v in d.items():
                e = getExtensionDefault(k, fallback="__fallback__")
                if e == "__fallback__":
                    setExtensionDefault(k, v)
    registerExtensionsDefaults(storage)
    nested = getExtensionDefault(defaultKeyTestStates)
    for key, default in storage[defaultKeyTestStates].items():
        if key not in nested:
            nested[key] = default
            setExtensionDefault(defaultKeyTestStates, nested)
    defaults.reload()




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
        display = defaults.getValue(defaultKeyObserverVisibility)
        if not display:
            return
        # make sure there is something to be tested
        glyph = info["glyph"]
        if glyph is None:
            return
        # get the report
        font = glyph.getParent()
        testStates = defaults.getValue(defaultKeyTestStates)
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

        self.w = vanilla.Window((264, 457), "Glyph Nanny Preferences")

        # global visibility
        state = defaults.getValue(defaultKeyObserverVisibility)
        self.w.displayLiveReportTitle = vanilla.TextBox((15, 15, 150, 17), "Live report display is:")
        self.w.displayLiveReportRadioGroup = vanilla.RadioGroup((159, 15, -15, 17), ["On", "Off"], isVertical=False, callback=self.displayLiveReportRadioGroupCallback)
        self.w.displayLiveReportRadioGroup.set(not state)

        # test states
        _buildGlyphTestTabs(self, 50)

        # colors
        colors = [
            ("Information", defaults.colorInform, defaultKeyColorInform),
            ("Review Something", defaults.colorReview, defaultKeyColorReview),
            ("Insert Something", defaults.colorInsert, defaultKeyColorInsert),
            ("Remove Something", defaults.colorRemove, defaultKeyColorRemove)
        ]
        top = 290
        for title, color, key in colors:
            control = vanilla.ColorWell((15, top, 70, 25), color=color, callback=self.noteColorColorWellCallback)
            self.colorControlToKey[control] = key
            setattr(self.w, "colorWell_" + title, control)
            control = vanilla.TextBox((90, top + 3, -15, 17), title)
            setattr(self.w, "colorTitle_" + title, control)
            top += 32

        # titles
        state = defaults.getValue(defaultKeyTitleVisibility)
        self.w.displayReportTitlesCheckBox = vanilla.CheckBox((15, 425, -15, 22), "Show Report Titles", value=state, callback=self.displayReportTitlesCheckBoxCallback)

        self.w.open()

    def displayLiveReportRadioGroupCallback(self, sender):
        state = not sender.get()
        setExtensionDefault(defaultKeyObserverVisibility, state)
        defaults.reload()
        UpdateCurrentGlyphView()

    def testStateTabSelectorCallback(self, sender):
        tab = sender.get()
        self.w.testStateBox.testStateTabs.set(tab)

    def testStateCheckBoxCallback(self, sender):
        identifier = self.testStateControlToIdentifier[sender]
        state = sender.get()
        storage = defaults.getValue(defaultKeyTestStates)
        storage[identifier] = state
        setExtensionDefault(defaultKeyTestStates, storage)
        defaults.reload()
        UpdateCurrentGlyphView()

    def noteColorColorWellCallback(self, sender):
        color = sender.get()
        key = self.colorControlToKey[sender]
        setExtensionDefaultColor(key, color)
        defaults.reload()
        UpdateCurrentGlyphView()

    def displayReportTitlesCheckBoxCallback(self, sender):
        state = sender.get()
        setExtensionDefault(defaultKeyTitleVisibility, state)
        defaults.reload()
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
               state = defaults.getValue(defaultKeyTestStates)[identifier]
               control = vanilla.CheckBox((15, top, -15, 22), testData["title"], value=state, callback=controller.testStateCheckBoxCallback)
               top += 25
               controller.testStateControlToIdentifier[control] = identifier
               setattr(tab, "testStateCheckBox_" + identifier, control)
    controller.w.testStateTabSelector = vanilla.PopUpButton((72, viewTop, 120, 20), groupTitles, callback=controller.testStateTabSelectorCallback)


# --------------
# Prefs Shortcut
# --------------

def toggleObserverVisibility():
    state = not defaults.getValue(defaultKeyObserverVisibility)
    setExtensionDefault(defaultKeyObserverVisibility, state)
    defaults.reload()
    UpdateCurrentGlyphView()


# ----------------
# Test Font Window
# ----------------

class GlyphNannyTestFontsWindow(BaseWindowController):

    def __init__(self):
        self.testStateControlToIdentifier = {}
        self.w = vanilla.Window((264, 350), "Glyph Nanny")
        # test states
        _buildGlyphTestTabs(self, 15)
        # global options
        self.w.ignoreOverlapCheckBox = vanilla.CheckBox((15, 245, -15, 22), "Ignore Outline Overlaps")
        # test buttons
        self.w.testCurrentButton = vanilla.Button((15, 285, -15, 20), "Test Current Font", callback=self.testCurrentButtonCallback)
        self.w.testAllButton = vanilla.Button((15, 315, -15, 20), "Test All Open Fonts", callback=self.testAllButtonCallback)

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
        self._processFont(font)

    def testAllButtonCallback(self, sender):
        fonts = AllFonts()
        if not fonts:
            dialogs.message("There are no fonts to test.", "Open a font and try again.")
            return
        for font in fonts:
            self._processFont(font)

    def _processFont(self, font):
        testStates = self.getTestStates()
        ignoreOverlap = self.w.ignoreOverlapCheckBox.get()
        progressBar = self.startProgress(tickCount=len(font))
        try:
            html, glyphsWithIssues = getFontReport(font, testStates, ignoreOverlap=ignoreOverlap, progressBar=progressBar)
        finally:
            progressBar.close()
        FontReportWindow(font, html, glyphsWithIssues)


class FontReportWindow(BaseWindowController):

    def __init__(self, font, html, glyphsWithIssues):
        self.font = font
        self.html = html
        self.glyphsWithIssues = glyphsWithIssues
        title = "Glyph Nanny Report: Unsaved Font"
        if font.path is not None:
            title = u"Glyph Nanny Report: %s" % os.path.basename(font.path)
        self.w = vanilla.Window((600, 400), title=title, minSize=(200, 200))
        self.w.reportView = HTMLView((0, 0, -0, -50))
        self.w.reportView.setHTML(html)
        self.w.line = vanilla.HorizontalLine((0, -50, 0, 1))
        self.w.saveButton = vanilla.Button((15, -35, 100, 20), "Save Report", callback=self.saveButtonCallback)
        self.w.markButton = vanilla.Button((-115, -35, 100, 20), "Mark Glyphs", callback=self.markButtonCallback)
        self.w.open()

    def saveButtonCallback(self, sender):
        fileName = "Untitled Font"
        directory = None
        if self.font.path is not None:
            directory, fileName = os.path.split(self.font.path)
            fileName = os.path.splitext(fileName)[0]
        fileName += " Glyph Nanny Report"
        self.showPutFile(
            fileTypes=["html"],
            callback=self._writeHTML,
            fileName=fileName,
            directory=directory
        )

    def _writeHTML(self, path):
        if not path:
            return
        f = open(path, "wb")
        f.write(self.html)
        f.close()

    def markButtonCallback(self, sender):
        for name in self.font.keys():
            if name in self.glyphsWithIssues:
                color = (1, 0, 0, 0.5)
            else:
                color = None
            self.font[name].mark = color

# ------
# Orders
# ------

reportOrder = """
unicodeValue
componentMetrics
ligatureMetrics
metricsSymmetry
stemWidths
strayPoints
smallContours
openContours
duplicateContours
extremePoints
curveSymmetry
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
componentMetrics
ligatureMetrics
metricsSymmetry
stemWidths
smallContours
pointsNearVerticalMetrics
complexCurves
crossedHandles
unsmoothSmooths
straightLines
duplicateContours
openContours
extremePoints
curveSymmetry
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

def getFontReport(font, testStates, ignoreOverlap=False, progressBar=None):
    """
    Get a report about all glyphs in the font.

    testStates should be a dict of the test names
    and a boolean indicating if they should be
    executed or not.
    """
    if ignoreOverlap:
        font = font.copy()
    html = fontReportTemplate
    glyphReports = []
    glyphsWithIssues = []
    if roboFontVersion > "1.5.1":
        testStates = dictToTuple(testStates)
    for name in font.glyphOrder:
        if progressBar is not None:
            progressBar.update(u"Analyzing %s..." % name)
        glyph = font[name]
        if ignoreOverlap:
            glyph.removeOverlap()
        if roboFontVersion > "1.5.1":
            report = glyph.getRepresentation("com.typesupply.GlyphNanny.Report", testStates=testStates)
        else:
            report = getGlyphReport(font, glyph, testStates)
        l = []
        for key in reportOrder:
            data = testRegistry[key]
            description = data["description"]
            value = report.get(key)
            if value:
                l.append("<li>%s</li>" % description)
        if l:
            png = _makeFontReportPNG(glyph, report)
            r = glyphReportTemplate
            r = r.replace("__glyphName__", name)
            r = r.replace("__glyphReportItems__", "".join(l))
            r = r.replace("__glyphPNG__", png)
            glyphReports.append(r)
            glyphsWithIssues.append(name)
    html = html.replace("__glyphReports__", "".join(glyphReports))
    return html, glyphsWithIssues

fontReportTemplate = """
<html>
    <head>
        <style>
            body {
                font-family: Helvetica;
                line-height: 1.4em;
                font-size: 15px;
                padding: 10px;
                background-color: white;
            }

            .glyphReport {
              margin-bottom: 40px;
            }

            .glyphReport ul {
              margin: 0;
                width: 380px;
                padding-left: 1em;
                float: left;
            }

            .glyphReport li {
                padding-left: 0;
            }

            .glyphReport h1 {
                font-size: 20px;
                border-bottom: 1px solid black;
                padding: 0 0 0.5em 0;
                margin: 0 0 1em 0;
            }

            .glyphImage {
                position: relative;
                left: 430px;
                height: 700px;
                width: 800px;
                background-size: Auto 100%;
                background-repeat: no-repeat;
            }
        </style>
    </head>
    <body>
        __glyphReports__
    </body>
</html>
"""

glyphReportTemplate = """
        <div class="glyphReport">
          <h1>__glyphName__</h1>
            <ul>
                __glyphReportItems__
            </ul>
            <div class="glyphImage" style="background-image: url(data:image/png;base64,__glyphPNG__);"></div>
        </div>
"""

def _makeFontReportPNG(glyph, report):
    font = glyph.getParent()
    upm = font.info.unitsPerEm
    xBuffer = upm * 0.3
    yBuffer = xBuffer * 0.5
    verticalMetrics = set([
        font.info.descender,
        0,
        font.info.xHeight,
        font.info.capHeight,
        font.info.ascender
    ])
    bottom = min(verticalMetrics)
    top = max(verticalMetrics)
    left = 0
    right = glyph.width
    width = left + right + (xBuffer * 2)
    height = top - bottom + (yBuffer * 2)
    # start the image
    image = NSImage.alloc().initWithSize_((width, height))
    image.lockFocus()
    # paint the background
    NSColor.whiteColor().set()
    NSRectFill(((0, 0), image.size()))
    # apply the buffer
    transform = NSAffineTransform.transform()
    transform.translateXBy_yBy_(xBuffer, yBuffer)
    transform.translateXBy_yBy_(0, -bottom)
    transform.concat()
    scale = 2.0
    # draw the metrics
    path = NSBezierPath.bezierPath()
    for y in verticalMetrics:
        drawLine((-xBuffer, y), (width, y), scale=scale, path=path)
    path.moveToPoint_((0, -yBuffer+bottom))
    path.lineToPoint_((0, height))
    path.moveToPoint_((right, -yBuffer+bottom))
    path.lineToPoint_((right, height))
    NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 0.1).set()
    path.setLineWidth_(1 * scale)
    path.stroke()
    # draw the report
    for key in drawingOrder:
        data = report.get(key)
        if data:
            drawingFunction = testRegistry[key]["drawingFunction"]
            if drawingFunction is not None:
                drawingFunction(data, scale, glyph)
    # draw the glyph
    pen = CocoaPen(font)
    glyph.draw(pen)
    path = pen.path
    NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 0.1).set()
    path.fill()
    NSColor.blackColor().set()
    path.setLineWidth_(1 * scale)
    path.stroke()
    path = NSBezierPath.bezierPath()
    handlePath = NSBezierPath.bezierPath()
    for contour in glyph:
        prev = contour.points[-1]
        for point in contour.points:
            t = point.type
            x = point.x
            y = point.y
            if t in ("move", "line") or (t == "curve" and not point.smooth):
                s = 7 * scale
                m = path.appendBezierPathWithRect_
            elif t in ("curve", "qCurve"):
                s = 8 * scale
                m = path.appendBezierPathWithOvalInRect_
            else:
                s = 5 * scale
                m = path.appendBezierPathWithOvalInRect_
            h = s * 0.5
            r = ((x - h, y - h), (s, s))
            m(r)
            if t == "offCurve" and prev.type in ("move", "line", "curve"):
                handlePath.moveToPoint_((prev.x, prev.y))
                handlePath.lineToPoint_((x, y))
            elif t in ("move", "line", "curve") and prev.type == "offCurve":
                handlePath.moveToPoint_((prev.x, prev.y))
                handlePath.lineToPoint_((x, y))
            prev = point
    NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 0.2).set()
    handlePath.setLineWidth_(1 * scale)
    handlePath.stroke()
    NSColor.whiteColor().set()
    path.fill()
    path.setLineWidth_(1 * scale)
    NSColor.blackColor().set()
    path.stroke()
    image.unlockFocus()
    # convert to base64
    data = image.TIFFRepresentation()
    rep = NSBitmapImageRep.imageRepWithData_(data)
    data = rep.representationUsingType_properties_(NSPNGFileType, None)
    data = base64.b64encode(data)
    return data


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
    if text:
        text = "\n".join(text)
        x = 50
        y = -50
        drawString((x, y), text, scale, defaults.colorInform, hAlignment="left")

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


# Stem Consistency

def testStemWidths(glyph):
    """
    Stem widths should be consistent.
    """
    hProblems = vProblems = None
    font = glyph.getParent()
    tolerance = 5
    # horizontal
    hStems = [_StemWrapper(v, tolerance) for v in font.info.postscriptStemSnapH]
    if hStems:
        hProblems = _findStemProblems(glyph, hStems, "h")
    # vertical
    vStems = [_StemWrapper(v, tolerance) for v in font.info.postscriptStemSnapV]
    if vStems:
        vProblems = _findStemProblems(glyph, vStems, "v")
    # report
    if hProblems or vProblems:
        stemProblems = dict(
            h=hProblems,
            v=vProblems
        )
        return stemProblems
    return None

def drawStemWidths(data, scale, glyph):
    hProblems = data["h"]
    vProblems = data["v"]
    if not hProblems and not vProblems:
        return
    font = glyph.getParent()
    b = font.info.unitsPerEm * 0.25
    color = textColor = defaults.colorReview
    # horizontal
    x = -b
    w = glyph.width + (b * 2)
    for y1, y2, xPositions in hProblems:
        xM = calcCenter(*xPositions)
        color.set()
        path = drawLine((xM, y1), (xM, y2), scale, arrowStart=True, arrowEnd=True)
        path.setLineWidth_(generalLineWidth * scale)
        path.stroke()
        if defaults.showTitles:
            tX, tY = calcMid((xM, y1), (xM, y2))
            drawString((tX, tY), "Check Stem", scale, textColor, backgroundColor=NSColor.whiteColor())
    # horizontal
    y = font.info.descender - b
    h = max((font.info.ascender, font.info.capHeight)) - y + (b * 2)
    for x1, x2, yPositions in vProblems:
        yM = calcCenter(*yPositions)
        color.set()
        path = drawLine((x1, yM), (x2, yM), scale, arrowStart=True, arrowEnd=True)
        path.setLineWidth_(generalLineWidth * scale)
        path.stroke()
        if defaults.showTitles:
            tX, tY = calcMid((x1, yM), (x2, yM))
            drawString((tX, tY), "Check Stem", scale, textColor, vAlignment="center", backgroundColor=NSColor.whiteColor())

registerTest(
    identifier="stemWidths",
    level="glyph",
    title="Stem Widths",
    description="One or more stems do not match the registered values.",
    testFunction=testStemWidths,
    drawingFunction=drawStemWidths
)

def _findStemProblems(glyph, targetStems, stemDirection):
    stems = set()
    # h/v abstraction
    if stemDirection == "h":
        primaryCoordinate = 1
        secondaryCoordinate = 0
        desiredClockwiseAngle = 0
        desiredCounterAngle = 180
    else:
        primaryCoordinate = 0
        secondaryCoordinate = 1
        desiredClockwiseAngle = -90
        desiredCounterAngle = 90
    # structure the contour and line data for efficient processing
    contours = {
        True : [],
        False : []
    }
    for contour in glyph:
        contourDirection = contour.clockwise
        if hasattr(contour, "bounds"):
            bounds = contour.bounds
        else:
            bounds = contour.box
        lines = {}
        # line to
        previous = _unwrapPoint(contour[-1].onCurve)
        for segment in contour:
            point = _unwrapPoint(segment.onCurve)
            if segment.type == "line":
                # only process completely horizontal/vertical lines
                # that have a length greater than 0
                if (previous[primaryCoordinate] == point[primaryCoordinate]) and (previous[secondaryCoordinate] != point[secondaryCoordinate]):
                    angle = _calcAngle(previous, point)
                    p = point[primaryCoordinate]
                    s1 = previous[secondaryCoordinate]
                    s2 = point[secondaryCoordinate]
                    s1, s2 = sorted((s1, s2))
                    if angle not in lines:
                        lines[angle] = {}
                    if p not in lines[angle]:
                        lines[angle][p] = []
                    lines[angle][p].append((s1, s2))
            previous = point
        # imply stems from curves by using BCP handles
        previous = contour[-1]
        for segment in contour:
            if segment.type == "curve" and previous.type == "curve":
                bcp1 = _unwrapPoint(previous[1])
                bcp2 = _unwrapPoint(segment[-1])
                if bcp1[primaryCoordinate] == bcp2[primaryCoordinate]:
                    angle = _calcAngle(bcp1, bcp2)
                    p = bcp1[primaryCoordinate]
                    s1 = bcp1[secondaryCoordinate]
                    s2 = bcp2[secondaryCoordinate]
                    s1, s2 = sorted((s1, s2))
                    if angle not in lines:
                        lines[angle] = {}
                    if p not in lines[angle]:
                        lines[angle][p] = []
                    lines[angle][p].append((s1, s2))
            previous = segment
        contours[contourDirection].append((bounds, lines))
    # single contours
    for clockwise, directionContours in contours.items():
        for contour in directionContours:
            bounds, data = contour
            for angle1, lineData1 in data.items():
                for angle2, lineData2 in data.items():
                    if angle1 == angle2:
                        continue
                    if clockwise and angle1 == desiredClockwiseAngle:
                        continue
                    if not clockwise and angle1 == desiredCounterAngle:
                        continue
                    for p1, lines1 in lineData1.items():
                        for p2, lines2 in lineData2.items():
                            if p2 <= p1:
                                continue
                            for s1a, s1b in lines1:
                                for s2a, s2b in lines2:
                                    overlap = _linesOverlap(s1a, s1b, s2a, s2b)
                                    if not overlap:
                                        continue
                                    w = p2 - p1
                                    hits = []
                                    for stem in targetStems:
                                        if w == stem:
                                            d = stem.diff(w)
                                            if d:
                                                hits.append((d, stem.value, (s1a, s1b, s2a, s2b)))
                                    if hits:
                                        hit = min(hits)
                                        w = hit[1]
                                        s = hit[2]
                                        stems.add((p1, p1 + w, s))
    # double contours to test
    for clockwiseContour in contours[True]:
        clockwiseBounds = clockwiseContour[0]
        for counterContour in contours[False]:
            counterBounds = counterContour[0]
            overlap = ftArrayTools.sectRect(clockwiseBounds, counterBounds)[0]
            if not overlap:
                continue
            clockwiseData = clockwiseContour[1]
            counterData = counterContour[1]
            for clockwiseAngle, clockwiseLineData in clockwiseContour[1].items():
                for counterAngle, counterLineData in counterContour[1].items():
                    if clockwiseAngle == counterAngle:
                        continue
                    for clockwiseP, clockwiseLines in clockwiseLineData.items():
                        for counterP, counterLines in counterLineData.items():
                            for clockwiseSA, clockwiseSB in clockwiseLines:
                                for counterSA, counterSB in counterLines:
                                    overlap = _linesOverlap(clockwiseSA, clockwiseSB, counterSA, counterSB)
                                    if not overlap:
                                        continue
                                    w = abs(counterP - clockwiseP)
                                    hits = []
                                    for stem in targetStems:
                                        if w == stem:
                                            d = stem.diff(w)
                                            if d:
                                                hits.append((d, stem.value, (clockwiseSA, clockwiseSB, counterSA, counterSB)))
                                    if hits:
                                        p = min((clockwiseP, counterP))
                                        hit = min(hits)
                                        w = hit[1]
                                        s = hit[2]
                                        stems.add((p, p + w, s))
    # done
    return stems


class _StemWrapper(object):

    def __init__(self, value, threshold):
        self.value = value
        self.threshold = threshold

    def __cmp__(self, other):
        d = abs(self.value - other)
        if d <= self.threshold:
            return 0
        return cmp(self.value, other)

    def diff(self, other):
        return abs(self.value - other)


def _linesOverlap(a1, a2, b1, b2):
    if a1 > b2 or a2 < b1:
        return False
    return True


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
    _drawSideBearingsReport(data, scale, y, defaults.colorReview)

def _drawSideBearingsReport(data, scale, textPosition, color):
    left = data["left"]
    right = data["right"]
    width = data["width"]
    leftMessage = data["leftMessage"]
    rightMessage = data["rightMessage"]
    xMin, yMin, xMax, yMax = data["box"]
    h = (yMax - yMin) / 2.0
    y = textPosition
    color = defaults.colorReview
    color.set()
    if leftMessage:
        path = drawLine((0, y), (left, y), scale=scale, arrowStart=True)
        path.setLineWidth_(generalLineWidth * scale)
        path.stroke()
        if defaults.showTitles:
            x = min((0, left)) - (5 * scale)
            drawString((x, y), leftMessage, scale, color, hAlignment="right")
    if rightMessage:
        path = drawLine((right, y), (width, y), scale=scale, arrowEnd=True)
        path.setLineWidth_(generalLineWidth * scale)
        path.stroke()
        if defaults.showTitles:
            x = max((width, right)) - (5 * scale)
            drawString((x, y), rightMessage, scale, color, hAlignment="left")

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
    boxes = [c.box for c in components]
    # a component has no contours
    if None in boxes:
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
    _drawSideBearingsReport(data, scale, y, defaults.colorReview)

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
    color = defaults.colorReview
    left = data["left"]
    right = data["right"]
    width = data["width"]
    message = data["message"]
    y = -20
    x = left + (((width - right) - left) / 2.0)
    color.set()
    path = drawLine((min((0, left)), y), (max((width, width - right)), y), scale=scale, arrowStart=True, arrowEnd=True)
    path.setLineWidth_(generalLineWidth * scale)
    path.stroke()
    if defaults.showTitles:
        drawString((x, y), message, scale, color, backgroundColor=NSColor.whiteColor())

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
    color = defaults.colorRemove
    color.set()
    for contourIndex in contours:
        pen = CocoaPen(None)
        contour = glyph[contourIndex]
        contour.draw(pen)
        path = pen.path
        path.setLineWidth_(highlightLineWidth * scale)
        path.stroke()
        if defaults.showTitles:
            xMin, yMin, xMax, yMax = contour.box
            mid = calcMid((xMin, yMin), (xMax, yMin))
            x, y = mid
            drawString((x, y), "Duplicate Contour", scale, color, vAlignment="top", vOffset="-y")

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
    color = defaults.colorRemove
    color.set()
    for contourIndex, box in contours.items():
        pen = CocoaPen(None)
        contour = glyph[contourIndex]
        contour.draw(pen)
        path = pen.path
        path.setLineWidth_(highlightLineWidth * scale)
        path.stroke()
        if defaults.showTitles:
            xMin, yMin, xMax, yMax = box
            w = xMax - xMin
            x = xMin + (w / 2)
            y = yMin
            drawString((x, y), "Tiny Contour", scale, color, vAlignment="top", vOffset="-y")

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
    color = defaults.colorInsert
    color.set()
    for contourIndex, points in contours.items():
        start, end = points
        path = drawLine(start, end, scale=scale, arrowStart=True)
        path.setLineWidth_(generalLineWidth * scale)
        path.stroke()
        if defaults.showTitles:
            mid = calcMid(start, end)
            drawString(mid, "Open Contour", scale, color, backgroundColor=NSColor.whiteColor())

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
    color = defaults.colorInsert
    path = NSBezierPath.bezierPath()
    d = 16 * scale
    h = d / 2.0
    o = 3 * scale
    for contourIndex, points in contours.items():
        for (x, y) in points:
            drawAddMark((x, y), scale, path=path)
            if defaults.showTitles:
                drawString((x, y), "Insert Point", scale, color, vAlignment="top", vOffset="-y")
    color.set()
    path.setLineWidth_(generalLineWidth * scale)
    path.stroke()

registerTest(
    identifier="extremePoints",
    level="contour",
    title="Extreme Points",
    description="One or more curves need an extreme point.",
    testFunction=testForExtremePoints,
    drawingFunction=drawExtremePoints
)

# Symmetrical Curves

def testForSlightlyAssymmetricCurves(glyph):
    """
    Note adjacent curves that are almost symmetrical.
    """
    slightlyAsymmetricalCurves = []
    for contour in glyph:
        # gather pairs of curves that could potentially be related
        curvePairs = []
        for index, segment in enumerate(contour):
            # curve + h/v line + curve
            if segment.type == "line":
                prev = index - 1
                next = index + 1
                if next == len(contour):
                    next = 0
                prevSegment = contour[prev]
                nextSegment = contour[next]
                if prevSegment.type == "curve" and nextSegment.type == "curve":
                    px = prevSegment[-1].x
                    py = prevSegment[-1].y
                    x = segment[-1].x
                    y = segment[-1].y
                    if px == x or py == y:
                        prevPrevSegment = contour[prev - 1]
                        c1 = (
                            (prevPrevSegment[-1].x, prevPrevSegment[-1].y),
                            (prevSegment[0].x, prevSegment[0].y),
                            (prevSegment[1].x, prevSegment[1].y),
                            (prevSegment[2].x, prevSegment[2].y)
                        )
                        c2 = (
                            (segment[-1].x, segment[-1].y),
                            (nextSegment[0].x, nextSegment[0].y),
                            (nextSegment[1].x, nextSegment[1].y),
                            (nextSegment[2].x, nextSegment[2].y)
                        )
                        curvePairs.append((c1, c2))
                        curvePairs.append((c2, c1))
            # curve + curve
            elif segment.type == "curve":
                prev = index - 1
                prevSegment = contour[prev]
                if prevSegment.type == "curve":
                    prevPrevSegment = contour[prev - 1]
                    c1 = (
                        (prevPrevSegment[-1].x, prevPrevSegment[-1].y),
                        (prevSegment[0].x, prevSegment[0].y),
                        (prevSegment[1].x, prevSegment[1].y),
                        (prevSegment[2].x, prevSegment[2].y)
                    )
                    c2 = (
                        (prevSegment[2].x, prevSegment[2].y),
                        (segment[0].x, segment[0].y),
                        (segment[1].x, segment[1].y),
                        (segment[2].x, segment[2].y)
                    )
                    curvePairs.append((c1, c2))
                    curvePairs.append((c2, c1))
        # relativize the pairs and compare
        for curve1, curve2 in curvePairs:
            curve1Compare = _relativizeCurve(curve1)
            curve2Compare = _relativizeCurve(curve2)
            if curve1 is None or curve2 is None:
                continue
            if curve1Compare is None or curve2Compare is None:
                continue
            flipped = curve1Compare.getFlip(curve2Compare)
            if flipped:
                slightlyAsymmetricalCurves.append((flipped, curve2))
    # done
    if not slightlyAsymmetricalCurves:
        return None
    return slightlyAsymmetricalCurves

def drawSlightlyAsymmetricCurves(data, scale, glyph):
    arrowPath = NSBezierPath.bezierPath()
    curvePath = NSBezierPath.bezierPath()
    for toCurve, fromCurve in data:
        to3, to2, to1, to0 = toCurve
        from0, from1, from2, from3 = fromCurve
        if to0 != from0:
            drawLine(from0, to0, scale=scale, path=arrowPath, arrowEnd=True)
        if to1 != from1:
            drawLine(from1, to1, scale=scale, path=arrowPath, arrowEnd=True)
        if to2 != from2:
            drawLine(from2, to2, scale=scale, path=arrowPath, arrowEnd=True)
        if to3 != from3:
            drawLine(from3, to3, scale=scale, path=arrowPath, arrowEnd=True)
        curvePath.moveToPoint_(to3)
        curvePath.curveToPoint_controlPoint1_controlPoint2_(to0, to2, to1)
    color = defaults.colorReview
    color.set()
    arrowPath.setLineWidth_(generalLineWidth * scale)
    arrowPath.stroke()
    curvePath.setLineWidth_(highlightLineWidth * scale)
    curvePath.stroke()

registerTest(
    identifier="curveSymmetry",
    level="contour",
    title="Curve Symmetry",
    description="One or more curve pairs are slightly asymmetrical.",
    testFunction=testForSlightlyAssymmetricCurves,
    drawingFunction=drawSlightlyAsymmetricCurves
)

def _relativizeCurve(curve):
    pt0, pt1, pt2, pt3 = curve
    # bcps aren't horizontal or vertical
    if (pt0[0] != pt1[0]) and (pt0[1] != pt1[1]):
        return None
    if (pt3[0] != pt2[0]) and (pt3[1] != pt2[1]):
        return None
    # xxx validate that the bcps aren't backwards here
    w = abs(pt3[0] - pt0[0])
    h = abs(pt3[1] - pt0[1])
    bw = None
    bh = None
    # pt0 -> pt1 is vertical
    if pt0[0] == pt1[0]:
        bh = abs(pt1[1] - pt0[1])
    # pt0 -> pt1 is horizontal
    elif pt0[1] == pt1[1]:
        bw = abs(pt1[0] - pt0[0])
    # pt2 -> pt3 is vertical
    if pt2[0] == pt3[0]:
        bh = abs(pt3[1] - pt2[1])
    # pt2 -> pt3 is horizontal
    elif pt2[1] == pt3[1]:
        bw = abs(pt3[0] - pt2[0])
    # safety
    if bw is None or bh is None:
        return None
    # done
    curve = _CurveFlipper((w, h, bw, bh), curve, 5, 10)
    return curve


class _CurveFlipper(object):

    def __init__(self, relativeCurve, curve, sizeThreshold, bcpThreshold):
        self.w, self.h, self.bcpw, self.bcph = relativeCurve
        self.pt0, self.pt1, self.pt2, self.pt3 = curve
        self.sizeThreshold = sizeThreshold
        self.bcpThreshold = bcpThreshold

    def getFlip(self, other):
        ## determine if they need a flip
        # curves are exactly the same
        if (self.w, self.h, self.bcpw, self.bcph) == (other.w, other.h, other.bcpw, other.bcph):
            return None
        # width/height are too different
        if abs(self.w - other.w) > self.sizeThreshold:
            return None
        if abs(self.h - other.h) > self.sizeThreshold:
            return None
        # bcp deltas are too different
        if abs(self.bcpw - other.bcpw) > self.bcpThreshold:
            return None
        if abs(self.bcph - other.bcph) > self.bcpThreshold:
            return None
        # determine the flip direction
        minX = min((self.pt0[0], self.pt3[0]))
        otherMinX = min((other.pt0[0], other.pt3[0]))
        minY = min((self.pt0[1], self.pt3[1]))
        otherMinY = min((other.pt0[1], other.pt3[1]))
        direction = None
        if abs(minX - otherMinX) <= self.sizeThreshold:
            direction = "v"
        elif abs(minY - otherMinY) <= self.sizeThreshold:
            direction = "h"
        if direction is None:
            return None
        # flip
        if direction == "h":
            transformation = (-1, 0, 0, 1, 0, 0)
        else:
            transformation = (1, 0, 0, -1, 0, 0)
        self._transformedPoints = []
        transformPen = TransformPen(self, transformation)
        transformPen.moveTo(self.pt0)
        transformPen.curveTo(self.pt1, self.pt2, self.pt3)
        points = self._transformedPoints
        del self._transformedPoints
        # offset
        oX = oY = 0
        if direction == "v":
            oY = points[-1][1] - other.pt0[1]
        else:
            oX = points[-1][0] - other.pt0[0]
        offset = []
        for x, y in points:
            x -= oX
            y -= oY
            offset.append((x, y))
        points = offset
        # done
        return points

    def moveTo(self, pt):
        self._transformedPoints.append(pt)

    def curveTo(self, pt1, pt2, pt3):
        self._transformedPoints.append(pt1)
        self._transformedPoints.append(pt2)
        self._transformedPoints.append(pt3)


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
                if x > 0 and x <= 5 and prev[1] != point[1]:
                    if index not in straightLines:
                        straightLines[index] = set()
                    straightLines[index].add((prev, point))
                if y > 0 and y <= 5 and prev[0] != point[0]:
                    if index not in straightLines:
                        straightLines[index] = set()
                    straightLines[index].add((prev, point))
            prev = point
    return straightLines

def drawStraightLines(contours, scale, glyph):
    color = defaults.colorReview
    color.set()
    for contourIndex, segments in contours.items():
        for pt1, pt2 in segments:
            path = drawLine(pt1, pt2, scale=scale)
            path.setLineWidth_(highlightLineWidth * scale)
            path.stroke()
            if defaults.showTitles:
                mid = calcMid(pt1, pt2)
                drawString(mid, "Angled Line", scale, color, backgroundColor=NSColor.whiteColor())

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
    Points shouldn't be just off a vertical metric or blue zone.
    """
    threshold = 5
    # gather the blues into top and bottom groups
    font = glyph.getParent()
    topZones = _makeZonePairs(font.info.postscriptBlueValues)
    bottomZones = _makeZonePairs(font.info.postscriptOtherBlues)
    if topZones:
        t = topZones[0]
        if t[0] <= 0 and t[1] == 0:
            bottomZones.append(topZones.pop(0))
    # insert vertical metrics into the zones
    topMetrics = [getattr(font.info, attr) for attr in "xHeight capHeight ascender".split(" ") if getattr(font.info, attr) is not None]
    bottomMetrics = [getattr(font.info, attr) for attr in "descender".split(" ") if getattr(font.info, attr) is not None] + [0]
    for value in topMetrics:
        found = False
        for b, t in topZones:
            if b <= value and t >= value:
                found = True
                break
        if not found:
            topZones.append((value, value))
    for value in bottomMetrics:
        found = False
        for b, t in bottomZones:
            if b <= value and t >= value:
                found = True
                break
        if not found:
            bottomZones.append((value, value))
    # find points
    found = {}
    for contour in glyph:
        if len(contour) < 3:
            continue
        for segmentIndex, segment in enumerate(contour):
            prev = segmentIndex - 1
            next = segmentIndex + 1
            if next == len(contour):
                next = 0
            prevSegment = contour[prev]
            nextSegment = contour[next]
            pt = (segment.onCurve.x, segment.onCurve.y)
            prevPt = (prevSegment.onCurve.x, prevSegment.onCurve.y)
            nextPt = (nextSegment.onCurve.x, nextSegment.onCurve.y)
            pY = prevPt[1]
            x, y = pt
            nY = nextPt[1]
            # top point
            if y >= pY and y >= nY:
                for b, t in topZones:
                    test = None
                    # point is above zone
                    if y > t and abs(t - y) <= threshold:
                        test = t
                    # point is below zone
                    elif y < b and abs(b - y) <= threshold:
                        test = b
                    if test is not None:
                        if glyph.pointInside((x, y - 1)):
                            if test not in found:
                                found[test] = set()
                            found[test].add((x, y))
            # bottom point
            if y <= pY and y <= nY:
                for b, t in bottomZones:
                    test = None
                    # point is above zone
                    if y > t and abs(t - y) <= threshold:
                        test = t
                    # point is below zone
                    elif y < b and abs(b - y) <= threshold:
                        test = b
                    if test is not None:
                        if glyph.pointInside((x, y + 1)):
                            if test not in found:
                                found[test] = set()
                            found[test].add((x, y))
    return found

def _makeZonePairs(blues):
    blues = list(blues)
    pairs = []
    if not len(blues) % 2:
        while blues:
            bottom = blues.pop(0)
            top = blues.pop(0)
            pairs.append((bottom, top))
    return pairs

def drawSegmentsNearVericalMetrics(verticalMetrics, scale, glyph):
    color = defaults.colorReview
    path = NSBezierPath.bezierPath()
    for verticalMetric, points in verticalMetrics.items():
        for (x, y) in points:
            drawLine((x, y), (x, verticalMetric), scale=scale, path=path, arrowEnd=True)
    color.set()
    path.setLineWidth_(generalLineWidth * scale)
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
    color = defaults.colorReview
    color.set()
    for contourIndex, points in contours.items():
        path = NSBezierPath.bezierPath()
        for pt1, pt2, pt3 in points:
            path.moveToPoint_(pt1)
            path.lineToPoint_(pt3)
            path.setLineWidth_(highlightLineWidth * scale)
            path.stroke()
            if defaults.showTitles:
                x, y = pt2
                drawString((x, y), "Unsmooth Smooth", scale, color, backgroundColor=NSColor.whiteColor())

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
    color = defaults.colorReview
    color.set()
    for contourIndex, segments in contours.items():
        for segment in segments:
            pt0, pt1, pt2, pt3 = segment
            path = NSBezierPath.bezierPath()
            path.moveToPoint_(pt0)
            path.curveToPoint_controlPoint1_controlPoint2_(pt3, pt1, pt2)
            path.setLineWidth_(highlightLineWidth * scale)
            path.setLineCapStyle_(NSRoundLineCapStyle)
            path.stroke()
            if defaults.showTitles:
                mid = ftBezierTools.splitCubicAtT(pt0, pt1, pt2, pt3, 0.5)[0][-1]
                drawString(mid, "Complex Curve", scale, color, backgroundColor=NSColor.whiteColor())

registerTest(
    identifier="complexCurves",
    level="segment",
    title="Complex Curves",
    description="One or more curves is suspiciously complex.",
    testFunction=testForComplexCurves,
    drawingFunction=drawComplexCurves
)

# Crossed Handles

def _crossedHanldeWithNoOtherOptions(hit, pt0, pt1, pt2, pt3):
    hitWidth = max((abs(hit[0] - pt0[0]), abs(hit[0] - pt3[0])))
    hitHeight = max((abs(hit[1] - pt0[1]), abs(hit[1] - pt3[1])))
    w = abs(pt0[0] - pt3[0])
    h = abs(pt0[1] - pt3[1])
    bw = max((abs(pt0[0] - pt1[0]), abs(pt3[0] - pt2[0])))
    bh = max((abs(pt0[1] - pt1[1]), abs(pt3[1] - pt2[1])))
    if w == 1 and bw == 1 and not bh > h:
        return True
    elif h == 1 and bh == 1 and not bw > w:
        return True
    return False

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
                    if _crossedHanldeWithNoOtherOptions(direct, pt0, pt1, pt2, pt3):
                        pass
                    else:
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
                            if _crossedHanldeWithNoOtherOptions(indirect, pt0, pt1, pt2, pt3):
                                pass
                            else:
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
                            if _crossedHanldeWithNoOtherOptions(indirect, pt0, pt1, pt2, pt3):
                                pass
                            else:
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
    color = defaults.colorReview
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
            path1.setLineWidth_(highlightLineWidth * scale)
            path1.setLineCapStyle_(NSRoundLineCapStyle)
            path1.stroke()
            path2.fill()
            if defaults.showTitles:
                drawString((x, y), "Crossed Handles", scale, color, vAlignment="top", vOffset="-y", backgroundColor=NSColor.whiteColor())

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
    color = defaults.colorRemove
    color.set()
    d = 10 * scale
    h = d / 2.0
    for contourIndex, points in contours.items():
        for bcp1, bcp2 in points:
            path = NSBezierPath.bezierPath()
            drawDeleteMark(bcp1, scale, path=path)
            drawDeleteMark(bcp2, scale, path=path)
            path.setLineWidth_(generalLineWidth * scale)
            path.stroke()
            path = NSBezierPath.bezierPath()
            path.moveToPoint_(bcp1)
            path.lineToPoint_(bcp2)
            path.setLineWidth_(highlightLineWidth * scale)
            path.stroke()
            if defaults.showTitles:
                mid = calcMid(bcp1, bcp2)
                drawString(mid, "Unnecessary Handles", scale, color, backgroundColor=NSColor.whiteColor())

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
                # create rays perpendicular to the
                # angle between the on and off
                # through the on
                on1 = _unwrapPoint(prevPoint)
                off1, off2 = [_unwrapPoint(pt) for pt in segment.offCurve]
                on2 = _unwrapPoint(segment.onCurve)
                curve = (on1, off1, off2, on2)
                off1Angle = _calcAngle(on1, off1) - 90
                on1Ray = _createLineThroughPoint(on1, off1Angle)
                off2Angle = _calcAngle(off2, on2) - 90
                on2Ray = _createLineThroughPoint(on2, off2Angle)
                # find the intersection of the rays
                rayIntersection = _intersectLines(on1Ray, on2Ray)
                if rayIntersection is not None:
                    # draw a line between the off curves and the intersection
                    # and find out where these lines intersect the curve
                    off1Intersection = _getLineCurveIntersection((off1, rayIntersection), curve)
                    off2Intersection = _getLineCurveIntersection((off2, rayIntersection), curve)
                    if off1Intersection is not None and off2Intersection is not None:
                        if off1Intersection.points and off2Intersection.points:
                            off1IntersectionPoint = (off1Intersection.points[0].x, off1Intersection.points[0].y)
                            off2IntersectionPoint = (off2Intersection.points[0].x, off2Intersection.points[0].y)
                            # assemble the off curves and their intersections into lines
                            off1Line = (off1, off1IntersectionPoint)
                            off2Line = (off2, off2IntersectionPoint)
                            # measure and compare these
                            # if they are not both very short calculate the ratio
                            length1, length2 = sorted((_getLineLength(*off1Line), _getLineLength(*off2Line)))
                            if length1 >= 3 and length2 >= 3:
                                ratio = length2 / float(length1)
                                # if outside acceptable range, flag
                                if ratio > 1.5:
                                    off1Shape = _getUnevenHandleShape(on1, off1, off2, on2, off1Intersection, on1, off1IntersectionPoint, off1)
                                    off2Shape = _getUnevenHandleShape(on1, off1, off2, on2, off2Intersection, off2IntersectionPoint, on2, off2)
                                    if index not in unevenHandles:
                                        unevenHandles[index] = []
                                    unevenHandles[index].append((off1, off2, off1Shape, off2Shape))
            prevPoint = segment.onCurve
    return unevenHandles

def _getUnevenHandleShape(pt0, pt1, pt2, pt3, intersection, start, end, off):
    splitSegments = ftBezierTools.splitCubicAtT(pt0, pt1, pt2, pt3, *intersection.t)
    curves = []
    for segment in splitSegments:
        if _roundPoint(segment[0]) != _roundPoint(start) and not curves:
            continue
        curves.append(segment[1:])
        if _roundPoint(segment[-1]) == _roundPoint(end):
            break
    return curves + [off, start]

def drawUnevenHandles(contours, scale, glyph):
    textColor = defaults.colorReview
    fillColor = modifyColorAlpha(textColor, 0.15)
    for index, groups in contours.items():
        for off1, off2, shape1, shape2 in groups:
            fillColor.set()
            path = NSBezierPath.bezierPath()
            for shape in (shape1, shape2):
                path.moveToPoint_(shape[-1])
                for curve in shape[:-2]:
                    pt1, pt2, pt3 = curve
                    path.curveToPoint_controlPoint1_controlPoint2_(pt3, pt1, pt2)
                path.lineToPoint_(shape[-2])
                path.lineToPoint_(shape[-1])
            path.fill()
            if defaults.showTitles:
                mid = calcMid(off1, off2)
                drawString(mid, "Uneven Handles", scale, textColor, backgroundColor=NSColor.whiteColor())

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
    for index, anchor in enumerate(glyph.anchors):
        if anchor.name == "":
            pt = (anchor.x, anchor.y)
            strayPoints[index+1+len(strayPoints)] = pt
    return strayPoints

def drawStrayPoints(contours, scale, glyph):
    color = defaults.colorRemove
    path = NSBezierPath.bezierPath()
    for contourIndex, (x, y) in contours.items():
        drawDeleteMark((x, y), scale, path=path)
        if defaults.showTitles:
            drawString((x, y), "Stray Point", scale, color, vAlignment="top", vOffset="-y")
    color.set()
    path.setLineWidth_(generalLineWidth * scale)
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
    color = defaults.colorRemove
    path = NSBezierPath.bezierPath()
    for contourIndex, points in contours.items():
        for pt in points:
            drawDeleteMark(pt, scale, path)
            if defaults.showTitles:
                x, y = pt
                drawString((x, y), "Unnecessary Point", scale, color, vAlignment="top", vOffset="-y")
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
    color = defaults.colorRemove
    path = NSBezierPath.bezierPath()
    for contourIndex, points in contours.items():
        for (x, y) in points:
            drawDeleteMark((x, y), scale, path)
            if defaults.showTitles:
                drawString((x, y), "Overlapping Points", scale, color, vAlignment="top", vOffset="-y")
    color.set()
    path.setLineWidth_(generalLineWidth * scale)
    path.stroke()

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

def _roundPoint(pt):
    return round(pt[0]), round(pt[1])

def _intersectLines((a1, a2), (b1, b2)):
    # adapted from: http://www.kevlindev.com/gui/math/intersection/Intersection.js
    ua_t = (b2[0] - b1[0]) * (a1[1] - b1[1]) - (b2[1] - b1[1]) * (a1[0] - b1[0])
    ub_t = (a2[0] - a1[0]) * (a1[1] - b1[1]) - (a2[1] - a1[1]) * (a1[0] - b1[0])
    u_b  = (b2[1] - b1[1]) * (a2[0] - a1[0]) - (b2[0] - b1[0]) * (a2[1] - a1[1])
    if u_b != 0:
        ua = ua_t / float(u_b)
        ub = ub_t / float(u_b)
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
    return round(b, 5)

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

def _getLineCurveIntersection(line, curve):
    points = curve + line
    intersection = rfBezierTools.intersectCubicLine(*points)
    return intersection

# -----------------
# Drawing Utilities
# -----------------

def modifyColorAlpha(color, a):
    r = color.redComponent()
    g = color.greenComponent()
    b = color.blueComponent()
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)

def drawLine(pt1, pt2, scale, arrowStart=False, arrowEnd=False, arrowLenght=16, arrowAngle=36, path=None):
    if path is None:
        path = NSBezierPath.bezierPath()
    path.moveToPoint_(pt1)
    path.lineToPoint_(pt2)
    if arrowStart or arrowEnd:
        x1, y1 = pt1
        x2, y2 = pt2
        angle = math.atan2(y2-y1, x2-x1)
        headLength = arrowLenght * scale
        headAngle = math.radians(arrowAngle)
        if arrowStart:
            h1 = (
                x1 + headLength * math.cos(angle - headAngle),
                y1 + headLength * math.sin(angle - headAngle)
            )
            h2 = (
                x1 + headLength * math.cos(angle + headAngle),
                y1 + headLength * math.sin(angle + headAngle)
            )
            path.moveToPoint_(h1)
            path.lineToPoint_(pt1)
            path.lineToPoint_(h2)
        if arrowEnd:
            h1 = (
                x2 - headLength * math.cos(angle - headAngle),
                y2 - headLength * math.sin(angle - headAngle)
            )
            h2 = (
                x2 - headLength * math.cos(angle + headAngle),
                y2 - headLength * math.sin(angle + headAngle)
            )
            path.moveToPoint_(h1)
            path.lineToPoint_(pt2)
            path.lineToPoint_(h2)
    return path

def drawCircles(points, size, scale, path=None):
    if path is None:
        path = NSBezierPath.bezierPath()
    size *= scale
    h = size / 2
    for (x, y) in points:
        rect = ((x - h, y - h), (size, size))
        path.appendBezierPathWithOvalInRect_(rect)
    return path

def drawAddMark(pt, scale, path=None):
    if path is None:
        path = NSBezierPath.bezierPath()
    h = 8 * scale
    x, y = pt
    path.moveToPoint_((x - h , y))
    path.lineToPoint_((x + h, y))
    path.moveToPoint_((x, y - h))
    path.lineToPoint_((x, y + h))
    return path

def drawDeleteMark(pt, scale, path=None):
    if path is None:
        path = NSBezierPath.bezierPath()
    h = 8 * scale
    x, y = pt
    x1 = x - h
    x2 = x + h
    y1 = y - h
    y2 = y + h
    path.moveToPoint_((x1, y1))
    path.lineToPoint_((x2, y2))
    path.moveToPoint_((x1, y2))
    path.lineToPoint_((x2, y1))
    return path

def drawString(pt, text, scale, color, hAlignment="center", vAlignment="center", vOffset=None, backgroundColor=None):
    attributes = attributes = {
        NSFontAttributeName : NSFont.fontWithName_size_("Lucida Grande", textSize * scale),
        NSForegroundColorAttributeName : color
    }
    if backgroundColor is not None:
        text = " " + text + " "
        attributes[NSBackgroundColorAttributeName] = backgroundColor
    text = NSAttributedString.alloc().initWithString_attributes_(text, attributes)
    x, y = pt
    width, height = text.size()
    if hAlignment == "center":
        x -= width / 2.0
    elif hAlignment == "right":
        x -= width
    if vAlignment == "center":
        y -= height / 2.0
    elif vAlignment == "top":
        y -= height
    if vOffset == "y":
        y += textVerticalOffset * scale
    elif vOffset == "-y":
        y -= textVerticalOffset * scale
    text.drawAtPoint_((x, y))

def calcMid(pt1, pt2):
    x1, y1 = pt1
    x2, y2 = pt2
    x = x1 - ((x1 - x2) / 2)
    y = y1 - ((y1 - y2) / 2)
    return x, y

def calcCenter(v1, v2, v3, v4):
    a = b = None
    if v1 > v3:
        a = v1
    else:
        a = v3
    if v2 < v4:
        b = v2
    else:
        b = v4
    c = a + ((b - a) / 2)
    return c


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
