# def drawTextReport(report, scale, glyph):
#     text = []
#     r = report.get("unicodeValue")
#     if r:
#         text += r
#     if text:
#         text = "\n".join(text)
#         x = 50
#         y = -50
#         drawString((x, y), text, scale, defaults.colorInform, hAlignment="left")
# 
# # Unicode Value
# 
# uniNamePattern = re.compile(
#     "uni"
#     "([0-9A-Fa-f]{4})"
#     "$"
# )
# 
# def testUnicodeValue(glyph):
#     """
#     A Unicode value should appear only once per font.
#     """
#     report = []
#     font = glyph.getParent()
#     uni = glyph.unicode
#     name = glyph.name
#     # test for uniXXXX name
#     m = uniNamePattern.match(name)
#     if m is not None:
#         uniFromName = m.group(1)
#         uniFromName = int(uniFromName, 16)
#         if uni != uniFromName:
#             report.append("The Unicode value for this glyph does not match its name.")
#     # test against AGLFN
#     else:
#         expectedUni = AGL2UV.get(name)
#         if expectedUni != uni:
#             report.append("The Unicode value for this glyph may not be correct.")
#     # look for duplicates
#     if uni is not None:
#         duplicates = []
#         for name in sorted(font.keys()):
#             if name == glyph.name:
#                 continue
#             other = font[name]
#             if other.unicode == uni:
#                 duplicates.append(name)
#         if duplicates:
#             report.append("The Unicode for this glyph is also used by: %s." % " ".join(duplicates))
#     return report
# 
# registerTest(
#     identifier="unicodeValue",
#     level="glyph",
#     title="Unicode Value",
#     description="Unicode value may have problems.",
#     testFunction=testUnicodeValue,
#     drawingFunction=None
# )
# 
# 
# # Stem Consistency
# 
# def testStemWidths(glyph):
#     """
#     Stem widths should be consistent.
#     """
#     hProblems = vProblems = None
#     font = glyph.getParent()
#     tolerance = 5
#     # horizontal
#     hStems = [_StemWrapper(v, tolerance) for v in font.info.postscriptStemSnapH]
#     if hStems:
#         hProblems = _findStemProblems(glyph, hStems, "h")
#     # vertical
#     vStems = [_StemWrapper(v, tolerance) for v in font.info.postscriptStemSnapV]
#     if vStems:
#         vProblems = _findStemProblems(glyph, vStems, "v")
#     # report
#     if hProblems or vProblems:
#         stemProblems = dict(
#             h=hProblems,
#             v=vProblems
#         )
#         return stemProblems
#     return None
# 
# def drawStemWidths(data, scale, glyph):
#     hProblems = data["h"]
#     vProblems = data["v"]
#     if not hProblems and not vProblems:
#         return
#     font = glyph.getParent()
#     b = font.info.unitsPerEm * 0.25
#     color = textColor = defaults.colorReview
#     # horizontal
#     x = -b
#     w = glyph.width + (b * 2)
#     for y1, y2, xPositions in hProblems:
#         xM = calcCenter(*xPositions)
#         color.set()
#         path = drawLine((xM, y1), (xM, y2), scale, arrowStart=True, arrowEnd=True)
#         path.setLineWidth_(generalLineWidth * scale)
#         path.stroke()
#         if defaults.showTitles:
#             tX, tY = calcMid((xM, y1), (xM, y2))
#             drawString((tX, tY), "Check Stem", scale, textColor, backgroundColor=NSColor.whiteColor())
#     # horizontal
#     y = font.info.descender - b
#     h = max((font.info.ascender, font.info.capHeight)) - y + (b * 2)
#     for x1, x2, yPositions in vProblems:
#         yM = calcCenter(*yPositions)
#         color.set()
#         path = drawLine((x1, yM), (x2, yM), scale, arrowStart=True, arrowEnd=True)
#         path.setLineWidth_(generalLineWidth * scale)
#         path.stroke()
#         if defaults.showTitles:
#             tX, tY = calcMid((x1, yM), (x2, yM))
#             drawString((tX, tY), "Check Stem", scale, textColor, vAlignment="center", backgroundColor=NSColor.whiteColor())
# 
# registerTest(
#     identifier="stemWidths",
#     level="glyph",
#     title="Stem Widths",
#     description="One or more stems do not match the registered values.",
#     testFunction=testStemWidths,
#     drawingFunction=drawStemWidths
# )
# 
# def _findStemProblems(glyph, targetStems, stemDirection):
#     stems = set()
#     # h/v abstraction
#     if stemDirection == "h":
#         primaryCoordinate = 1
#         secondaryCoordinate = 0
#         desiredClockwiseAngle = 0
#         desiredCounterAngle = 180
#     else:
#         primaryCoordinate = 0
#         secondaryCoordinate = 1
#         desiredClockwiseAngle = -90
#         desiredCounterAngle = 90
#     # structure the contour and line data for efficient processing
#     contours = {
#         True : [],
#         False : []
#     }
#     for contour in glyph:
#         contourDirection = contour.clockwise
#         if hasattr(contour, "bounds"):
#             bounds = contour.bounds
#         else:
#             bounds = contour.box
#         lines = {}
#         # line to
#         previous = _unwrapPoint(contour[-1].onCurve)
#         for segment in contour:
#             point = _unwrapPoint(segment.onCurve)
#             if segment.type == "line":
#                 # only process completely horizontal/vertical lines
#                 # that have a length greater than 0
#                 if (previous[primaryCoordinate] == point[primaryCoordinate]) and (previous[secondaryCoordinate] != point[secondaryCoordinate]):
#                     angle = _calcAngle(previous, point)
#                     p = point[primaryCoordinate]
#                     s1 = previous[secondaryCoordinate]
#                     s2 = point[secondaryCoordinate]
#                     s1, s2 = sorted((s1, s2))
#                     if angle not in lines:
#                         lines[angle] = {}
#                     if p not in lines[angle]:
#                         lines[angle][p] = []
#                     lines[angle][p].append((s1, s2))
#             previous = point
#         # imply stems from curves by using BCP handles
#         previous = contour[-1]
#         for segment in contour:
#             if segment.type == "curve" and previous.type == "curve":
#                 bcp1 = _unwrapPoint(previous[1])
#                 bcp2 = _unwrapPoint(segment[-1])
#                 if bcp1[primaryCoordinate] == bcp2[primaryCoordinate]:
#                     angle = _calcAngle(bcp1, bcp2)
#                     p = bcp1[primaryCoordinate]
#                     s1 = bcp1[secondaryCoordinate]
#                     s2 = bcp2[secondaryCoordinate]
#                     s1, s2 = sorted((s1, s2))
#                     if angle not in lines:
#                         lines[angle] = {}
#                     if p not in lines[angle]:
#                         lines[angle][p] = []
#                     lines[angle][p].append((s1, s2))
#             previous = segment
#         contours[contourDirection].append((bounds, lines))
#     # single contours
#     for clockwise, directionContours in contours.items():
#         for contour in directionContours:
#             bounds, data = contour
#             for angle1, lineData1 in data.items():
#                 for angle2, lineData2 in data.items():
#                     if angle1 == angle2:
#                         continue
#                     if clockwise and angle1 == desiredClockwiseAngle:
#                         continue
#                     if not clockwise and angle1 == desiredCounterAngle:
#                         continue
#                     for p1, lines1 in lineData1.items():
#                         for p2, lines2 in lineData2.items():
#                             if p2 <= p1:
#                                 continue
#                             for s1a, s1b in lines1:
#                                 for s2a, s2b in lines2:
#                                     overlap = _linesOverlap(s1a, s1b, s2a, s2b)
#                                     if not overlap:
#                                         continue
#                                     w = p2 - p1
#                                     hits = []
#                                     for stem in targetStems:
#                                         if w == stem:
#                                             d = stem.diff(w)
#                                             if d:
#                                                 hits.append((d, stem.value, (s1a, s1b, s2a, s2b)))
#                                     if hits:
#                                         hit = min(hits)
#                                         w = hit[1]
#                                         s = hit[2]
#                                         stems.add((p1, p1 + w, s))
#     # double contours to test
#     for clockwiseContour in contours[True]:
#         clockwiseBounds = clockwiseContour[0]
#         for counterContour in contours[False]:
#             counterBounds = counterContour[0]
#             overlap = ftArrayTools.sectRect(clockwiseBounds, counterBounds)[0]
#             if not overlap:
#                 continue
#             clockwiseData = clockwiseContour[1]
#             counterData = counterContour[1]
#             for clockwiseAngle, clockwiseLineData in clockwiseContour[1].items():
#                 for counterAngle, counterLineData in counterContour[1].items():
#                     if clockwiseAngle == counterAngle:
#                         continue
#                     for clockwiseP, clockwiseLines in clockwiseLineData.items():
#                         for counterP, counterLines in counterLineData.items():
#                             for clockwiseSA, clockwiseSB in clockwiseLines:
#                                 for counterSA, counterSB in counterLines:
#                                     overlap = _linesOverlap(clockwiseSA, clockwiseSB, counterSA, counterSB)
#                                     if not overlap:
#                                         continue
#                                     w = abs(counterP - clockwiseP)
#                                     hits = []
#                                     for stem in targetStems:
#                                         if w == stem:
#                                             d = stem.diff(w)
#                                             if d:
#                                                 hits.append((d, stem.value, (clockwiseSA, clockwiseSB, counterSA, counterSB)))
#                                     if hits:
#                                         p = min((clockwiseP, counterP))
#                                         hit = min(hits)
#                                         w = hit[1]
#                                         s = hit[2]
#                                         stems.add((p, p + w, s))
#     # done
#     return stems
# 
# 
# class _StemWrapper(object):
# 
#     def __init__(self, value, threshold):
#         self.value = value
#         self.threshold = threshold
# 
#     def __cmp__(self, other):
#         d = abs(self.value - other)
#         if d <= self.threshold:
#             return 0
#         return cmp(self.value, other)
# 
#     def diff(self, other):
#         return abs(self.value - other)
# 
# 
# def _linesOverlap(a1, a2, b1, b2):
#     if a1 > b2 or a2 < b1:
#         return False
#     return True
# 
