from mojo.extensions import getExtensionDefault, getExtensionDefaultColor
from AppKit import NSColor

defaultKeyStub = "com.typesupply.GlyphNanny."
defaultKeyObserverVisibility = defaultKeyStub + "displayReportInGlyphView"
defaultKeyTitleVisibility = defaultKeyStub + "displayReportTitles"
defaultKeyTestStates = defaultKeyStub + "testStates"
defaultKeyColorInform = defaultKeyStub + "colorInform"
defaultKeyColorReview = defaultKeyStub + "colorReview"
defaultKeyColorRemove = defaultKeyStub + "colorRemove"
defaultKeyColorInsert = defaultKeyStub + "colorInsert"


class DefaultsManager(object):

    def __init__(self):
        self._values = {}

    def reload(self):
        self._values = {}

    # values

    def getValue(self, key):
        if key not in self._values:
            self._values[key] = getExtensionDefault(key)
        return self._values[key]

    def _get_showTitles(self):
        return self.getValue(defaultKeyTitleVisibility)

    showTitles = property(_get_showTitles)

    # Colors

    def _getColor(self, key, fallback):
        if key not in self._values:
            color = getExtensionDefaultColor(key)
            if color is None:
                color = NSColor.colorWithCalibratedRed_green_blue_alpha_(*fallback)
            self._values[key] = color
        return self._values[key]

    def _get_colorInform(self):
        return self._getColor(defaultKeyColorInform, (0, 0, 0.7, 0.3))

    colorInform = property(_get_colorInform)

    def _get_colorInsert(self):
        return self._getColor(defaultKeyColorInsert, (0, 1, 0, 0.75))

    colorInsert = property(_get_colorInsert)

    def _get_colorRemove(self):
        return self._getColor(defaultKeyColorRemove, (1, 0, 0, 0.5))

    colorRemove = property(_get_colorRemove)

    def _get_colorReview(self):
        return self._getColor(defaultKeyColorReview, (1, 0.7, 0, 0.7))

    colorReview = property(_get_colorReview)


defaults = DefaultsManager()
