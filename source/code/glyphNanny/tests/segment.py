"""
Segment level tests.
"""

from fontTools.misc import bezierTools as ftBezierTools
import defcon
from .tools import (
    roundPoint,
    unwrapPoint,
    calculateAngle,
    calculateAngleOffset,
    calculateLineLineIntersection,
    calculateLineCurveIntersection,
    calculateLineLength,
    calculateLineThroughPoint
)
from . import registry
from .wrappers import *

# Straight Lines

def testForAngleNearMiss(contour):
    """
    Lines shouldn't be just shy of vertical or horizontal.

    Data structure:

        set(
            (pt1, pt2),
            ...
        )

    """
    contour = wrapContour(contour)
    segments = contour.segments
    prev = unwrapPoint(segments[-1].onCurve)
    slightlyOffLines = set()
    for segment in segments:
        point = unwrapPoint(segment.onCurve)
        if segment[-1].type == "line":
            x = abs(prev[0] - point[0])
            y = abs(prev[1] - point[1])
            if x > 0 and x <= 5 and prev[1] != point[1]:
                slightlyOffLines.add((prev, point))
            if y > 0 and y <= 5 and prev[0] != point[0]:
                slightlyOffLines.add((prev, point))
        prev = point
    return slightlyOffLines

registry.registerTest(
    identifier="angleNearMiss",
    level="segment",
    title="Angle Near Miss",
    description="One or more lines are nearly at important angles.",
    testFunction=testForAngleNearMiss,
    defconClass=defcon.Contour,
    destructiveNotifications=["Contour.PointsChanged"]
)

# Segments Near Vertical Metrics

def testForSegmentsNearVerticalMetrics(contour):
    """
    Points shouldn't be just off a vertical metric or blue zone.

    Data structure:

        {
            vertical metric y value : set(pt, ...),
            ...
        }

    """
    font = wrapFont(contour.font)
    glyph = wrapGlyph(contour.glyph)
    contour = wrapContour(contour)
    threshold = 5
    # gather the blues into top and bottom groups
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
    if len(contour) >= 3:
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
                        if contour.pointInside((x, y - 1)):
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
                        if contour.pointInside((x, y + 1)):
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

registry.registerTest(
    identifier="pointsNearVerticalMetrics",
    level="segment",
    title="Near Vertical Metrics",
    description="Two or more points are just off a vertical metric.",
    testFunction=testForSegmentsNearVerticalMetrics,
    defconClass=defcon.Contour,
    destructiveNotifications=["Contour.PointsChanged"]
)

# Unsmooth Smooths

def testUnsmoothSmooths(contour):
    """
    Smooth segments should have bcps in the right places.

    Data structure:

        [
            (offcurvePoint, point, offcurvePoint),
            ...
        ]
    """
    contour = wrapContour(contour)
    unsmoothSmooths = []
    prev = contour[-1]
    for segment in contour:
        if prev.type == "curve" and segment.type == "curve":
            if prev.smooth:
                angle1 = calculateAngle(prev.offCurve[1], prev.onCurve, r=0)
                angle2 = calculateAngle(prev.onCurve, segment.offCurve[0], r=0)
                if angle1 != angle2:
                    pt1 = unwrapPoint(prev.offCurve[1])
                    pt2 = unwrapPoint(prev.onCurve)
                    pt3 = unwrapPoint(segment.offCurve[0])
                    unsmoothSmooths.append((pt1, pt2, pt3))
        prev = segment
    return unsmoothSmooths

registry.registerTest(
    identifier="unsmoothSmooths",
    level="segment",
    title="Unsmooth Smooths",
    description="One or more smooth points do not have handles that are properly placed.",
    testFunction=testUnsmoothSmooths,
    defconClass=defcon.Contour,
    destructiveNotifications=["Contour.PointsChanged"]
)

# Complex Curves

def testForComplexCurves(contour):
    """
    S curves are suspicious.

    Data structure:

        [
            (onCurve, offCurve, offCurve, onCurve),
            ...
        ]
    """
    contour = wrapContour(contour)
    impliedS = []
    prev = unwrapPoint(contour[-1].onCurve)
    for segment in contour:
        if segment.type == "curve":
            pt0 = prev
            pt1, pt2 = [unwrapPoint(p) for p in segment.offCurve]
            pt3 = unwrapPoint(segment.onCurve)
            line1 = (pt0, pt3)
            line2 = (pt1, pt2)
            if calculateLineLineIntersection(line1, line2):
                impliedS.append((prev, pt1, pt2, pt3))
        prev = unwrapPoint(segment.onCurve)
    return impliedS

registry.registerTest(
    identifier="complexCurves",
    level="segment",
    title="Complex Curves",
    description="One or more curves is suspiciously complex.",
    testFunction=testForComplexCurves,
    defconClass=defcon.Contour,
    destructiveNotifications=["Contour.PointsChanged"]
)


# Crossed Handles

def testForCrossedHandles(contour):
    """
    Handles shouldn't intersect.

    Data structure:

        [
            {
                points : (pt1, pt2, pt3, pt4),
                intersection : pt
            },
            ...
        ]
    """
    contour = wrapContour(contour)
    crossedHandles = []
    pt0 = unwrapPoint(contour[-1].onCurve)
    for segment in contour:
        pt3 = unwrapPoint(segment.onCurve)
        if segment.type == "curve":
            pt1, pt2 = [unwrapPoint(p) for p in segment.offCurve]
            # direct intersection
            direct = calculateLineLineIntersection((pt0, pt1), (pt2, pt3))
            if direct:
                if _crossedHanldeWithNoOtherOptions(direct, pt0, pt1, pt2, pt3):
                    pass
                else:
                    crossedHandles.append(dict(points=(pt0, pt1, pt2, pt3), intersection=direct))
            # indirect intersection
            else:
                while 1:
                    # bcp1 = ray, bcp2 = segment
                    angle = calculateAngle(pt0, pt1)
                    if angle in (0, 180.0):
                        t1 = (pt0[0] + 1000, pt0[1])
                        t2 = (pt0[0] - 1000, pt0[1])
                    else:
                        yOffset = calculateAngleOffset(angle, 1000)
                        t1 = (pt0[0] + 1000, pt0[1] + yOffset)
                        t2 = (pt0[0] - 1000, pt0[1] - yOffset)
                    indirect = calculateLineLineIntersection((t1, t2), (pt2, pt3))
                    if indirect:
                        if _crossedHanldeWithNoOtherOptions(indirect, pt0, pt1, pt2, pt3):
                            pass
                        else:
                            crossedHandles.append(dict(points=(pt0, indirect, pt2, pt3), intersection=indirect))
                        break
                    # bcp1 = segment, bcp2 = ray
                    angle = calculateAngle(pt3, pt2)
                    if angle in (90.0, 270.0):
                        t1 = (pt3[0], pt3[1] + 1000)
                        t2 = (pt3[0], pt3[1] - 1000)
                    else:
                        yOffset = calculateAngleOffset(angle, 1000)
                        t1 = (pt3[0] + 1000, pt3[1] + yOffset)
                        t2 = (pt3[0] - 1000, pt3[1] - yOffset)
                    indirect = calculateLineLineIntersection((t1, t2), (pt0, pt1))
                    if indirect:
                        if _crossedHanldeWithNoOtherOptions(indirect, pt0, pt1, pt2, pt3):
                            pass
                        else:
                            crossedHandles.append(dict(points=(pt0, pt1, indirect, pt3), intersection=indirect))
                        break
                    break
        pt0 = pt3
    return crossedHandles

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

registry.registerTest(
    identifier="crossedHandles",
    level="segment",
    title="Crossed Handles",
    description="One or more curves contain crossed handles.",
    testFunction=testForCrossedHandles,
    defconClass=defcon.Contour,
    destructiveNotifications=["Contour.PointsChanged"]
)


# Unnecessary Handles

def testForUnnecessaryHandles(contour):
    """
    Handles shouldn't be used if they aren't doing anything.

    Data structure:

        [
            (pt1, pt2),
            ...
        ]
    """
    contour = wrapContour(contour)
    unnecessaryHandles = []
    prevPoint = contour[-1].onCurve
    for segment in contour:
        if segment.type == "curve":
            pt0 = prevPoint
            pt1, pt2 = segment.offCurve
            pt3 = segment.onCurve
            lineAngle = calculateAngle(pt0, pt3, 0)
            bcpAngle1 = bcpAngle2 = None
            if (pt0.x, pt0.y) != (pt1.x, pt1.y):
                bcpAngle1 = calculateAngle(pt0, pt1, 0)
            if (pt2.x, pt2.y) != (pt3.x, pt3.y):
                bcpAngle2 = calculateAngle(pt2, pt3, 0)
            if bcpAngle1 == lineAngle and bcpAngle2 == lineAngle:
                unnecessaryHandles.append((unwrapPoint(pt1), unwrapPoint(pt2)))
        prevPoint = segment.onCurve
    return unnecessaryHandles

registry.registerTest(
    identifier="unnecessaryHandles",
    level="segment",
    title="Unnecessary Handles",
    description="One or more curves has unnecessary handles.",
    testFunction=testForUnnecessaryHandles,
    defconClass=defcon.Contour,
    destructiveNotifications=["Contour.PointsChanged"]
)


# Uneven Handles

def testForUnevenHandles(contour):
    """
    Handles should share the workload as evenly as possible.

    Data structure:

        [
            (off1, off2, off1Shape, off2Shape),
            ...
        ]

    """
    contour = wrapContour(contour)
    unevenHandles = []
    prevPoint = contour[-1].onCurve
    for segment in contour:
        if segment.type == "curve":
            # create rays perpendicular to the
            # angle between the on and off
            # through the on
            on1 = unwrapPoint(prevPoint)
            off1, off2 = [unwrapPoint(pt) for pt in segment.offCurve]
            on2 = unwrapPoint(segment.onCurve)
            curve = (on1, off1, off2, on2)
            off1Angle = calculateAngle(on1, off1) - 90
            on1Ray = calculateLineThroughPoint(on1, off1Angle)
            off2Angle = calculateAngle(off2, on2) - 90
            on2Ray = calculateLineThroughPoint(on2, off2Angle)
            # find the intersection of the rays
            rayIntersection = calculateLineLineIntersection(on1Ray, on2Ray)
            if rayIntersection is not None:
                # draw a line between the off curves and the intersection
                # and find out where these lines intersect the curve
                off1Intersection = calculateLineCurveIntersection((off1, rayIntersection), curve)
                off2Intersection = calculateLineCurveIntersection((off2, rayIntersection), curve)
                if off1Intersection is not None and off2Intersection is not None:
                    if off1Intersection.points and off2Intersection.points:
                        off1IntersectionPoint = (off1Intersection.points[0].x, off1Intersection.points[0].y)
                        off2IntersectionPoint = (off2Intersection.points[0].x, off2Intersection.points[0].y)
                        # assemble the off curves and their intersections into lines
                        off1Line = (off1, off1IntersectionPoint)
                        off2Line = (off2, off2IntersectionPoint)
                        # measure and compare these
                        # if they are not both very short calculate the ratio
                        length1, length2 = sorted((calculateLineLength(*off1Line), calculateLineLength(*off2Line)))
                        if length1 >= 3 and length2 >= 3:
                            ratio = length2 / float(length1)
                            # if outside acceptable range, flag
                            if ratio > 1.5:
                                off1Shape = _getUnevenHandleShape(on1, off1, off2, on2, off1Intersection, on1, off1IntersectionPoint, off1)
                                off2Shape = _getUnevenHandleShape(on1, off1, off2, on2, off2Intersection, off2IntersectionPoint, on2, off2)
                                unevenHandles.append((off1, off2, off1Shape, off2Shape))
        prevPoint = segment.onCurve
    return unevenHandles

def _getUnevenHandleShape(pt0, pt1, pt2, pt3, intersection, start, end, off):
    splitSegments = ftBezierTools.splitCubicAtT(pt0, pt1, pt2, pt3, *intersection.t)
    curves = []
    for segment in splitSegments:
        if roundPoint(segment[0]) != roundPoint(start) and not curves:
            continue
        curves.append(segment[1:])
        if roundPoint(segment[-1]) == roundPoint(end):
            break
    return curves + [off, start]

registry.registerTest(
    identifier="unevenHandles",
    level="segment",
    title="Uneven Handles",
    description="One or more curves has uneven handles.",
    testFunction=testForUnevenHandles,
    defconClass=defcon.Contour,
    destructiveNotifications=["Contour.PointsChanged"]
)