"""
These functions convert the incoming
objects to fontParts objects if necessary.
"""

from fontParts.world import dispatcher

__all__ = (
    "RFont",
    "RGlyph",
    "RContour"
)


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