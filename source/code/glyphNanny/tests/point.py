import defcon
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

    Data structure:

        [
            point,
            ...
        ]
    """
    contour = wrapContour(contour)
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

registry.registerTest(
    identifier="unnecessaryPoints",
    level="point",
    title="Unnecessary Points",
    description="One or more unnecessary points are present in lines.",
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
