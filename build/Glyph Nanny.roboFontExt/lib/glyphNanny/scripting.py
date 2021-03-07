import re
from .tests.registry import testRegistry

def registeredTests():
    registered = {}
    for testIdentifier, testData in testRegistry.items():
        registered[testIdentifier] = dict(
            level=testData["level"],
            title=testData["title"],
            description=testData["description"],
            representationName=testData["representationName"]
        )
    return registered

def testFont(
        font,
        tests=None,
        ignoreOverlap=False,
        progressBar=None
    ):
    if tests is None:
        tests = registeredTests().keys()
    layer = font.defaultLayer
    return testLayer(
        layer,
        tests=tests,
        ignoreOverlap=ignoreOverlap,
        progressBar=progressBar
    )

def testLayer(
        layer,
        tests=None,
        ignoreOverlap=False,
        progressBar=None
    ):
    if tests is None:
        tests = registeredTests().keys()
    font = layer.font
    if font is not None:
        glyphOrder = font.glyphOrder
    else:
        glyphOrder = sorted(layer.keys())
    report = {}
    for name in glyphOrder:
        if progressBar is not None:
            progressBar.update("Analyzing %s..." % name)
        glyph = layer[name]
        glyphReport = testGlyph(glyph, tests=tests)
        report[name] = glyphReport
    return report

def testGlyph(glyph, tests=None):
    if tests is None:
        tests = registeredTests().keys()
    objectLevels = {}
    for testIdentifier in sorted(tests):
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
    for contourIndex, contour in enumerate(glyph.contours):
        for testIdentifier in contourLevelTests:
            key = f"contour{contourIndex}: {testIdentifier}"
            report[key] = contour.getRepresentation(stub + testIdentifier)
    return report

# --------------
# Report Purging
# --------------

def purgeGlyphReport(report):
    purged = {}
    for key, value in report.items():
        if isinstance(value, dict):
            value = purgeDict(value)
        if not value:
            continue
        purged[key] = value
    return purged

def purgeDict(d):
    purged = {}
    for k, v in d.items():
        if not v:
            continue
        purged[k] = v
    return purged

# ----------
# Formatting
# ----------

def formatFontReport(report):
    return formatLayerReport(report)

def formatLayerReport(report):
    lines = []
    for glyphName, glyphReport in report.items():
        glyphReport = formatGlyphReport(glyphReport)
        if not glyphReport:
            continue
        lines.append("# " + glyphName)
        lines.append("\n")
        lines.append(glyphReport)
        lines.append("\n")
    return "\n".join(lines).strip()

contourTitle_RE = re.compile(r"contour([\d])+:")

def formatGlyphReport(report):
    report = purgeGlyphReport(report)
    notContours = {}
    contours = {}
    for key, value in report.items():
        m = contourTitle_RE.match(key)
        if m:
            contourIndex = m.group(1)
            if contourIndex not in contours:
                contours[contourIndex] = {}
            key = key.split(":", 1)[-1].strip()
            contours[contourIndex][key] = value
        else:
            notContours[key] = value
    lines = []
    for key, value in sorted(notContours.items()):
        title = testRegistry[key]["title"]
        lines.append("## " + title)
        lines.append(formatValue(value))
        lines.append("")
    for contourIndex, contourReport in sorted(contours.items()):
        for key, value in sorted(notContours.items()):
            title = testRegistry[key]["title"]
            lines.append("## {title}: Contour {contourIndex}".format(title=title, contourIndex=contourIndex))
            lines.append(formatValue(value))
            lines.append("")
    return "\n".join(lines).strip()

def formatValue(value):
    if isinstance(value, str):
        return value
    elif isinstance(value, list):
        l = []
        for i in value:
            l.append("- " + formatValue(i))
        return "\n".join(l)
    elif isinstance(value, dict):
        l = []
        for k, v in sorted(value.items()):
            l.append("- {key}: {value}".format(key=k, value=format(v)))
        return "\n".join(l)
    return repr(value)
