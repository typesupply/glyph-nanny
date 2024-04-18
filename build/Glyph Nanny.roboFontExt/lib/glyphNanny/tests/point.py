from fontTools.misc import bezierTools as ftBezierTools
import defcon
from fontPens.penTools import distance
from . import registry
from .wrappers import *
from .tools import (
    unwrapPoint,
    calculateAngle
)

# Stray Points

def testForStrayPoints(contour):
    """
    There should be no stray points.

    Data structure:

        (x, y)
    """
    contour = wrapContour(contour)
    if len(contour) == 1:
        pt = contour[0].onCurve
        pt = (pt.x, pt.y)
        return pt
    return None

registry.registerTest(
    identifier="strayPoints",
    level="point",
    title="Stray Points",
    description="One or more stray points are present.",
    testFunction=testForStrayPoints,
    defconClass=defcon.Contour,
    destructiveNotifications=["Contour.PointsChanged"]
)

# Unnecessary Points

def testForUnnecessaryPoints(contour):
    """
    Consecutive segments shouldn't have the same angle.
    Non-exteme curve points between curve points shouldn't
    exist unless they are needed to support the curve.

    Data structure:

        [
            point,
            ...
        ]
    """
    contour = wrapContour(contour)
    unnecessaryPoints = _testForUnnecessaryLinePoints(contour)
    unnecessaryPoints += _testForUnnecessaryCurvePoints(contour)
    return unnecessaryPoints

def _testForUnnecessaryLinePoints(contour):
    unnecessaryPoints = []
    for segmentIndex, segment in enumerate(contour):
        if segment.type == "line":
            prevSegment = contour[segmentIndex - 1]
            nextSegment = contour[(segmentIndex + 1) % len(contour)]
            if nextSegment.type == "line":
                thisAngle = calculateAngle(prevSegment.onCurve, segment.onCurve)
                nextAngle = calculateAngle(segment.onCurve, nextSegment.onCurve)
                if thisAngle == nextAngle:
                    unnecessaryPoints.append(unwrapPoint(segment.onCurve))
    return unnecessaryPoints

def _testForUnnecessaryCurvePoints(contour):
    # Art School Graduate Implementation of Fréchet Distance
    # ------------------------------------------------------
    # aka "a probably poor understanding of Fréchet Distance with a
    # clumsy implementation, but, hey, we're not doing rocket science."
    #
    # 1. find the relative T for the first segment in the before.
    # 2. split the after segment into two segments.
    # 3. divide all for segments into flattened subsegments.
    # 4. determine the maximum distance between corresponding points
    #    in the corresponding subsegments.
    # 5. if the distance exceeds the "leash" length, the point
    #    is necessary.
    tolerance = 0.035
    unnecessaryPoints = []
    bPoints = list(contour.bPoints)
    if len(bPoints) < 3:
        return unnecessaryPoints
    for i, bPoint in enumerate(bPoints):
        if bPoint.type == "curve":
            inX, inY = bPoint.bcpIn
            outX, outY = bPoint.bcpOut
            if all((inX != outX, inX != 0, outX != 0, inY != outY, inY != 0, outY != 0)):
                afterContour = contour.copy()
                afterContour.removeBPoint(afterContour.bPoints[i], preserveCurve=True)
                afterBPoints = afterContour.bPoints
                # calculate before length
                start = i - 1
                middle = i
                end = i + 1
                if start == -1:
                    start = len(bPoints) - 1
                if end == len(bPoints):
                    end = 0
                start = bPoints[start]
                middle = bPoints[middle]
                end = bPoints[end]
                beforeSegment1 = (
                    start.anchor,
                    _makeBCPAbsolute(start.anchor, start.bcpOut),
                    _makeBCPAbsolute(middle.anchor, middle.bcpIn),
                    middle.anchor
                )
                beforeSegment2 = (
                    middle.anchor,
                    _makeBCPAbsolute(middle.anchor, middle.bcpOut),
                    _makeBCPAbsolute(end.anchor, end.bcpIn),
                    end.anchor
                )
                beforeSegment1Length = abs(ftBezierTools.approximateCubicArcLength(*beforeSegment1))
                beforeSegment2Length = abs(ftBezierTools.approximateCubicArcLength(*beforeSegment2))
                beforeLength = beforeSegment1Length + beforeSegment2Length
                # calculate after length
                start = i - 1
                end = i
                if start == -1:
                    start = len(afterBPoints) - 1
                if end == len(afterBPoints):
                    end = 0
                start = afterBPoints[start]
                end = afterBPoints[end]
                afterSegment = (
                    start.anchor,
                    _makeBCPAbsolute(start.anchor, start.bcpOut),
                    _makeBCPAbsolute(end.anchor, end.bcpIn),
                    end.anchor
                )
                midT = beforeSegment1Length / beforeLength
                afterSegment1, afterSegment2 = ftBezierTools.splitCubicAtT(*afterSegment, midT)
                subSegmentCount = 10
                beforeSegment1Points = _splitSegmentByCount(*beforeSegment1, subSegmentCount=subSegmentCount)
                beforeSegment2Points = _splitSegmentByCount(*beforeSegment2, subSegmentCount=subSegmentCount)
                afterSegment1Points = _splitSegmentByCount(*afterSegment1, subSegmentCount=subSegmentCount)
                afterSegment2Points = _splitSegmentByCount(*afterSegment2, subSegmentCount=subSegmentCount)
                beforePoints = beforeSegment1Points + beforeSegment2Points[1:]
                afterPoints = afterSegment1Points + afterSegment2Points[1:]
                leashLength = beforeLength * tolerance
                isUnnecessary = True
                for i, b in enumerate(beforePoints):
                    a = afterPoints[i]
                    d = abs(distance(a, b))
                    if d > leashLength:
                        isUnnecessary = False
                        break
                if isUnnecessary:
                    unnecessaryPoints.append(bPoint.anchor)
    return unnecessaryPoints

def _makeBCPAbsolute(anchor, bcp):
    x1, y1 = anchor
    x2, y2 = bcp
    return (x1 + x2, y1 + y2)

def _splitSegmentByCount(pt1, pt2, pt3, pt4, subSegmentCount=10):
    ts = [i / subSegmentCount for i in range(subSegmentCount + 1)]
    splits = ftBezierTools.splitCubicAtT(pt1, pt2, pt3, pt4, *ts)
    anchors = []
    for segment in splits:
        anchors.append(segment[-1])
    return anchors

registry.registerTest(
    identifier="unnecessaryPoints",
    level="point",
    title="Unnecessary Points",
    description="One or more unnecessary points are present.",
    testFunction=testForUnnecessaryPoints,
    defconClass=defcon.Contour,
    destructiveNotifications=["Contour.PointsChanged"]
)

# Overlapping Points

def testForOverlappingPoints(contour):
    """
    Consecutive points should not overlap.

    Data structure:

        [
            point,
            ...
        ]
    """
    contour = wrapContour(contour)
    overlappingPoints = []
    if len(contour) > 1:
        prev = unwrapPoint(contour[-1].onCurve)
        for segment in contour:
            point = unwrapPoint(segment.onCurve)
            if point == prev:
                overlappingPoints.append(point)
            prev = point
    return overlappingPoints

registry.registerTest(
    identifier="overlappingPoints",
    level="point",
    title="Overlapping Points",
    description="Two or more points are overlapping.",
    testFunction=testForOverlappingPoints,
    defconClass=defcon.Contour,
    destructiveNotifications=["Contour.PointsChanged"]
)
