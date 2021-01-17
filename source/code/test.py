import os
from defcon import Font
from glyphNanny.tests.segment import testForStraightLines

directory = os.getcwd()
for i in range(2):
    directory = os.path.dirname(directory)

path = os.path.join(directory, "test.ufo")
font = Font(path)
glyph = font["E"]

# contour = glyph[2]
# print(contour.getRepresentation("GlyphNanny.straightLines"))

contour = glyph[3]
print(contour.getRepresentation("GlyphNanny.pointsNearVerticalMetrics"))