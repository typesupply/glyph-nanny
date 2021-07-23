from fontPens.digestPointPen import DigestPointPen
from fontTools.misc import arrayTools as ftArrayTools
import defcon
from .tools import (
    unwrapPoint,
    calculateAngle
)
from . import registry
from .wrappers import *

# Stem Consistency

def testStemWidths(glyph):
    """
    Stem widths should be consistent.

    Data structure:

        {
            horizontal : [(y1, y2, [x1, x2, ...]), ...]
            vertical : [(x1, x2, [y1, y2, ...]), ...]
        }
    """
    font = wrapFont(glyph.font)
    layer = font.getLayer(glyph.layer.name)
    glyph = layer[glyph.name]
    hProblems = vProblems = None
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
    data = dict(horizontal=hProblems, vertical=vProblems)
    return data

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
        bounds = contour.bounds
        lines = {}
        # line to
        previous = unwrapPoint(contour[-1].onCurve)
        for segment in contour:
            point = unwrapPoint(segment.onCurve)
            if segment.type == "line":
                # only process completely horizontal/vertical lines
                # that have a length greater than 0
                if (previous[primaryCoordinate] == point[primaryCoordinate]) and (previous[secondaryCoordinate] != point[secondaryCoordinate]):
                    angle = calculateAngle(previous, point)
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
                bcp1 = unwrapPoint(previous[1])
                bcp2 = unwrapPoint(segment[-1])
                if bcp1[primaryCoordinate] == bcp2[primaryCoordinate]:
                    angle = calculateAngle(bcp1, bcp2)
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

    def __repr__(self):
        return "<PS Stem Value: value=%d threshold=%d>" % (self.value, self.threshold)

    def __eq__(self, other):
        d = abs(self.value - other)
        return d <= self.threshold

    def diff(self, other):
        return abs(self.value - other)


def _linesOverlap(a1, a2, b1, b2):
    if a1 > b2 or a2 < b1:
        return False
    return True

registry.registerTest(
    identifier="stemWidths",
    level="glyph",
    title="Stem Widths",
    description="One or more stems do not match the registered values.",
    testFunction=testStemWidths,
    defconClass=defcon.Glyph,
    destructiveNotifications=["Glyph.ContoursChanged"]
)

# Duplicate Contours

def testDuplicateContours(glyph):
    """
    Contours shouldn't be duplicated on each other.

    Data structure:

        [
            (contourIndex, bounds),
            ...
        ]
    """
    glyph = wrapGlyph(glyph)
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
            duplicateContours.append((indexes[0], contour.bounds))
    return duplicateContours

registry.registerTest(
    identifier="duplicateContours",
    level="glyph",
    title="Duplicate Contours",
    description="One or more contours are duplicated.",
    testFunction=testDuplicateContours,
    defconClass=defcon.Glyph,
    destructiveNotifications=["Glyph.ContoursChanged"]
)

# Duplicate Components

def testDuplicateComponents(glyph):
    """
    Components shouldn't be duplicated on each other.

        [
            (componentIndex, bounds),
            ...
        ]

    """
    glyph = wrapGlyph(glyph)
    duplicateComponents = []
    components = set()
    for index, component in enumerate(glyph.components):
        key = (component.baseGlyph, component.transformation)
        if key in components:
            duplicateComponents.append((index, component.bounds))
        components.add(key)
    return duplicateComponents

registry.registerTest(
    identifier="duplicateComponents",
    level="glyph",
    title="Duplicate Components",
    description="One or more components are duplicated.",
    testFunction=testDuplicateComponents,
    defconClass=defcon.Glyph,
    destructiveNotifications=["Glyph.ComponentsChanged"]
)
