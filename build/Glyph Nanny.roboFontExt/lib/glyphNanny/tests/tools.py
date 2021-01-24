import math
from fontTools.misc.arrayTools import calcBounds
from lib.tools import bezierTools as rfBezierTools

# -----------
# Conversions
# -----------

def roundPoint(pt):
    return round(pt[0]), round(pt[1])

def unwrapPoint(pt):
    return pt.x, pt.y

def convertBoundsToRect(bounds):
    if bounds is None:
        return (0, 0, 0, 0)
    xMin, yMin, xMax, yMax = bounds
    x = xMin
    y = yMin
    w = xMax - xMin
    h = yMax - yMin
    return (x, y, w, h)

def getOnCurves(contour):
    points = set()
    for segment in contour:
        pt = segment.onCurve
        points.add((pt.x, pt.y))
    return points

# ------------
# Calculations
# ------------

def calculateMidpoint(*points):
    if len(points) != 2:
        xMin, yMin, xMax, yMax = calcBounds(points)
        points = (
            (xMin, yMin),
            (xMax, yMax)
        )
    pt1, pt2 = points
    x1, y1 = pt1
    x2, y2 = pt2
    x = (x1 + x2) / 2
    y = (y1 + y2) / 2
    return (x, y)

def calculateAngle(point1, point2, r=None):
    if not isinstance(point1, tuple):
        point1 = unwrapPoint(point1)
    if not isinstance(point2, tuple):
        point2 = unwrapPoint(point2)
    width = point2[0] - point1[0]
    height = point2[1] - point1[1]
    angle = round(math.atan2(height, width) * 180 / math.pi, 3)
    if r is not None:
        angle = round(angle, r)
    return angle

def calculateLineLineIntersection(a1a2, b1b2):
    # adapted from: http://www.kevlindev.com/gui/math/intersection/Intersection.js
    a1, a2 = a1a2
    b1, b2 = b1b2
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

def calculateLineCurveIntersection(line, curve):
    points = curve + line
    intersection = rfBezierTools.intersectCubicLine(*points)
    return intersection

def calculateAngleOffset(angle, distance):
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

def calculateLineLength(pt1, pt2):
    return math.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])

def calculateAreaOfTriangle(pt1, pt2, pt3):
    a = calculateLineLength(pt1, pt2)
    b = calculateLineLength(pt2, pt3)
    c = calculateLineLength(pt3, pt1)
    s = (a + b + c) / 2.0
    area = math.sqrt(s * (s - a) * (s - b) * (s - c))
    return area

def calculateLineThroughPoint(pt, angle):
    angle = math.radians(angle)
    length = 100000
    x1 = math.cos(angle) * -length + pt[0]
    y1 = math.sin(angle) * -length + pt[1]
    x2 = math.cos(angle) * length + pt[0]
    y2 = math.sin(angle) * length + pt[1]
    return (x1, y1), (x2, y2)
