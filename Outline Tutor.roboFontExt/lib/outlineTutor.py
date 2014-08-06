"""
Font
----
X duplicate unicode

Glyph
-----
X points at extreme
X unnecessary points
X contours overlapping in bad ways / too many contours
X open paths
X stray points
X unnecessay handles
- lines that are just off vertical or horizontal
X implied s curve
- crossed handles
- overlapping points on the same contour

- the colors need to vary and perhaps the interface
  needs some sort or color indication. or, more text
  needs to be drawn.
- finish the interface and incorporate it into the observer
- use a representation factory for the report
"""

import math
from AppKit import *
import vanilla
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.events import addObserver, removeObserver
from mojo import drawingTools

# ------
# Colors
# ------

missingExtremaColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0, 0, 0.5)
openContourColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0, 0, 0.5)
strayPointColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0, 0, 0.5)
smallContourColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0, 0, 0.5)
textReportColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0, 0, 0.5)
impliedSCurveColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0, 0, 0.5)
unnecessaryPointsColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0, 0, 0.5)
unnecessaryHandlesColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0, 0, 0.5)

# -------
# Palette
# -------

class OutlineTutorControls(BaseWindowController):

    def __init__(self):
        self.w = vanilla.FloatingWindow((170, 300))

        t = 10
        self.w.glyphAttributesTitle = vanilla.TextBox((10, t, -10, 14), "Glyph Attributes", sizeStyle="small")
        self.w.glyphAttributesLine = vanilla.HorizontalLine((10, t + 18, -10, 1))
        t += 24
        self.w.duplicateUnicodeCheckBox = vanilla.CheckBox((10, t, -10, 18), "Duplicate Unicode Value", value=True, sizeStyle="small")
        t += 20

        self.setUpBaseWindowBehavior()
        self.startObserver()
        self.w.open()

    def windowCloseCallback(self, sender):
        self.stopObserver()

    def startObserver(self):
        self.observer = OutlineTutorObserver()
        addObserver(self.observer, "drawComments", "draw")

    def stopObserver(self):
        removeObserver(self.observer, "draw")
        self.observer = None


# ----------------
# Drawing Observer
# ----------------

class OutlineTutorObserver(object):

    def drawComments(self, info):
        glyph = info["glyph"]
        font = glyph.getParent()
        scale = info["scale"]
        report = getGlyphReport(font, glyph)
        # small contours
        d = report.get("tooSmallContours")
        if d:
            self.drawSmallContours(d, scale)
        # open contours
        d = report.get("openContours")
        if d:
            self.drawOpenContours(d, scale)
        # missing extremes
        d = report.get("needPointsAtExtrema")
        if d:
            self.drawMissingExtrema(d, scale)
        # stray points
        d = report.get("strayPoints")
        if d:
            self.drawStrayPoints(d, scale)
        # implied S curves
        d = report.get("impliedSCurves")
        if d:
            self.drawImpliedSCurves(d, scale)
        # unnecessary points
        d = report.get("unnecessaryPoints")
        if d:
            self.drawUnnecessaryPoints(d, scale)
        # unnecessary handles
        d = report.get("unnecessaryHandles")
        if d:
            self.drawUnnecessaryHandles(d, scale)
        # text report
        self.drawTextReport(report, scale)

    def drawSmallContours(self, contours, scale):
        smallContourColor.set()
        for contourIndex, box in contours.items():
            xMin, yMin, xMax, yMax = box
            w = xMax - xMin
            h = yMax - yMin
            r = ((xMin, yMin), (w, h))
            NSRectFillUsingOperation(r, NSCompositeSourceOver)
            x = xMin + (w / 2)
            y = yMin - (10 * scale)
            drawString((x, y), "Tiny Contour", 10, scale, smallContourColor)

    def drawOpenContours(self, contours, scale):
        for contourIndex, points in contours.items():
            start, end = points
            mid = calcMid(start, end)
            drawString(mid, "Open Contour", 10, scale, openContourColor)

    def drawMissingExtrema(self, contours, scale):
        path = NSBezierPath.bezierPath()
        d = 10 * scale
        h = d / 2.0
        for contourIndex, points in contours.items():
            for (x, y) in points:
                r = ((x - h, y - h), (d, d))
                path.appendBezierPathWithOvalInRect_(r)
        missingExtremaColor.set()
        path.fill()

    def drawStrayPoints(self, contours, scale):
        path = NSBezierPath.bezierPath()
        for contourIndex, pt in contours.items():
            drawDeleteMark(pt, scale, path)
        strayPointColor.set()
        path.setLineWidth_(scale)
        path.stroke()

    def drawImpliedSCurves(self, contours, scale):
        path = NSBezierPath.bezierPath()
        for contourIndex, segments in contours.items():
            for segment in segments:
                pt0, pt1, pt2, pt3 = segment
                path.moveToPoint_(pt0)
                path.curveToPoint_controlPoint1_controlPoint2_(pt3, pt1, pt2)
        impliedSCurveColor.set()
        path.setLineWidth_(3 * scale)
        path.stroke()

    def drawUnnecessaryPoints(self, contours, scale):
        path = NSBezierPath.bezierPath()
        for contourIndex, points in contours.items():
            for pt in points:
                drawDeleteMark(pt, scale, path)
        unnecessaryPointsColor.set()
        path.setLineWidth_(scale)
        path.stroke()

    def drawUnnecessaryHandles(self, contours, scale):
        path1 = NSBezierPath.bezierPath()
        path2 = NSBezierPath.bezierPath()
        for contourIndex, points in contours.items():
            for bcp, anchor in points:
                drawDeleteMark(bcp, scale, path1)
                path2.moveToPoint_(bcp)
                path2.lineToPoint_(anchor)
        unnecessaryHandlesColor.set()
        path1.setLineWidth_(scale)
        path1.stroke()
        path2.setLineWidth_(3 * scale)
        path2.stroke()

    def drawTextReport(self, report, scale):
        text = []
        d = report.get("duplicateUnicode")
        if d:
            text.append("The Unicode for this glyph is also used by: %s." % " ".join(d))
        d = report.get("tooManyOverlappingContours")
        if d:
            text.append("This glyph has a unusally high number of overlapping contours.")
        text = "\n".join(text)
        x = 0
        y = 0
        drawString((x, y), text, 16, scale, textReportColor, alignment="left")

# Utilities

def drawDeleteMark(pt, scale, path):
    h = 10 * scale
    x, y = pt
    x1 = x - h
    x2 = x + h
    y1 = y - h
    y2 = y + h
    path.moveToPoint_((x1, y1))
    path.lineToPoint_((x2, y2))
    path.moveToPoint_((x1, y2))
    path.lineToPoint_((x2, y1))

def drawString(pt, text, size, scale, color, alignment="center"):
    attributes = attributes = {
        NSFontAttributeName : NSFont.fontWithName_size_("Lucida Grande", size * scale),
        NSForegroundColorAttributeName : color
    }
    text = NSAttributedString.alloc().initWithString_attributes_(text, attributes)
    x, y = pt
    if alignment == "center":
        width, height = text.size()
        x -= width / 2.0
        y -= height / 2.0
    text.drawAtPoint_((x, y))

def calcMid(pt1, pt2):
    x1, y1 = pt1
    x2, y2 = pt2
    x = x1 - ((x1 - x2) / 2)
    y = y1 - ((y1 - y2) / 2)
    return x, y

# --------
# Reporter
# --------

def getGlyphReport(font, glyph):
    report = dict(
        duplicateUnicode=testForDuplicateUnicode(glyph),
        tooManyOverlappingContours=testOverlappingContours(glyph),
        tooSmallContours=testForSmallContours(glyph),
        openContours=testForOpenContours(glyph),
        needPointsAtExtrema=testForPointsAtExtrema(glyph),
        unnecessaryPoints=testForUnnecessaryPoints(glyph),
        unnecessaryHandles=testForUnnecessaryHandles(glyph),
        impliedSCurves=testForImpliedSCurve(glyph),
        strayPoints=testForStrayPoints(glyph)
    )
    return report

# Glyph Data

def testForDuplicateUnicode(glyph):
    """
    A Unicode value should appear only once per font.
    """
    font = glyph.getParent()
    uni = glyph.unicode
    if uni is None:
        return None
    duplicates = []
    for name in sorted(font.keys()):
        if name == glyph.name:
            continue
        other = font[name]
        if other.unicode == uni:
            duplicates.append(name)
    return duplicates

# Glyph Construction

def testOverlappingContours(glyph):
    """
    There shouldn't be too many overlapping contours.
    """
    count = len(glyph)
    test = glyph.copy()
    test.removeOverlap()
    if count - len(test) > 2:
        return True
    return False

# Contours

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

def testForPointsAtExtrema(glyph):
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

def testForImpliedSCurve(glyph):
    """
    Implied S curves are suspicious.
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
                if index not in impliedS:
                    impliedS[index] = []
                if _intersectLines(line1, line2):
                    impliedS[index].append((prev, pt1, pt2, pt3))
            prev = _unwrapPoint(segment.onCurve)
    return impliedS

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

# Segments

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
                bcp1 = bcp2 = False
                if bcpAngle1 == lineAngle:
                    bcp1 = True
                if bcpAngle2 == lineAngle:
                    bcp2 = True
                if bcp1 and bcp2:
                    if index not in unnecessaryHandles:
                        unnecessaryHandles[index] = []
                    if bcp1:
                        unnecessaryHandles[index].append(((pt1.x, pt1.y), (pt0.x, pt0.y)))
                    if bcp2:
                        unnecessaryHandles[index].append(((pt2.x, pt2.y), (pt3.x, pt3.y)))
            prevPoint = segment.onCurve
    return unnecessaryHandles

# Points

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

# Utilities

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
    width = point2.x - point1.x
    height = point2.y - point1.y
    angle = round(math.atan2(height, width) * 180 / math.pi, 3)
    if r is not None:
        angle = round(angle, r)
    return angle


if __name__ == "__main__":
    OutlineTutorControls()
