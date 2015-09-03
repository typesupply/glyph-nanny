import math
from lib.tools import bezierTools

###

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
    return b

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

###

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

def _getSegmentIntersection(bcp, intersection, curve):
    pt0, pt1, pt2, pt3 = curve
    intersection = bezierTools.intersectCubicLine(pt0, pt1, pt2, pt3, bcp, intersection)
    if intersection:
        point = intersection.points[0]
        return point.x, point.y
    return None


###

_points = """
move 84 119
offCurve 131 377
offCurve 528 487
curve 643 418
"""
points = []
for l in _points.strip().splitlines():
    c, x, y = l.split(" ")
    x = int(x)
    y = int(y)
    points.append((x, y))

pt0, pt1, pt2, pt3 = points

# draw the curve
newPath()
moveTo(pt0)
curveTo(pt1, pt2, pt3)

fill(None)
stroke(0)
strokeWidth(1)

drawPath()

# draw the points
stroke(None)
fill(0)

for (x, y) in (pt0, pt1, pt2, pt3):
    oval(x - 5, y - 5, 10, 10)

# find the intersection of the two angles

angle1 = _calcAngle(pt0, pt1) - 90
line1 = _createLineThroughPoint(pt0, angle1)
angle2 = _calcAngle(pt2, pt3) - 90
line2 = _createLineThroughPoint(pt3, angle2)

stroke(1, 0, 0, 1)
strokeWidth(1)
line(*line1)
line(*line2)


intersection = _intersectLines(line1, line2)

x, y = intersection
stroke(None)
fill(1, 0, 0, 0.75)
oval(x - 5, y - 5, 10, 10)

segmentIntersection1 = _getSegmentIntersection(pt1, intersection, (pt0, pt1, pt2, pt3))
segmentIntersection2 = _getSegmentIntersection(pt2, intersection, (pt0, pt1, pt2, pt3))

x, y = segmentIntersection1
oval(x - 5, y - 5, 10, 10)

x, y = segmentIntersection2
oval(x - 5, y - 5, 10, 10)

fill(None)
stroke(1, 0, 0, 1)

line(pt1, segmentIntersection1)
line(pt2, segmentIntersection2)

# # make the triangles

# triangle1 = (intersection, pt0, pt1)
# triangle2 = (intersection, pt2, pt3)

# # draw the traingles

# fill(1, 0, 0, 0.25)
# polygon(*triangle1)
# polygon(*triangle2)

# # find the area of the triangles

# print _getAreaOfTriangle(*triangle1)
# print _getAreaOfTriangle(*triangle2)