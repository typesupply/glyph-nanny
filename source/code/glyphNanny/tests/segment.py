"""
Segment level tests.
"""

import defcon
from .tools import unwrapPoint
from . import registry
from .wrappers import *

# Straight Lines

def testForStraightLines(contour):
    """
    Lines shouldn't be just shy of vertical or horizontal.

    structure:

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
    identifier="straightLines",
    level="segment",
    title="Straight Lines",
    description="One or more lines is a few units from being horizontal or vertical.",
    testFunction=testForStraightLines,
    defconClass=defcon.Contour,
    destructiveNotifications=["Contour.PointsChanged"]
)

# Segments Near Vertical Metrics

def testForSegmentsNearVerticalMetrics(contour):
    """
    Points shouldn't be just off a vertical metric or blue zone.

    structure:

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


# # Unsmooth Smooths
# 
# def testUnsmoothSmooths(glyph):
#     """
#     Smooth segments should have bcps in the right places.
#     """
#     unsmoothSmooths = {}
#     for index, contour in enumerate(glyph):
#         prev = contour[-1]
#         for segment in contour:
#             if prev.type == "curve" and segment.type == "curve":
#                 if prev.smooth:
#                     angle1 = _calcAngle(prev.offCurve[1], prev.onCurve, r=0)
#                     angle2 = _calcAngle(prev.onCurve, segment.offCurve[0], r=0)
#                     if angle1 != angle2:
#                         if index not in unsmoothSmooths:
#                             unsmoothSmooths[index] = []
#                         pt1 = _unwrapPoint(prev.offCurve[1])
#                         pt2 = _unwrapPoint(prev.onCurve)
#                         pt3 = _unwrapPoint(segment.offCurve[0])
#                         unsmoothSmooths[index].append((pt1, pt2, pt3))
#             prev = segment
#     return unsmoothSmooths
# 
# def drawUnsmoothSmooths(contours, scale, glyph):
#     color = defaults.colorReview
#     color.set()
#     for contourIndex, points in contours.items():
#         path = NSBezierPath.bezierPath()
#         for pt1, pt2, pt3 in points:
#             path.moveToPoint_(pt1)
#             path.lineToPoint_(pt3)
#             path.setLineWidth_(highlightLineWidth * scale)
#             path.stroke()
#             if defaults.showTitles:
#                 x, y = pt2
#                 drawString((x, y), "Unsmooth Smooth", scale, color, backgroundColor=NSColor.whiteColor())
# 
# registerTest(
#     identifier="unsmoothSmooths",
#     level="segment",
#     title="Unsmooth Smooths",
#     description="One or more smooth points do not have handles that are properly placed.",
#     testFunction=testUnsmoothSmooths,
#     drawingFunction=drawUnsmoothSmooths
# )
# 
# # Complex Curves
# 
# def testForComplexCurves(glyph):
#     """
#     S curves are suspicious.
#     """
#     impliedS = {}
#     for index, contour in enumerate(glyph):
#         prev = _unwrapPoint(contour[-1].onCurve)
#         for segment in contour:
#             if segment.type == "curve":
#                 pt0 = prev
#                 pt1, pt2 = [_unwrapPoint(p) for p in segment.offCurve]
#                 pt3 = _unwrapPoint(segment.onCurve)
#                 line1 = (pt0, pt3)
#                 line2 = (pt1, pt2)
#                 if _intersectLines(line1, line2):
#                     if index not in impliedS:
#                         impliedS[index] = []
#                     impliedS[index].append((prev, pt1, pt2, pt3))
#             prev = _unwrapPoint(segment.onCurve)
#     return impliedS
# 
# def drawComplexCurves(contours, scale, glyph):
#     color = defaults.colorReview
#     color.set()
#     for contourIndex, segments in contours.items():
#         for segment in segments:
#             pt0, pt1, pt2, pt3 = segment
#             path = NSBezierPath.bezierPath()
#             path.moveToPoint_(pt0)
#             path.curveToPoint_controlPoint1_controlPoint2_(pt3, pt1, pt2)
#             path.setLineWidth_(highlightLineWidth * scale)
#             path.setLineCapStyle_(NSRoundLineCapStyle)
#             path.stroke()
#             if defaults.showTitles:
#                 mid = ftBezierTools.splitCubicAtT(pt0, pt1, pt2, pt3, 0.5)[0][-1]
#                 drawString(mid, "Complex Curve", scale, color, backgroundColor=NSColor.whiteColor())
# 
# registerTest(
#     identifier="complexCurves",
#     level="segment",
#     title="Complex Curves",
#     description="One or more curves is suspiciously complex.",
#     testFunction=testForComplexCurves,
#     drawingFunction=drawComplexCurves
# )
# 
# # Crossed Handles
# 
# def _crossedHanldeWithNoOtherOptions(hit, pt0, pt1, pt2, pt3):
#     hitWidth = max((abs(hit[0] - pt0[0]), abs(hit[0] - pt3[0])))
#     hitHeight = max((abs(hit[1] - pt0[1]), abs(hit[1] - pt3[1])))
#     w = abs(pt0[0] - pt3[0])
#     h = abs(pt0[1] - pt3[1])
#     bw = max((abs(pt0[0] - pt1[0]), abs(pt3[0] - pt2[0])))
#     bh = max((abs(pt0[1] - pt1[1]), abs(pt3[1] - pt2[1])))
#     if w == 1 and bw == 1 and not bh > h:
#         return True
#     elif h == 1 and bh == 1 and not bw > w:
#         return True
#     return False
# 
# def testForCrossedHandles(glyph):
#     """
#     Handles shouldn't intersect.
#     """
#     crossedHandles = {}
#     for index, contour in enumerate(glyph):
#         pt0 = _unwrapPoint(contour[-1].onCurve)
#         for segment in contour:
#             pt3 = _unwrapPoint(segment.onCurve)
#             if segment.type == "curve":
#                 pt1, pt2 = [_unwrapPoint(p) for p in segment.offCurve]
#                 # direct intersection
#                 direct = _intersectLines((pt0, pt1), (pt2, pt3))
#                 if direct:
#                     if _crossedHanldeWithNoOtherOptions(direct, pt0, pt1, pt2, pt3):
#                         pass
#                     else:
#                         if index not in crossedHandles:
#                             crossedHandles[index] = []
#                         crossedHandles[index].append(dict(points=(pt0, pt1, pt2, pt3), intersection=direct))
#                 # indirect intersection
#                 else:
#                     while 1:
#                         # bcp1 = ray, bcp2 = segment
#                         angle = _calcAngle(pt0, pt1)
#                         if angle in (0, 180.0):
#                             t1 = (pt0[0] + 1000, pt0[1])
#                             t2 = (pt0[0] - 1000, pt0[1])
#                         else:
#                             yOffset = _getAngleOffset(angle, 1000)
#                             t1 = (pt0[0] + 1000, pt0[1] + yOffset)
#                             t2 = (pt0[0] - 1000, pt0[1] - yOffset)
#                         indirect = _intersectLines((t1, t2), (pt2, pt3))
#                         if indirect:
#                             if _crossedHanldeWithNoOtherOptions(indirect, pt0, pt1, pt2, pt3):
#                                 pass
#                             else:
#                                 if index not in crossedHandles:
#                                     crossedHandles[index] = []
#                                 crossedHandles[index].append(dict(points=(pt0, indirect, pt2, pt3), intersection=indirect))
#                             break
#                         # bcp1 = segment, bcp2 = ray
#                         angle = _calcAngle(pt3, pt2)
#                         if angle in (90.0, 270.0):
#                             t1 = (pt3[0], pt3[1] + 1000)
#                             t2 = (pt3[0], pt3[1] - 1000)
#                         else:
#                             yOffset = _getAngleOffset(angle, 1000)
#                             t1 = (pt3[0] + 1000, pt3[1] + yOffset)
#                             t2 = (pt3[0] - 1000, pt3[1] - yOffset)
#                         indirect = _intersectLines((t1, t2), (pt0, pt1))
#                         if indirect:
#                             if _crossedHanldeWithNoOtherOptions(indirect, pt0, pt1, pt2, pt3):
#                                 pass
#                             else:
#                                 if index not in crossedHandles:
#                                     crossedHandles[index] = []
#                                 crossedHandles[index].append(dict(points=(pt0, pt1, indirect, pt3), intersection=indirect))
#                             break
#                         break
#             pt0 = pt3
#     return crossedHandles
# 
# def drawCrossedHandles(contours, scale, glyph):
#     d = 10 * scale
#     h = d / 2.0
#     color = defaults.colorReview
#     color.set()
#     for contourIndex, segments in contours.items():
#         for segment in segments:
#             pt1, pt2, pt3, pt4 = segment["points"]
#             pt5 = segment["intersection"]
#             path1 = NSBezierPath.bezierPath()
#             path2 = NSBezierPath.bezierPath()
#             path1.moveToPoint_(pt1)
#             path1.lineToPoint_(pt2)
#             path1.moveToPoint_(pt3)
#             path1.lineToPoint_(pt4)
#             x, y = pt5
#             r = ((x - h, y - h), (d, d))
#             path2.appendBezierPathWithOvalInRect_(r)
#             path1.setLineWidth_(highlightLineWidth * scale)
#             path1.setLineCapStyle_(NSRoundLineCapStyle)
#             path1.stroke()
#             path2.fill()
#             if defaults.showTitles:
#                 drawString((x, y), "Crossed Handles", scale, color, vAlignment="top", vOffset="-y", backgroundColor=NSColor.whiteColor())
# 
# registerTest(
#     identifier="crossedHandles",
#     level="segment",
#     title="Crossed Handles",
#     description="One or more curves contain crossed handles.",
#     testFunction=testForCrossedHandles,
#     drawingFunction=drawCrossedHandles
# )
# 
# # Unnecessary Handles
# 
# def testForUnnecessaryHandles(glyph):
#     """
#     Handles shouldn't be used if they aren't doing anything.
#     """
#     unnecessaryHandles = {}
#     for index, contour in enumerate(glyph):
#         prevPoint = contour[-1].onCurve
#         for segment in contour:
#             if segment.type == "curve":
#                 pt0 = prevPoint
#                 pt1, pt2 = segment.offCurve
#                 pt3 = segment.onCurve
#                 lineAngle = _calcAngle(pt0, pt3, 0)
#                 bcpAngle1 = bcpAngle2 = None
#                 if (pt0.x, pt0.y) != (pt1.x, pt1.y):
#                     bcpAngle1 = _calcAngle(pt0, pt1, 0)
#                 if (pt2.x, pt2.y) != (pt3.x, pt3.y):
#                     bcpAngle2 = _calcAngle(pt2, pt3, 0)
#                 if bcpAngle1 == lineAngle and bcpAngle2 == lineAngle:
#                     if index not in unnecessaryHandles:
#                         unnecessaryHandles[index] = []
#                     unnecessaryHandles[index].append((_unwrapPoint(pt1), _unwrapPoint(pt2)))
#             prevPoint = segment.onCurve
#     return unnecessaryHandles
# 
# def drawUnnecessaryHandles(contours, scale, glyph):
#     color = defaults.colorRemove
#     color.set()
#     d = 10 * scale
#     h = d / 2.0
#     for contourIndex, points in contours.items():
#         for bcp1, bcp2 in points:
#             path = NSBezierPath.bezierPath()
#             drawDeleteMark(bcp1, scale, path=path)
#             drawDeleteMark(bcp2, scale, path=path)
#             path.setLineWidth_(generalLineWidth * scale)
#             path.stroke()
#             path = NSBezierPath.bezierPath()
#             path.moveToPoint_(bcp1)
#             path.lineToPoint_(bcp2)
#             path.setLineWidth_(highlightLineWidth * scale)
#             path.stroke()
#             if defaults.showTitles:
#                 mid = calcMid(bcp1, bcp2)
#                 drawString(mid, "Unnecessary Handles", scale, color, backgroundColor=NSColor.whiteColor())
# 
# registerTest(
#     identifier="unnecessaryHandles",
#     level="segment",
#     title="Unnecessary Handles",
#     description="One or more curves has unnecessary handles.",
#     testFunction=testForUnnecessaryHandles,
#     drawingFunction=drawUnnecessaryHandles
# )
# 
# # Uneven Handles
# 
# def testForUnevenHandles(glyph):
#     """
#     Handles should share the workload as evenly as possible.
#     """
#     unevenHandles = {}
#     for index, contour in enumerate(glyph):
#         prevPoint = contour[-1].onCurve
#         for segment in contour:
#             if segment.type == "curve":
#                 # create rays perpendicular to the
#                 # angle between the on and off
#                 # through the on
#                 on1 = _unwrapPoint(prevPoint)
#                 off1, off2 = [_unwrapPoint(pt) for pt in segment.offCurve]
#                 on2 = _unwrapPoint(segment.onCurve)
#                 curve = (on1, off1, off2, on2)
#                 off1Angle = _calcAngle(on1, off1) - 90
#                 on1Ray = _createLineThroughPoint(on1, off1Angle)
#                 off2Angle = _calcAngle(off2, on2) - 90
#                 on2Ray = _createLineThroughPoint(on2, off2Angle)
#                 # find the intersection of the rays
#                 rayIntersection = _intersectLines(on1Ray, on2Ray)
#                 if rayIntersection is not None:
#                     # draw a line between the off curves and the intersection
#                     # and find out where these lines intersect the curve
#                     off1Intersection = _getLineCurveIntersection((off1, rayIntersection), curve)
#                     off2Intersection = _getLineCurveIntersection((off2, rayIntersection), curve)
#                     if off1Intersection is not None and off2Intersection is not None:
#                         if off1Intersection.points and off2Intersection.points:
#                             off1IntersectionPoint = (off1Intersection.points[0].x, off1Intersection.points[0].y)
#                             off2IntersectionPoint = (off2Intersection.points[0].x, off2Intersection.points[0].y)
#                             # assemble the off curves and their intersections into lines
#                             off1Line = (off1, off1IntersectionPoint)
#                             off2Line = (off2, off2IntersectionPoint)
#                             # measure and compare these
#                             # if they are not both very short calculate the ratio
#                             length1, length2 = sorted((_getLineLength(*off1Line), _getLineLength(*off2Line)))
#                             if length1 >= 3 and length2 >= 3:
#                                 ratio = length2 / float(length1)
#                                 # if outside acceptable range, flag
#                                 if ratio > 1.5:
#                                     off1Shape = _getUnevenHandleShape(on1, off1, off2, on2, off1Intersection, on1, off1IntersectionPoint, off1)
#                                     off2Shape = _getUnevenHandleShape(on1, off1, off2, on2, off2Intersection, off2IntersectionPoint, on2, off2)
#                                     if index not in unevenHandles:
#                                         unevenHandles[index] = []
#                                     unevenHandles[index].append((off1, off2, off1Shape, off2Shape))
#             prevPoint = segment.onCurve
#     return unevenHandles
# 
# def _getUnevenHandleShape(pt0, pt1, pt2, pt3, intersection, start, end, off):
#     splitSegments = ftBezierTools.splitCubicAtT(pt0, pt1, pt2, pt3, *intersection.t)
#     curves = []
#     for segment in splitSegments:
#         if _roundPoint(segment[0]) != _roundPoint(start) and not curves:
#             continue
#         curves.append(segment[1:])
#         if _roundPoint(segment[-1]) == _roundPoint(end):
#             break
#     return curves + [off, start]
# 
# def drawUnevenHandles(contours, scale, glyph):
#     textColor = defaults.colorReview
#     fillColor = modifyColorAlpha(textColor, 0.15)
#     for index, groups in contours.items():
#         for off1, off2, shape1, shape2 in groups:
#             fillColor.set()
#             path = NSBezierPath.bezierPath()
#             for shape in (shape1, shape2):
#                 path.moveToPoint_(shape[-1])
#                 for curve in shape[:-2]:
#                     pt1, pt2, pt3 = curve
#                     path.curveToPoint_controlPoint1_controlPoint2_(pt3, pt1, pt2)
#                 path.lineToPoint_(shape[-2])
#                 path.lineToPoint_(shape[-1])
#             path.fill()
#             if defaults.showTitles:
#                 mid = calcMid(off1, off2)
#                 drawString(mid, "Uneven Handles", scale, textColor, backgroundColor=NSColor.whiteColor())
# 
# registerTest(
#     identifier="unevenHandles",
#     level="segment",
#     title="Uneven Handles",
#     description="One or more curves has uneven handles.",
#     testFunction=testForUnevenHandles,
#     drawingFunction=drawUnevenHandles
# )