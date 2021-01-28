import merz
from mojo import events
from mojo.UI import getDefault
from . import defaults
from .tests.registry import testRegistry
from .tests.tools import (
    convertBoundsToRect,
    calculateMidpoint
)
from .tests.wrappers import *

class TemporaryManagerSpawner:

    # XXX this will be replaced by something in mojo

    def __init__(self):
        deadObservations = events.findObservations(
            identifier="com.typesupply.GlyphNanny2.*"
        )
        for observation in deadObservations:
            observer = observation["observer"]
            notification = observation["notification"]
            events.removeObserver(observer, notification)
        events.addObserver(
            self,
            "glyphWindowWillOpenCallback",
            "glyphWindowWillOpen",
            identifier="com.typesupply.GlyphNanny2.TemporaryManagerSpawner.glyphWindowWillOpen"
        )
        events.addObserver(
            self,
            "glyphWindowWillCloseCallback",
            "glyphWindowWillClose",
            identifier="com.typesupply.GlyphNanny2.TemporaryManagerSpawner.glyphWindowWillClose"
        )
        events.addObserver(
            self,
            "viewDidChangeGlyphCallback",
            "viewDidChangeGlyph",
            identifier="com.typesupply.GlyphNanny2.TemporaryManagerSpawner.viewDidChangeGlyph"
        )
        events.addObserver(
            self,
            "didUndoCallback",
            "didUndo",
            identifier="com.typesupply.GlyphNanny2.TemporaryManagerSpawner.didUndo"
        )
        self.windows = {}

    def destroy(self):
        events.removeObserver(self, "glyphWindowWillOpen")
        events.removeObserver(self, "glyphWindowWillClose")
        events.removeObserver(self, "viewDidChangeGlyph")
        events.removeObserver(self, "didUndo")

    def glyphWindowWillOpenCallback(self, notification):
        window = notification["window"]
        obj = GlyphNannyEditorDisplayManager(window)
        self.windows[window] = obj
        glyph = window.getGlyph()
        if glyph is not None:
            glyph = wrapGlyph(glyph)
        obj.setGlyph(glyph)

    def glyphWindowWillCloseCallback(self, notification):
        window = notification["window"]
        obj = self.windows.pop(window)
        obj.windowClosed()

    def viewDidChangeGlyphCallback(self, notification):
        view = notification["view"]
        glyph = notification["glyph"]
        if glyph is not None:
            glyph = wrapGlyph(glyph)
        for window, obj in self.windows.items():
            if window.getGlyphView() == view:
                obj.setGlyph(glyph)
                break

    def didUndoCallback(self, notification):
        view = notification["view"]
        glyph = notification["glyph"]
        if glyph is not None:
            glyph = wrapGlyph(glyph)
        for window, obj in self.windows.items():
            if window.getGlyphView() == view:
                obj.updateLayers()
                break

class GlyphNannyEditorDisplayManager:

    def __init__(self, window):
        events.addObserver(self, "preferencesChangedCallback", "preferencesChanged")
        self.loadUserDefaults()
        self.inactiveTests = set()

        self.glyphInfoLevelTests = []
        self.metricsLevelTests = []
        self.glyphLevelTests = []
        self.contourLevelTests = []
        self.segmentLevelTests = []
        self.pointLevelTests = []
        for testIdentifier, testData in testRegistry.items():
            level = testData["level"]
            if level == "glyphInfo":
                self.glyphInfoLevelTests.append(testIdentifier)
            elif level == "metrics":
                self.metricsLevelTests.append(testIdentifier)
            elif level == "glyph":
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
        self.buildContainer(window)

    def windowClosed(self):
        events.removeObserver(self, "preferencesChanged")
        self.container.clearSublayers()
        self.container.clearAnimation()
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

    def preferencesChangedCallback(self, notification):
        self.loadUserDefaults()
        self.updateLayers(forceUpdate=True)

    # -------------
    # User Defaults
    # -------------

    def loadUserDefaults(self):
        self.showReport = defaults.getDisplayLiveReport()
        self.colorBackground = getDefault("glyphViewBackgroundColor")
        self.colorReview = defaults.getColorReview()
        self.colorRemove = defaults.getColorRemove()
        self.colorInsert = defaults.getColorInsert()
        self.colorInform = defaults.getColorInform()
        self.lineWidthRegular = defaults.getLineWidthRegular()
        self.lineWidthHighlight = defaults.getLineWidthHighlight()
        self.showTitles = defaults.getDisplayTitles()
        self.textFont = defaults.getTextFont()
        self.inactiveTests = set()
        for testIdentifier in testRegistry.keys():
            state = defaults.getTestState(testIdentifier)
            if not state:
                self.inactiveTests.add(testIdentifier)

    # -----
    # Glyph
    # -----

    glyph = None

    def setGlyph(self, glyph):
        if glyph == self.glyph:
            return
        self.stopObservingGlyph()
        self.destroyContourContainers()
        self.glyph = glyph
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
        self.glyph.removeObserver(self, None)

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
        # contours
        for testIdentifier in self.glyphLevelTests:
            testData = testRegistry[testIdentifier]
            layer = self.container.appendBaseSublayer(
                name=testIdentifier
            )
            layer.setInfoValue("representationName", testData["representationName"])
            layer.setInfoValue("representedValue", None)
        # info
        textProperties = self.getTextProperties()
        textProperties["fillColor"] = self.colorInform
        textProperties["horizontalAlignment"] = "left"
        textProperties["verticalAlignment"] = "top"
        layer = self.container.appendTextLineSublayer(
            name="glyphInfo",
            position=(30, -50),
            **textProperties
        )
        layer.setInfoValue("representedValue", None)
        # metrics
        layer = self.container.appendTextLineSublayer(
            name="metrics",
            position=(30, -10),
            **textProperties
        )
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
        contourContainer = self.contourContainers[contour] = self.container.appendBaseSublayer(
            name="contour.%s" % id(contour.naked())
        )
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
        # during cut, the contour can come
        # through here > 1 times, so return
        # if the contour is unknown.
        if contour not in self.contourContainers:
            return
        contourContainer = self.contourContainers.pop(contour)
        self.container.removeSublayer(contourContainer)

    def updateLayers(self, forceUpdate=False):
        # if the contour containers don't match,
        # the mismatched containers need to be
        # torn down or built. this happens after
        # undo/redo.
        if self.glyph is not None:
            containerContours = set(self.contourContainers.keys())
            glyphContours = set((contour for contour in self.glyph))
            for contour in containerContours - glyphContours:
                self.destroyContourContainer(contour)
            for contour in glyphContours - containerContours:
                self.buildContourContainer(contour)
        # info
        self._updateGlyphInfoLayer()
        # metrics
        self._updateMetricsLayer()
        # glyph
        for testIdentifier in self.glyphLevelTests:
            testLayer = self.container.getSublayer(testIdentifier)
            if self.glyph is None:
                testLayer.clearSublayers()
                continue
            self._updateLayer(testLayer, self.glyph, testIdentifier, forceUpdate)
        # contour, segment, points
        if self.glyph is not None:
            for contour in self.glyph.contours:
                contourContainer = self.contourContainers[contour]
                for testIdentifier in self.contourContainerTestIdentifiers:
                    testLayer = contourContainer.getSublayer(testIdentifier)
                    self._updateLayer(testLayer, contour, testIdentifier, forceUpdate)

    def _updateGlyphInfoLayer(self):
        layer = self.container.getSublayer("glyphInfo")
        if self.glyph is None or not self.showReport:
            layer.clearSublayers()
            return
        glyphInfoData = {}
        for testIdentifier in self.glyphInfoLevelTests:
            if testIdentifier in self.inactiveTests:
                continue
            representationName = testRegistry[testIdentifier]["representationName"]
            glyphInfoData[testIdentifier] = self.glyph.getRepresentation(representationName)
        representedValue = layer.getInfoValue("representedValue")
        if glyphInfoData != representedValue:
            layer.setInfoValue("representedValue", glyphInfoData)
            text = []
            for key, value in sorted(glyphInfoData.items()):
                text += value
            text = "\n".join(text)
            layer.setText(text)

    def _updateMetricsLayer(self):
        layer = self.container.getSublayer("metrics")
        if self.glyph is None or not self.showReport:
            layer.clearSublayers()
            return
        metricsData = {}
        for testIdentifier in self.metricsLevelTests:
            if testIdentifier in self.inactiveTests:
                continue
            representationName = testRegistry[testIdentifier]["representationName"]
            metricsData[testIdentifier] = self.glyph.getRepresentation(representationName)
        representedValue = layer.getInfoValue("representedValue")
        if metricsData != representedValue:
            layer.clearSublayers()
            layer.setInfoValue("representedValue", metricsData)
            arrowSettings = self.getArrowSymbolSettings()
            arrowSettings["strokeColor"] = self.colorReview
            y = 0
            offset = -20
            for testIdentifier, data in sorted(metricsData.items()):
                if not data:
                    continue
                if testIdentifier == "metricsSymmetry":
                    left = data["left"]
                    right = data["right"]
                    width = data["width"]
                    message = data["message"]
                    layer.appendLineSublayer(
                        startPoint=(0, y),
                        endPoint=(width, y),
                        strokeColor=self.colorReview,
                        strokeWidth=self.lineWidthRegular,
                        startSymbol=arrowSettings,
                        endSymbol=arrowSettings
                    )
                    textProperties = self.getTextProperties()
                    textProperties["fillColor"] = self.colorReview
                    textProperties["horizontalAlignment"] = "center"
                    layer.appendTextLineSublayer(
                        position=(width / 2, y),
                        text=message,
                        **textProperties
                    )
                    y += offset
                else:
                    left = data["left"]
                    right = data["right"]
                    width = data["width"]
                    leftMessage = data["leftMessage"]
                    rightMessage = data["rightMessage"]
                    if leftMessage:
                        layer.appendLineSublayer(
                            startPoint=(0, y),
                            endPoint=(left, y),
                            strokeColor=self.colorReview,
                            strokeWidth=self.lineWidthRegular,
                            startSymbol=arrowSettings
                        )
                        textProperties = self.getTextProperties()
                        textProperties["fillColor"] = self.colorReview
                        textProperties["horizontalAlignment"] = "left"
                        layer.appendTextLineSublayer(
                            position=(left, y),
                            text=leftMessage,
                            **textProperties
                        )
                    if rightMessage:
                        layer.appendLineSublayer(
                            startPoint=(right, y),
                            endPoint=(width, y),
                            strokeColor=self.colorReview,
                            strokeWidth=self.lineWidthRegular,
                            endSymbol=arrowSettings
                        )
                        textProperties = self.getTextProperties()
                        textProperties["fillColor"] = self.colorReview
                        textProperties["horizontalAlignment"] = "right"
                        layer.appendTextLineSublayer(
                            position=(right, y),
                            text=rightMessage,
                            **textProperties
                        )
                    y += offset

    def _updateLayer(self, layer, obj, testIdentifier, forceUpdate):
        if testIdentifier in self.inactiveTests or not self.showReport:
            layer.clearSublayers()
            return
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
                method(obj, layer, newValue)

    # -------------
    # Visualization
    # -------------

    def getTextProperties(self):
        textFont = self.textFont
        font = textFont["font"]
        weight = textFont["weight"]
        pointSize = textFont["pointSize"]
        properties = dict(
            font=font,
            weight=weight,
            pointSize=pointSize,
            horizontalAlignment="center",
            verticalAlignment="center",
            fillColor=(0, 0, 0, 1),
            backgroundColor=self.colorBackground,
            cornerRadius=pointSize / 2,
            padding=(pointSize / 2, pointSize / 4),
            offset=(0, -10)
        )
        return properties

    def getArrowSymbolSettings(self):
        settings = dict(
            name="GlyphNanny.editorArrow",
            size=(30, 20),
            strokeColor=self.colorReview,
            strokeWidth=1
        )
        return settings

    def getInsertSymbolSettings(self):
        settings = dict(
            name="GlyphNanny.editorInsert",
            size=(17, 17),
            strokeColor=self.colorInsert,
            strokeWidth=1
        )
        return settings

    def getRemoveSymbolSettings(self):
        settings = dict(
            name="GlyphNanny.editorRemove",
            size=(17, 17),
            strokeColor=self.colorRemove,
            strokeWidth=1
        )
        return settings

    # Glyph
    # -----

    def visualize_stemWidths(self, glyph, layer, data):
        layer.clearSublayers()
        hProblems = data["horizontal"]
        vProblems = data["vertical"]
        if not hProblems and not vProblems:
            return
        arrowSettings = self.getArrowSymbolSettings()
        textProperties = self.getTextProperties()
        textProperties["fillColor"] = self.colorReview
        for y1, y2, xPositions in hProblems:
            xM = sum(xPositions) / len(xPositions)
            lineLayer = layer.appendLineSublayer(
                startPoint=(xM, y1),
                endPoint=(xM, y2),
                strokeColor=self.colorReview,
                strokeWidth=self.lineWidthRegular,
                startSymbol=arrowSettings,
                endSymbol=arrowSettings
            )
            if self.showTitles:
                x, y = calculateMidpoint((xM, y1), (xM, y2))
                lineLayer.appendTextLineSublayer(
                    text="Check Stem",
                    position=(x, y),
                    **textProperties
                )
        for x1, x2, yPositions in vProblems:
            yM = sum(yPositions) / len(yPositions)
            lineLayer = layer.appendLineSublayer(
                startPoint=(x1, yM),
                endPoint=(x2, yM),
                strokeColor=self.colorReview,
                strokeWidth=self.lineWidthRegular,
                startSymbol=arrowSettings,
                endSymbol=arrowSettings
            )
            if self.showTitles:
                x, y = calculateMidpoint((x1, yM), (x2, yM))
                lineLayer.appendTextLineSublayer(
                    text="Check Stem",
                    position=(x, y),
                    **textProperties
                )

    def visualize_duplicateContours(self, glyph, layer, data):
        layer.clearSublayers()
        if data:
            for contourIndex, bounds in data:
                contour = self.glyph[contourIndex]
                path = contour.getRepresentation("merz.CGPath")
                pathLayer = layer.appendPathSublayer(
                    path=path,
                    fillColor=None,
                    strokeColor=self.colorRemove,
                    strokeWidth=self.lineWidthHighlight
                )
                if self.showTitles:
                    textProperties = self.getTextProperties()
                    textProperties["fillColor"] = self.colorRemove
                    textProperties["verticalAlignment"] = "top"
                    xMin, yMin, xMax, yMax = contour.bounds
                    x, y = calculateMidpoint((xMin, yMin), (xMax, yMax))
                    pathLayer.appendTextLineSublayer(
                        text="Duplicate Contour",
                        position=(x, yMin),
                        **textProperties
                    )

    def visualize_duplicateComponents(self, component, layer, data):
        layer.clearSublayers()
        if data:
            for componentIndex, bounds in data:
                component = self.glyph.components[componentIndex]
                path = component.getRepresentation("merz.CGPath")
                pathLayer = layer.appendPathSublayer(
                    path=path,
                    fillColor=None,
                    strokeColor=self.colorRemove,
                    strokeWidth=self.lineWidthHighlight
                )
                if self.showTitles:
                    textProperties = self.getTextProperties()
                    textProperties["fillColor"] = self.colorRemove
                    textProperties["verticalAlignment"] = "top"
                    xMin, yMin, xMax, yMax = component.bounds
                    x, y = calculateMidpoint((xMin, yMin), (xMax, yMax))
                    pathLayer.appendTextLineSublayer(
                        text="Duplicate Component",
                        position=(x, yMin),
                        **textProperties
                    )

    # Contour
    # -------

    def visualize_smallContours(self, contour, layer, data):
        layer.clearSublayers()
        if data:
            path = contour.getRepresentation("merz.CGPath")
            pathLayer = layer.appendPathSublayer(
                path=contour.getRepresentation("merz.CGPath"),
                fillColor=None,
                strokeWidth=self.lineWidthHighlight,
                strokeColor=self.colorRemove
            )
            if self.showTitles:
                textProperties = self.getTextProperties()
                textProperties["fillColor"] = self.colorRemove
                textProperties["verticalAlignment"] = "top"
                xMin, yMin, xMax, yMax = contour.bounds
                x, y = calculateMidpoint((xMin, yMin), (xMax, yMax))
                pathLayer.appendTextLineSublayer(
                    text="Tiny Contour",
                    position=(x, yMin),
                    **textProperties
                )

    def visualize_openContour(self, contour, layer, data):
        layer.clearSublayers()
        if data:
            arrowSymbolSettings = self.getArrowSymbolSettings()
            arrowSymbolSettings["strokeColor"] = self.colorInsert
            pt1, pt2 = data
            lineLayer = layer.appendLineSublayer(
                startPoint=pt1,
                endPoint=pt2,
                strokeWidth=self.lineWidthRegular,
                strokeColor=self.colorInsert,
                startSymbol=arrowSymbolSettings
            )
            if self.showTitles:
                textProperties = self.getTextProperties()
                textProperties["fillColor"] = self.colorInsert
                x, y = calculateMidpoint(pt1, pt2)
                lineLayer.appendTextLineSublayer(
                    text="Open Contour",
                    position=(x, y),
                    **textProperties
                )

    def visualize_curveSymmetry(self, contour, layer, data):
        layer.clearSublayers()
        if data:
            arrowSettings = self.getArrowSymbolSettings()
            arrowSettings["strokeColor"] = self.colorReview
            for toCurve, fromCurve in data:
                to3, to2, to1, to0 = toCurve
                from0, from1, from2, from3 = fromCurve
                if to0 != from0:
                    layer.appendLineSublayer(
                        startPoint=from0,
                        endPoint=to0,
                        strokeColor=self.colorReview,
                        strokeWidth=self.lineWidthRegular,
                        endSymbol=arrowSettings
                    )
                if to1 != from1:
                    layer.appendLineSublayer(
                        startPoint=from1,
                        endPoint=to1,
                        strokeColor=self.colorReview,
                        strokeWidth=self.lineWidthRegular,
                        endSymbol=arrowSettings
                    )
                if to2 != from2:
                    layer.appendLineSublayer(
                        startPoint=from2,
                        endPoint=to2,
                        strokeColor=self.colorReview,
                        strokeWidth=self.lineWidthRegular,
                        endSymbol=arrowSettings
                    )
                if to3 != from3:
                    layer.appendLineSublayer(
                        startPoint=from3,
                        endPoint=to3,
                        strokeColor=self.colorReview,
                        strokeWidth=self.lineWidthRegular,
                        endSymbol=arrowSettings
                    )
                curvePath = layer.appendPathSublayer(
                    fillColor=None,
                    strokeColor=self.colorReview,
                    strokeWidth=self.lineWidthRegular
                )
                pen = curvePath.getPen()
                pen.moveTo(to3)
                pen.curveTo(to2, to1, to0)
                pen.endPath()

    # Segment
    # -------

    def visualize_angleNearMiss(self, contour, layer, data):
        layer.clearSublayers()
        for pt1, pt2 in data:
            lineLayer = layer.appendLineSublayer(
                startPoint=pt1,
                endPoint=pt2,
                strokeWidth=self.lineWidthHighlight,
                strokeColor=self.colorReview
            )
            if self.showTitles:
                textProperties = self.getTextProperties()
                textProperties["fillColor"] = self.colorReview
                x, y = calculateMidpoint(pt1, pt2)
                lineLayer.appendTextLineSublayer(
                    text="Angle Near Miss",
                    position=(x, y),
                    **textProperties
                )

    def visualize_pointsNearVerticalMetrics(self, contour, layer, data):
        layer.clearSublayers()
        arrowSymbolSettings = self.getArrowSymbolSettings()
        for verticalMetric, points in data.items():
            for (x, y) in points:
                lineLayer = layer.appendLineSublayer(
                    startPoint=(x, y),
                    endPoint=(x, verticalMetric),
                    strokeWidth=self.lineWidthHighlight,
                    strokeColor=self.colorReview,
                    endSymbol=arrowSymbolSettings
                )

    def visualize_unsmoothSmooths(self, contour, layer, data):
        layer.clearSublayers()
        for pt1, pt2, pt3 in data:
            pathLayer = layer.appendPathSublayer(
                fillColor=None,
                strokeWidth=self.lineWidthHighlight,
                strokeColor=self.colorReview
            )
            pen = pathLayer.getPen()
            pen.moveTo(pt1)
            pen.lineTo(pt2)
            pen.lineTo(pt3)
            pen.endPath()
            if self.showTitles:
                textProperties = self.getTextProperties()
                textProperties["fillColor"] = self.colorReview
                x, y = calculateMidpoint(pt1, pt3)
                pathLayer.appendTextLineSublayer(
                    text="Unsmooth Smooth",
                    position=(x, y),
                    **textProperties
                )

    def visualize_complexCurves(self, contour, layer, data):
        layer.clearSublayers()
        for pt1, pt2, pt3, pt4 in data:
            pathLayer = layer.appendPathSublayer(
                fillColor=None,
                strokeWidth=self.lineWidthHighlight,
                strokeColor=self.colorReview
            )
            pen = pathLayer.getPen()
            pen.moveTo(pt1)
            pen.curveTo(pt2, pt3, pt4)
            pen.endPath()
            if self.showTitles:
                textProperties = self.getTextProperties()
                textProperties["fillColor"] = self.colorReview
                x, y = calculateMidpoint(pt1, pt4)
                pathLayer.appendTextLineSublayer(
                    text="Complex Curve",
                    position=(x, y),
                    **textProperties
                )

    def visualize_crossedHandles(self, contour, layer, data):
        layer.clearSublayers()
        for handleData in data:
            pt1, pt2, pt3, pt4 = handleData["points"]
            pt5 = handleData["intersection"]
            pathLayer = layer.appendPathSublayer(
                fillColor=None,
                strokeWidth=self.lineWidthHighlight,
                strokeColor=self.colorReview
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
                    fillColor=self.colorReview
                )
            )
            if self.showTitles:
                textProperties = self.getTextProperties()
                textProperties["fillColor"] = self.colorReview
                x, y = calculateMidpoint(pt1, pt4)
                pathLayer.appendTextLineSublayer(
                    text="Crossed Handles",
                    position=(x, y),
                    **textProperties
                )

    def visualize_unnecessaryHandles(self, contour, layer, data):
        layer.clearSublayers()
        symbolSettings = self.getRemoveSymbolSettings()
        for pt1, pt2 in data:
            lineLayer = layer.appendLineSublayer(
                startPoint=pt1,
                endPoint=pt2,
                strokeWidth=self.lineWidthHighlight,
                strokeColor=self.colorRemove,
                startSymbol=symbolSettings,
                endSymbol=symbolSettings
            )
            if self.showTitles:
                textProperties = self.getTextProperties()
                textProperties["fillColor"] = self.colorRemove
                x, y = calculateMidpoint(pt1, pt2)
                lineLayer.appendTextLineSublayer(
                    text="Unnecessary Handles",
                    position=(x, y),
                    **textProperties
                )

    def visualize_unevenHandles(self, contour, layer, data):
        layer.clearSublayers()
        for off1, off2, shape1, shape2 in data:
            pathLayer = layer.appendPathSublayer(
                fillColor=self.colorReview
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
                textProperties["fillColor"] = self.colorReview
                x, y = calculateMidpoint(off1, off2)
                pathLayer.appendTextLineSublayer(
                    text="Uneven Handles",
                    position=(x, y),
                    **textProperties
                )

    def visualize_extremePoints(self, contour, layer, data):
        layer.clearSublayers()
        if data:
            imageSettings = self.getInsertSymbolSettings()
            for point in data:
                symbolLayer = layer.appendSymbolSublayer(
                    position=point,
                    size=imageSettings["size"],
                    imageSettings=imageSettings
                )
                if self.showTitles:
                    textProperties = self.getTextProperties()
                    textProperties["fillColor"] = self.colorInsert
                    textProperties["verticalAlignment"] = "top"
                    layer.appendTextLineSublayer(
                        text="Insert Point",
                        position=point,
                        **textProperties
                    )

    # Points
    # ------

    def _visualizeRemovePoints(self, layer, points, title):
        if points:
            imageSettings = self.getRemoveSymbolSettings()
            for point in points:
                symbolLayer = layer.appendSymbolSublayer(
                    position=point,
                    size=imageSettings["size"],
                    imageSettings=imageSettings
                )
                if self.showTitles:
                    textProperties = self.getTextProperties()
                    textProperties["fillColor"] = self.colorRemove
                    textProperties["verticalAlignment"] = "top"
                    layer.appendTextLineSublayer(
                        text=title,
                        position=point,
                        **textProperties
                    )

    def visualize_strayPoints(self, contour, layer, data):
        layer.clearSublayers()
        if data:
            self._visualizeRemovePoints(layer, [data], "Stray Point")

    def visualize_unnecessaryPoints(self, contour, layer, data):
        layer.clearSublayers()
        self._visualizeRemovePoints(layer, data, "Unnecessary Point")

    def visualize_overlappingPoints(self, contour, layer, data):
        layer.clearSublayers()
        self._visualizeRemovePoints(layer, data, "Overlapping Point")

# -------
# Symbols
# -------

from merz.tools.drawingTools import NSImageDrawingTools

def editorInsertSymbolFactory(size, strokeColor, strokeWidth):
    width, height = size
    cX = width / 2
    cY = height / 2
    bot = NSImageDrawingTools((width, height))
    pen = bot.BezierPath()
    pen.moveTo((0, cY))
    pen.lineTo((width, cY))
    pen.endPath()
    pen.moveTo((cX, height))
    pen.lineTo((cX, 0))
    pen.endPath()
    bot.stroke(*strokeColor)
    bot.strokeWidth(strokeWidth)
    bot.drawPath(pen)
    return bot.getImage()

merz.SymbolImageVendor.registerImageFactory("GlyphNanny.editorInsert", editorInsertSymbolFactory)

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
        self.manager = TemporaryManagerSpawner()
        self.w = vanilla.FloatingWindow((200, 200))
        self.setUpBaseWindowBehavior()
        self.w.open()

    def windowCloseCallback(self, sender):
        self.manager.destroy()


if __name__ == "__main__":
    Test()
