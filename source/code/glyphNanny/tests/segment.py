import defcon
from .tools import unwrapPoint
from . import registry

# Wrapping

from fontParts.world import dispatcher
RFont = dispatcher["RFont"]
RGlyph = dispatcher["RGlyph"]
RContour = dispatcher["RContour"]

def wrapFont(font):
    if isinstance(font, defcon.Font):
        return RFont(font)
    return font

def wrapGlyph(glyph):
    if isinstance(glyph, defcon.Glyph):
        return RGlyph(glyph)
    return glyph

def wrapContour(contour):
    if isinstance(contour, defcon.Contour):
        return RContour(contour)
    return contour

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