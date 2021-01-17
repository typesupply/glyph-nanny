from mojo import events
from tests.registry import testRegistry

highlightStrokeWidth = 4

class GlyphNannyEditorDisplayManager:

    def __init__(self, window=None):
        self.testLayerDefaultProperties = dict(
            straightLines=dict(
                fillColor=None,
                strokeColor="colorReview",
                strokeWidth=highlightStrokeWidth
            ),
            pointsNearVerticalMetrics=dict(
                fillColor=None,
                strokeColor="colorReview",
                strokeWidth=highlightStrokeWidth * 5
                # XXX end triangle once Path can handle > 1 subpaths
            )
        )
        self.loadDefaultLayerProperties()
        self.testContainers = {}
        events.addObserver(self, "glyphWindowWillOpenCallback", "glyphWindowWillOpen")
        events.addObserver(self, "viewDidChangeGlyphCallback", "viewDidChangeGlyph")
        if window is not None:
            self.buildContainer(window)

    def destroy(self):
        self.backgroundContainer.clearSublayers()
        self.backgroundContainer.clearAnimation()
        events.removeObserver(self, "glyphWindowWillOpen")
        events.removeObserver(self, "viewDidChangeGlyph")
        self.stopObservingGlyph()

    # -----------------
    # App Notifications
    # -----------------

    def glyphWindowWillOpenCallback(self, notification):
        window = notification["window"]
        self.build(window)

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
        self.buildGlyphLayers()
        self.startObservingGlyph()

    glyphObservations = (
        "Glyph.ContoursChanged",
        "Glyph.ComponentsChanged"
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

    def glyphContoursChangedCallback(self, notification):
        self.updateLayers()

    def glyphComponentsChangedCallback(self, notification):
        self.updateLayers()

    # -----
    # Build
    # -----

    def loadDefaultLayerProperties(self):
        # XXX these need to be loaded from user defaults
        replacements = dict(
            colorInform=(0, 0, 0.7, 0.3),
            colorReview=(1, 0.7, 0, 0.7),
            colorRemove=(1, 0, 0, 0.5),
            colorInsert=(0, 1, 0, 0.75)
        )
        replacableProperties = [
            "backgroundColor",
            "borderColor",
            "fillColor",
            "strokeColor"
        ]
        self.testLayerProperties = {}
        for testIdentifier, defaults in self.testLayerDefaultProperties.items():
            updated = dict(defaults)
            for property in replacableProperties:
                if property in updated:
                    value = updated[property]
                    updated[property] = replacements.get(value, value)
            self.testLayerProperties[testIdentifier] = updated

    def getTestLayerProperties(self, testIdentifier):
        return self.testLayerProperties[testIdentifier]

    def buildContainer(self, window):
        self.backgroundContainer = window.extensionContainer(
            "com.typesupply.GlyphNanny",
            location="background",
            clear=True
        )
        self.buildSegmentTestContainers()

    def buildSegmentTestContainers(self):
        for testIdentifier, testData in testRegistry.items():
            layer = self.testContainers[testIdentifier] = self.backgroundContainer.appendBaseSublayer(
                name=testIdentifier,
                position=(0, 0),
                size=("width", "height"),
                backgroundColor=(1, 1, 0, 1)
            )
            layer.setInfoValue("representationName", testData["representationName"])
            layer.appendTextLineSublayer(
                fillColor=(1, 0, 0, 0.25),
                text=testIdentifier,
                horizontalAlignment="center",
                verticalAlignment="center",
                pointSize=20
            )

    def buildGlyphLayers(self):
        self.contourLayers = {}
        for contourIndex, contour in enumerate(self.glyph):
            self.contourLayers[contour] = []
            for testIdentifier, container in self.testContainers.items():
                properties = self.testLayerProperties[testIdentifier]
                layer = container.appendPathSublayer(
                    name=testIdentifier + str(contourIndex),
                    **properties
                )
                layer.setInfoValue("representationName", container.getInfoValue("representationName"))
                layer.setInfoValue("testIdentifier", testIdentifier)
                layer.setInfoValue("testData", None)
                self.contourLayers[contour].append(layer)
        self.updateLayers()

    def updateLayers(self):
        # Contours
        for contour, contourLayers in self.contourLayers.items():
            for contourLayer in contourLayers:
                representationName = contourLayer.getInfoValue("representationName")
                existingData = contourLayer.getInfoValue("testData")
                data = contour.getRepresentation(representationName)
                if not existingData and not data:
                    continue
                if data != existingData:
                    testIdentifier = contourLayer.getInfoValue("testIdentifier")
                    method = getattr(self, "visualize_" + testIdentifier)
                    method(contourLayer, contour, existingData, data)
                    contourLayer.setInfoValue("testData", data)

    # ---------
    # Visualize
    # ---------

    # Segments

    def visualize_straightLines(self, contourLayer, contour, existingData, data):
        with contourLayer.propertyGroup():
            if data:
                pen = contourLayer.getPen()
                for pt1, pt2 in data:
                    pen.moveTo(pt1)
                    pen.lineTo(pt2)
                    pen.endPath()
            else:
                contourLayer.setPath(None)

    def visualize_pointsNearVerticalMetrics(self, contourLayer, contour, existingData, data):
        with contourLayer.propertyGroup():
            if data:
                pen = contourLayer.getPen()
                for verticalMetric, points in data.items():
                    for (x, y) in points:
                        pen.moveTo((x, y))
                        pen.lineTo((x, verticalMetric))
                        pen.endPath()
            else:
                contourLayer.setPath(None)

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
