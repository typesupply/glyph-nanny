# # Stray Points
# 
# def testForStrayPoints(glyph):
#     """
#     There should be no stray points.
#     """
#     strayPoints = {}
#     for index, contour in enumerate(glyph):
#         if len(contour) == 1:
#             pt = contour[0].onCurve
#             pt = (pt.x, pt.y)
#             strayPoints[index] = pt
#     for index, anchor in enumerate(glyph.anchors):
#         if anchor.name == "":
#             pt = (anchor.x, anchor.y)
#             strayPoints[index+1+len(strayPoints)] = pt
#     return strayPoints
# 
# def drawStrayPoints(contours, scale, glyph):
#     color = defaults.colorRemove
#     path = NSBezierPath.bezierPath()
#     for contourIndex, (x, y) in contours.items():
#         drawDeleteMark((x, y), scale, path=path)
#         if defaults.showTitles:
#             drawString((x, y), "Stray Point", scale, color, vAlignment="top", vOffset="-y")
#     color.set()
#     path.setLineWidth_(generalLineWidth * scale)
#     path.stroke()
# 
# registerTest(
#     identifier="strayPoints",
#     level="point",
#     title="Stray Points",
#     description="One or more stray points are present.",
#     testFunction=testForStrayPoints,
#     drawingFunction=drawStrayPoints
# )
# 
# # Unnecessary Points
# 
# def testForUnnecessaryPoints(glyph):
#     """
#     Consecutive segments shouldn't have the same angle.
#     """
#     unnecessaryPoints = {}
#     for index, contour in enumerate(glyph):
#         for segmentIndex, segment in enumerate(contour):
#             if segment.type == "line":
#                 prevSegment = contour[segmentIndex - 1]
#                 nextSegment = contour[(segmentIndex + 1) % len(contour)]
#                 if nextSegment.type == "line":
#                     thisAngle = calculateAngle(prevSegment.onCurve, segment.onCurve)
#                     nextAngle = calculateAngle(segment.onCurve, nextSegment.onCurve)
#                     if thisAngle == nextAngle:
#                         if index not in unnecessaryPoints:
#                             unnecessaryPoints[index] = []
#                         unnecessaryPoints[index].append(unwrapPoint(segment.onCurve))
#     return unnecessaryPoints
# 
# def drawUnnecessaryPoints(contours, scale, glyph):
#     color = defaults.colorRemove
#     path = NSBezierPath.bezierPath()
#     for contourIndex, points in contours.items():
#         for pt in points:
#             drawDeleteMark(pt, scale, path)
#             if defaults.showTitles:
#                 x, y = pt
#                 drawString((x, y), "Unnecessary Point", scale, color, vAlignment="top", vOffset="-y")
#     color.set()
#     path.setLineWidth_(2 * scale)
#     path.stroke()
# 
# registerTest(
#     identifier="unnecessaryPoints",
#     level="point",
#     title="Unnecessary Points",
#     description="One or more unnecessary points are present in lines.",
#     testFunction=testForUnnecessaryPoints,
#     drawingFunction=drawUnnecessaryPoints
# )
# 
# # Overlapping Points
# 
# def testForOverlappingPoints(glyph):
#     """
#     Consequtive points should not overlap.
#     """
#     overlappingPoints = {}
#     for index, contour in enumerate(glyph):
#         if len(contour) == 1:
#             continue
#         prev = unwrapPoint(contour[-1].onCurve)
#         for segment in contour:
#             point = unwrapPoint(segment.onCurve)
#             if point == prev:
#                 if index not in overlappingPoints:
#                     overlappingPoints[index] = set()
#                 overlappingPoints[index].add(point)
#             prev = point
#     return overlappingPoints
# 
# def drawOverlappingPoints(contours, scale, glyph):
#     color = defaults.colorRemove
#     path = NSBezierPath.bezierPath()
#     for contourIndex, points in contours.items():
#         for (x, y) in points:
#             drawDeleteMark((x, y), scale, path)
#             if defaults.showTitles:
#                 drawString((x, y), "Overlapping Points", scale, color, vAlignment="top", vOffset="-y")
#     color.set()
#     path.setLineWidth_(generalLineWidth * scale)
#     path.stroke()
# 
# registerTest(
#     identifier="overlappingPoints",
#     level="point",
#     title="Overlapping Points",
#     description="Two or more points are overlapping.",
#     testFunction=testForOverlappingPoints,
#     drawingFunction=drawOverlappingPoints
# )