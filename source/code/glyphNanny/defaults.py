from tests.registry import testRegistry
from mojo.extensions import (
    registerExtensionDefaults,
    getExtensionDefault,
    setExtensionDefault
)

defaultKeyStub = "com.typesupply.GlyphNanny2."
defaults = {
    defaultKeyStub + "displayLiveReport" : True,
    defaultKeyStub + "displayTitles" : True,
    defaultKeyStub + "colorInform" : (0, 0, 0.7, 0.3),
    defaultKeyStub + "colorReview" : (0, 1, 0, 0.75),
    defaultKeyStub + "colorRemove" : (1, 0, 0, 0.5),
    defaultKeyStub + "colorInsert" : (1, 0.7, 0, 0.7),
    defaultKeyStub + "lineWidthRegular" : 1,
    defaultKeyStub + "lineWidthHighlight" : 4,
}
for testIdentifier in testRegistry.keys():
    defaults[defaultKeyStub + "testState." + testIdentifier] = True

registerExtensionDefaults(defaults)

# -----
# Tests
# -----

def getTestState(testIdentifier):
    return getExtensionDefault(defaultKeyStub + "testState." + testIdentifier)

def setTestState(testIdentifier, value):
    setExtensionDefault(defaultKeyStub + "testState." + testIdentifier, value)

# -------
# Display
# -------

# Live Report

def getDisplayLiveReport():
    return getExtensionDefault(defaultKeyStub + "displayLiveReport")

def setDisplayLiveReport(value):
    setExtensionDefault(defaultKeyStub + "displayLiveReport", value)

# Titles

def getDisplayTitles():
    return getExtensionDefault(defaultKeyStub + "displayTitles")

def setDisplayTitles(value):
    setExtensionDefault(defaultKeyStub + "displayTitles", value)

# ------
# Colors
# ------

# Inform

def getColorInform():
    return getExtensionDefault(defaultKeyStub + "colorInform")

def setColorInform(value):
    setExtensionDefault(defaultKeyStub + "colorInform", value)

# Review

def getColorReview():
    return getExtensionDefault(defaultKeyStub + "colorReview")

def setColorReview(value):
    setExtensionDefault(defaultKeyStub + "colorReview", value)

# Remove

def getColorRemove():
    return getExtensionDefault(defaultKeyStub + "colorRemove")

def setColorRemove(value):
    setExtensionDefault(defaultKeyStub + "colorRemove", value)

# Insert

def getColorInsert():
    return getExtensionDefault(defaultKeyStub + "colorInsert")

def setColorInsert(value):
    setExtensionDefault(defaultKeyStub + "colorInsert", value)

# -----------
# Line Widths
# -----------

# Line: Regular

def getLineWidthRegular():
    return getExtensionDefault(defaultKeyStub + "lineWidthRegular")

def setLineWidthRegular(value):
    setExtensionDefault(defaultKeyStub + "lineWidthRegular", value)

# Line: Highlight

def getLineWidthHighlight():
    return getExtensionDefault(defaultKeyStub + "lineWidthHighlight")

def setLineWidthHighlight(value):
    setExtensionDefault(defaultKeyStub + "lineWidthHighlight", value)