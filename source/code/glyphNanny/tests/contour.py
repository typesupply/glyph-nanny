from fontTools.pens.transformPen import TransformPen
import defcon
from . import registry
from .wrappers import *
from .tools import getOnCurves

# Small Contours

def testForSmallContour(contour):
    """
    Contours should not have an area less than or equal to 4 units.

    Data structure:

        bool
    """
    contour = wrapContour(contour)
    if len(contour) > 1:
        bounds = contour.bounds
        if bounds:
            xMin, yMin, xMax, yMax = bounds
            w = xMax - xMin
            h = yMin - yMax
            area = abs(w * h)
            if area <= 4:
                return True
    return False

registry.registerTest(
    identifier="smallContours",
    level="contour",
    title="Small Contours",
    description="One or more contours are suspiciously small.",
    testFunction=testForSmallContour,
    defconClass=defcon.Contour,
    destructiveNotifications=["Contour.PointsChanged"]
)

# Open Contours

def testForOpenContour(contour):
    """
    Contours should be closed.

    Data structure:

        (startPoint, endPoint)
    """
    contour = wrapContour(contour)
    if contour.open:
        start = contour[0].onCurve
        start = (start.x, start.y)
        end = contour[-1].onCurve
        end = (end.x, end.y)
        if start != end:
            return (start, end)
    return None

registry.registerTest(
    identifier="openContour",
    level="contour",
    title="Open Contours",
    description="One or more contours are not properly closed.",
    testFunction=testForOpenContour,
    defconClass=defcon.Contour,
    destructiveNotifications=["Contour.PointsChanged"]
)

# Extreme Points

def testForExtremePoints(contour):
    """
    Points should be at the extrema.

    Data structure:

        {
            (point),
            ...
        }
    """
    glyph = contour.glyph
    contourIndex = glyph.contourIndex(contour)
    glyph = wrapGlyph(glyph)
    contour = glyph[contourIndex]
    copyGlyph = glyph.copy()
    copyGlyph.clear()
    copyGlyph.appendContour(contour)
    copyGlyph.extremePoints()
    pointsAtExtrema = set()
    testPoints = getOnCurves(copyGlyph[0])
    points = getOnCurves(contour)
    if points != testPoints:
        pointsAtExtrema = testPoints - points
    return pointsAtExtrema

registry.registerTest(
    identifier="extremePoints",
    level="contour",
    title="Extreme Points",
    description="One or more curves need an extreme point.",
    testFunction=testForExtremePoints,
    defconClass=defcon.Contour,
    destructiveNotifications=["Contour.PointsChanged"]
)

# Symmetrical Curves

def testForSlightlyAssymmetricCurves(contour):
    """
    Note adjacent curves that are almost symmetrical.

    Data structure:

        [
            (
                (on, off, off, on),
                (on, off, off, on)
            ),
            ...
        ]
    """
    contour = wrapContour(contour)
    slightlyAsymmetricalCurves = []
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


registry.registerTest(
    identifier="curveSymmetry",
    level="contour",
    title="Curve Symmetry",
    description="One or more curve pairs are slightly asymmetrical.",
    testFunction=testForSlightlyAssymmetricCurves,
    defconClass=defcon.Contour,
    destructiveNotifications=["Contour.PointsChanged"]
)
