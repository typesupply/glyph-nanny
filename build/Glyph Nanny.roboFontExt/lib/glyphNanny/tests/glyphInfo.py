import re
from fontTools.agl import AGL2UV
import defcon
from . import registry
from .wrappers import *

# Unicode Value

uniNamePattern = re.compile(
    "uni"
    "([0-9A-Fa-f]{4})"
    "$"
)

def testUnicodeValue(glyph):
    """
    A Unicode value should appear only once per font.
    """
    font = wrapFont(glyph.font)
    layer = font.getLayer(glyph.layer.name)
    glyph = layer[glyph.name]
    report = []
    uni = glyph.unicode
    name = glyph.name
    # test for uniXXXX name
    m = uniNamePattern.match(name)
    if m is not None:
        uniFromName = m.group(1)
        uniFromName = int(uniFromName, 16)
        if uni != uniFromName:
            report.append("The Unicode value for this glyph does not match its name.")
    # test against AGLFN
    else:
        expectedUni = AGL2UV.get(name)
        if expectedUni != uni:
            report.append("The Unicode value for this glyph may not be correct.")
    # look for duplicates
    if uni is not None:
        duplicates = []
        for name in sorted(font.keys()):
            if name == glyph.name:
                continue
            other = font[name]
            if other.unicode == uni:
                duplicates.append(name)
        if duplicates:
            report.append("The Unicode for this glyph is also used by: %s." % " ".join(duplicates))
    return report

registry.registerTest(
    identifier="unicodeValue",
    level="glyphInfo",
    title="Unicode Value",
    description="Unicode value may have problems.",
    testFunction=testUnicodeValue,
    defconClass=defcon.Glyph,
    destructiveNotifications=["Glyph.UnicodesChanged"]
)