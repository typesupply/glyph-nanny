import merz
from mojo import events
from tests.registry import testRegistry
from tests.tools import convertBoundsToRect, calculateMidpoint
from tests.wrappers import *

lineStrokeWidth = 1
highlightStrokeWidth = 4

class GlyphNannyEditorDisplayManager:

    def __init__(self, window=None):
        events.addObserver(self, "glyphWindowWillOpenCallback", "glyphWindowWillOpen")
        events.addObserver(self, "viewDidChangeGlyphCallback", "viewDidChangeGlyph")
        self.showTitles = True
        self.inactiveTests = []

        self.glyphInfoLevelTests = []
        self.glyphLevelTests = []
        self.contourLevelTests = []
        self.segmentLevelTests = []
        self.pointLevelTests = []
        for testIdentifier, testData in testRegistry.items():
            level = testData["level"]
            if level == "glyph":
                self.glyphLevelTests.append(testIdentifier)
            elif level == "contour":
                self.contourLevelTests.append(testIdentifier)
            elif level == "segment":
                self.segmentLevelTests.append(testIdentifier)
            elif level == "point":
                self.pointLevelTests.append(testIdentifier)

        self.contourContainers = {}
        self.contourContainerTestIdentifiers = (
            self.contourLevelTests
          + self.segmentLevelTests
          + self.pointLevelTests
        )

        if window is not None:
            self.buildContainer(window)
            self.setGlyph(wrapGlyph(window.getGlyph()))

    def destroy(self):
        self.container.clearSublayers()
        self.container.clearAnimation()
        events.removeObserver(self, "glyphWindowWillOpen")
        events.removeObserver(self, "viewDidChangeGlyph")
        self.stopObservingGlyph()

    # -----------------
    # App Notifications
    # -----------------

    def glyphWindowWillOpenCallback(self, notification):
        window = notification["window"]
        self.buildContainer(window)
        self.setGlyph(wrapGlyph(window.getGlyph()))

    def viewDidChangeGlyphCallback(self, notification):
        glyph = notification["glyph"]
        self.setGlyph(glyph)

    # -----
    # Glyph
    # -----

    glyph = None

    def setGlyph(self, glyph):
        self.stopObservingGlyph()
        self.glyph = glyph
        self.destroyContourContainers()
        self.buildContourContainers()
        self.updateLayers()
        self.startObservingGlyph()

    glyphObservations = (
        "Glyph.Changed",
        "Glyph.ContourWillBeAdded",
        "Glyph.ContourWillBeDeleted"
    )

    def _makeObservationCallbackName(self, notification):
        name = notification.replace(".", "")
        name = name[0].lower() + name[1:]
        name += "Callback"
        return name

    def startObservingGlyph(self):
        if self.glyph is None:
            return
        for notification in self.glyphObservations:
            self.glyph.addObserver(
                self,
                self._makeObservationCallbackName(notification),
                notification
            )

    def stopObservingGlyph(self):
        if self.glyph is None:
            return
        for notification in self.glyphObservations:
            self.glyph.removeObserver(
                self,
                notification
            )

    def glyphChangedCallback(self, notification):
        self.updateLayers()

    def glyphContourWillBeAddedCallback(self, notification):
        contour = notification.data["object"]
        contour = wrapContour(contour)
        self.buildContourContainer(contour)

    def glyphContourWillBeDeletedCallback(self, notification):
        contour = notification.data["object"]
        contour = wrapContour(contour)
        self.destroyContourContainer(contour)

    # ----------------
    # Layer Management
    # ----------------

    def buildContainer(self, window):
        self.container = window.extensionContainer(
            "com.typesupply.GlyphNanny",
            location="background",
            clear=True
        )
        self.buildGlyphContainers()

    def buildGlyphContainers(self):
        """
        Build all necessary glyph containers.
        """
        for testIdentifier in self.glyphLevelTests:
            testData = testRegistry[testIdentifier]
            layer = self.container.appendBaseSublayer(
                name=testIdentifier
            )
            layer.setInfoValue("representationName", testData["representationName"])
            layer.setInfoValue("representedValue", None)

    def buildContourContainers(self):
        """
        Build all necessary contour containers.
        """
        if self.glyph is None:
            return
        if not self.glyph.contours:
            return
        with self.container.sublayerGroup():
            for contour in self.glyph.contours:
                self.buildContourContainer(contour)

    def destroyContourContainers(self):
        """
        Destroy all contour containers.
        """
        contours = list(self.contourContainers.keys())
        for contour in contours:
            self.destroyContourContainer(contour)

    def buildContourContainer(self, contour):
        """
        Build contour container for a specific contour.
        """
        contourContainer = self.contourContainers[contour] = self.container.appendBaseSublayer()
        for testIdentifier in self.contourContainerTestIdentifiers:
            testData = testRegistry[testIdentifier]
            layer = contourContainer.appendBaseSublayer(
                name=testIdentifier
            )
            layer.setInfoValue("representationName", testData["representationName"])
            layer.setInfoValue("representedValue", None)

    def destroyContourContainer(self, contour):
        """
        Destroy contour container for a specific contour.
        """
        contourContainer = self.contourContainers[contour]
        self.container.removeSublayer(contourContainer)
        del self.contourContainers[contour]

    def updateLayers(self, forceUpdate=False):
        for testIdentifier in self.glyphLevelTests:
            testLayer = self.container.getSublayer(testIdentifier)
            self._updateLayer(testLayer, self.glyph, testIdentifier, forceUpdate)
        for contour in self.glyph.contours:
            contourContainer = self.contourContainers[contour]
            for testIdentifier in self.contourContainerTestIdentifiers:
                testLayer = contourContainer.getSublayer(testIdentifier)
                self._updateLayer(testLayer, contour, testIdentifier, forceUpdate)

    def _updateLayer(self, layer, obj, testIdentifier, forceUpdate):
        representationName = layer.getInfoValue("representationName")
        representedValue = layer.getInfoValue("representedValue")
        newValue = obj.getRepresentation(representationName)
        needsUpdate = False
        if forceUpdate:
            needsUpdate = True
        elif newValue != representedValue:
            if not newValue and not representedValue:
                pass
            else:
                needsUpdate = True
        if needsUpdate:
            layer.setInfoValue("representedValue", newValue)
            methodName = "visualize_" + testIdentifier
            if not hasattr(self, methodName):
                print("missing method:", methodName)
            else:
                method = getattr(self, methodName)
                method(layer, newValue)

    # -------------
    # Visualization
    # -------------

    def getColor(self, color):
        replacements = dict(
            background=(1, 1, 1, 1),
            inform=(0, 0, 0.7, 0.3),
            review=(1, 0.7, 0, 0.7),
            remove=(1, 0, 0, 0.5),
            insert=(0, 1, 0, 0.75)
        )
        return replacements[color]

    def getTextProperties(self):
        properties = dict(
            font="system",
            weight="medium",
            pointSize=10,
            horizontalAlignment="center",
            verticalAlignment="center",
            fillColor=(0, 0, 0, 1),
            backgroundColor=self.getColor("background"),
            cornerRadius=5,
            padding=(10, 2)
        )
        return properties

    def getArrowSymbolSettings(self):
        settings = dict(
            name="GlyphNanny.editorArrow",
            size=(30, 20),
            strokeColor=self.getColor("review"),
            strokeWidth=1
        )
        return settings

    def getRemoveSymbolSettings(self):
        settings = dict(
            name="GlyphNanny.editorRemove",
            size=(17, 17),
            strokeColor=self.getColor("remove"),
            strokeWidth=1
        )
        return settings

    # Glyph
    # -----

    def visualize_duplicateContours(self, layer, data):
        layer.clearSublayers()
        if data:
            for contourIndex in data:
                contour = self.glyph[contourIndex]
                path = contour.getRepresentation("merz.CGPath")
                pathLayer = layer.appendPathSublayer(
                    path=path,
                    fillColor=None,
                    strokeColor=self.getColor("remove"),
                    strokeWidth=highlightStrokeWidth
                )
                textProperties = self.getTextProperties()
                textProperties["fillColor"] = self.getColor("remove")
                textProperties["verticalAlignment"] = "top"
                xMin, yMin, xMax, yMax = contour.bounds
                x, y = calculateMidpoint((xMin, yMin), (xMax, yMax))
                pathLayer.appendTextLineSublayer(
                    text="Duplicate Contour",
                    position=(x, yMin),
                    **textProperties
                )

    # Contour
    # -------

    def visualize_openContour(self, layer, data):
        layer.clearSublayers()
        if data:
            arrowSymbolSettings = self.getArrowSymbolSettings()
            arrowSymbolSettings["strokeColor"] = self.getColor("insert")
            pt1, pt2 = data
            lineLayer = layer.appendLineSublayer(
                startPoint=pt1,
                endPoint=pt2,
                strokeWidth=lineStrokeWidth,
                strokeColor=self.getColor("insert"),
                startSymbol=arrowSymbolSettings
            )
            if self.showTitles:
                textProperties = self.getTextProperties()
                textProperties["fillColor"] = self.getColor("insert")
                x, y = calculateMidpoint(pt1, pt2)
                lineLayer.appendTextLineSublayer(
                    text="Open Contour",
                    position=(x, y),
                    **textProperties
                )

    # Segment
    # -------

    def visualize_straightLines(self, layer, data):
        layer.clearSublayers()
        for pt1, pt2 in data:
            lineLayer = layer.appendLineSublayer(
                startPoint=pt1,
                endPoint=pt2,
                strokeWidth=highlightStrokeWidth,
                strokeColor=self.getColor("review")
            )
            if self.showTitles:
                textProperties = self.getTextProperties()
                textProperties["fillColor"] = self.getColor("review")
                x, y = calculateMidpoint(pt1, pt2)
                lineLayer.appendTextLineSublayer(
                    text="Slight Angle",
                    position=(x, y),
                    **textProperties
                )

    def visualize_pointsNearVerticalMetrics(self, layer, data):
        layer.clearSublayers()
        arrowSymbolSettings = self.getArrowSymbolSettings()
        for verticalMetric, points in data.items():
            for (x, y) in points:
                lineLayer = layer.appendLineSublayer(
                    startPoint=(x, y),
                    endPoint=(x, verticalMetric),
                    strokeWidth=highlightStrokeWidth,
                    strokeColor=self.getColor("review"),
                    endSymbol=arrowSymbolSettings
                )

    def visualize_unsmoothSmooths(self, layer, data):
        layer.clearSublayers()
        for pt1, pt2, pt3 in data:
            pathLayer = layer.appendPathSublayer(
                fillColor=None,
                strokeWidth=highlightStrokeWidth,
                strokeColor=self.getColor("review")
            )
            pen = pathLayer.getPen()
            pen.moveTo(pt1)
            pen.lineTo(pt2)
            pen.lineTo(pt3)
            pen.endPath()
            if self.showTitles:
                textProperties = self.getTextProperties()
                textProperties["fillColor"] = self.getColor("review")
                x, y = calculateMidpoint(pt1, pt3)
                pathLayer.appendTextLineSublayer(
                    text="Unsmooth Smooth",
                    position=(x, y),
                    **textProperties
                )

    def visualize_complexCurves(self, layer, data):
        layer.clearSublayers()
        for pt1, pt2, pt3, pt4 in data:
            pathLayer = layer.appendPathSublayer(
                fillColor=None,
                strokeWidth=highlightStrokeWidth,
                strokeColor=self.getColor("review")
            )
            pen = pathLayer.getPen()
            pen.moveTo(pt1)
            pen.curveTo(pt2, pt3, pt4)
            pen.endPath()
            if self.showTitles:
                textProperties = self.getTextProperties()
                textProperties["fillColor"] = self.getColor("review")
                x, y = calculateMidpoint(pt1, pt4)
                pathLayer.appendTextLineSublayer(
                    text="Complex Curve",
                    position=(x, y),
                    **textProperties
                )

    def visualize_crossedHandles(self, layer, data):
        layer.clearSublayers()
        for handleData in data:
            pt1, pt2, pt3, pt4 = handleData["points"]
            pt5 = handleData["intersection"]
            pathLayer = layer.appendPathSublayer(
                fillColor=None,
                strokeWidth=highlightStrokeWidth,
                strokeColor=self.getColor("review")
            )
            pen = pathLayer.getPen()
            pen.moveTo(pt1)
            pen.lineTo(pt2)
            pen.endPath()
            pen.moveTo(pt3)
            pen.lineTo(pt4)
            pen.endPath()
            pathLayer.appendSymbolSublayer(
                position=pt5,
                size=(10, 10),
                imageSettings=dict(
                    name="oval",
                    size=(10, 10),
                    fillColor=self.getColor("review")
                )
            )
            if self.showTitles:
                textProperties = self.getTextProperties()
                textProperties["fillColor"] = self.getColor("review")
                x, y = calculateMidpoint(pt1, pt4)
                pathLayer.appendTextLineSublayer(
                    text="Crossed Handles",
                    position=(x, y),
                    **textProperties
                )

    def visualize_unnecessaryHandles(self, layer, data):
        layer.clearSublayers()
        symbolSettings = self.getRemoveSymbolSettings()
        for pt1, pt2 in data:
            lineLayer = layer.appendLineSublayer(
                startPoint=pt1,
                endPoint=pt2,
                strokeWidth=highlightStrokeWidth,
                strokeColor=self.getColor("remove"),
                startSymbol=symbolSettings,
                endSymbol=symbolSettings
            )
            if self.showTitles:
                textProperties = self.getTextProperties()
                textProperties["fillColor"] = self.getColor("remove")
                x, y = calculateMidpoint(pt1, pt2)
                lineLayer.appendTextLineSublayer(
                    text="Unnecessary Handles",
                    position=(x, y),
                    **textProperties
                )

    def visualize_unevenHandles(self, layer, data):
        layer.clearSublayers()
        for off1, off2, shape1, shape2 in data:
            pathLayer = layer.appendPathSublayer(
                fillColor=self.getColor("review")
            )
            pen = pathLayer.getPen()
            for shape in (shape1, shape2):
                pen.moveTo(shape[-1])
                for curve in shape[:-2]:
                    pt1, pt2, pt3 = curve
                    pen.curveTo(pt1, pt2, pt3)
                pen.lineTo(shape[-2])
                pen.lineTo(shape[-1])
                pen.endPath()
            if self.showTitles:
                textProperties = self.getTextProperties()
                textProperties["fillColor"] = self.getColor("review")
                x, y = calculateMidpoint(off1, off2)
                pathLayer.appendTextLineSublayer(
                    text="Uneven Handles",
                    position=(x, y),
                    **textProperties
                )

# -------
# Symbols
# -------

from merz.tools.drawingTools import NSImageDrawingTools

def editorRemoveSymbolFactory(size, strokeColor, strokeWidth):
    width, height = size
    bot = NSImageDrawingTools((width, height))
    pen = bot.BezierPath()
    pen.moveTo((0, 0))
    pen.lineTo((width, height))
    pen.endPath()
    pen.moveTo((0, height))
    pen.lineTo((width, 0))
    pen.endPath()
    bot.stroke(*strokeColor)
    bot.strokeWidth(strokeWidth)
    bot.drawPath(pen)
    return bot.getImage()

merz.SymbolImageVendor.registerImageFactory("GlyphNanny.editorRemove", editorRemoveSymbolFactory)

def editorArrowSymbolFactory(size, strokeColor, strokeWidth):
    width, height = size
    xCenter = width / 2
    yCenter = height / 2
    bot = NSImageDrawingTools((width, height))
    pen = bot.BezierPath()
    pen.moveTo((0, 0))
    pen.lineTo((xCenter, yCenter))
    pen.lineTo((0, height))
    pen.endPath()
    bot.stroke(*strokeColor)
    bot.strokeWidth(strokeWidth)
    bot.drawPath(pen)
    return bot.getImage()

merz.SymbolImageVendor.registerImageFactory("GlyphNanny.editorArrow", editorArrowSymbolFactory)

# ----
# Test
# ----

import vanilla
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.UI import CurrentGlyphWindow

class Test(BaseWindowController):

    def __init__(self):
        self.manager = GlyphNannyEditorDisplayManager(CurrentGlyphWindow())
        self.w = vanilla.FloatingWindow((200, 200))
        self.setUpBaseWindowBehavior()
        self.w.open()

    def windowCloseCallback(self, sender):
        self.manager.destroy()


if __name__ == "__main__":
    Test()
