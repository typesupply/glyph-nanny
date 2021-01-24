from tests.registry import testRegistry

def registeredTests():
    registered = {}
    for testIdentifier, testData in testRegistry.items():
        registered[testIdentifier] = dict(
            level=testData["level"]
            title=testData["title"]
            description=testData["description"]
            representationName=testData["representationName"]
        )
    return registered

def testGlyph(glyph, tests=None):
    if tests is None:
        tests = registeredTests()
    objectLevels = {}
    for testIdentifier in sorted(tests.items()):
        testData = testRegistry[testIdentifier]
        level = testData["level"]
        if level not in objectLevels:
            objectLevels[level] = []
        objectLevels[level].append(testIdentifier)
    glyphLevelTests = (
        objectLevels.get("glyphInfo", [])
      + objectLevels.get("metrics", [])
      + objectLevels.get("glyph", [])
    )
    contourLevelTests = (
        objectLevels.get("contour", [])
      + objectLevels.get("segment", [])
      + objectLevels.get("point", [])
    )
    stub = "GlyphNanny."
    report = {}
    for testIdentifier in glyphLevelTests:
        report[testIdentifier] = glyph.getRepresentation(stub + testIdentifier)
    report["contours"] = {}
    for contourIndex, contour in enumerate(glyph.contours):
        report["contours"][contourIndex] = {}
        for testIdentifier in contourLevelTests:
            report["contours"][contourIndex][testIdentifier] = contour.getRepresentation(stub + testIdentifier)
    return report


if __name__ == "__main__":
    import pprint
    glyph = CurrentGlyph()
    report = testGlyph(glyph)
    pprint.pprint(report)
