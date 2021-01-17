from mojo import events
from tests.registry import testRegistry
from tests.tools import converBoundsToRect
from tests.wrappers import *

highlightStrokeWidth = 4
arrowSize = (15, 25)

class GlyphNannyEditorDisplayManager:

    def __init__(self, window=None):
        events.addObserver(self, "glyphWindowWillOpenCallback", "glyphWindowWillOpen")
        events.addObserver(self, "viewDidChangeGlyphCallback", "viewDidChangeGlyph")
        self.showTitles = True
        self.inactiveTests = []

        self.contourLevelTests = []
        self.segmentLevelTests = []
        self.pointLevelTests = []
        for testIdentifier, testData in testRegistry.items():
            level = testData["level"]
            if level == "contour":
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
        x, y, w, h = converBoundsToRect(contour.bounds)
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

    def updateLayers(self):
        for contour in self.glyph.contours:
            contourContainer = self.contourContainers[contour]
            for testIdentifier in self.contourContainerTestIdentifiers:
                testLayer = contourContainer.getSublayer(testIdentifier)
                representationName = testLayer.getInfoValue("representationName")
                representedValue = testLayer.getInfoValue("representedValue")
                newValue = contour.getRepresentation(representationName)
                if not newValue and not representedValue:
                    pass
                elif newValue != representedValue:
                    method = getattr(self, "visualize_" + testIdentifier)
                    testLayer.setInfoValue("representedValue", newValue)
                    method(testLayer, newValue)

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
            textProperties = self.getTextProperties()
            textProperties["fillColor"] = self.getColor("review")
            x1, y1 = pt1
            x2, y2 = pt2
            x = (x1 + x2) / 2
            y = (y1 + y2) / 2
            lineLayer.appendTextLineSublayer(
                text="Straighten Line",
                position=(x, y),
                **textProperties
            )

    def visualize_pointsNearVerticalMetrics(self, layer, data):
        layer.clearSublayers()
        for verticalMetric, points in data.items():
            for (x, y) in points:
                lineLayer = layer.appendLineSublayer(
                    startPoint=(x, y),
                    endPoint=(x, verticalMetric),
                    strokeWidth=highlightStrokeWidth,
                    strokeColor=self.getColor("review"),
                    endSymbol=dict(
                        name="triangle",
                        fillColor=self.getColor("review"),
                        size=arrowSize
                    )
                )


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
