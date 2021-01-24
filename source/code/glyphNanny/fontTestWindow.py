import os
import vanilla
from vanilla import dialogs
from defconAppKit.windows.baseWindow import BaseWindowController
from fontParts.world import CurrentFont
from testTabs import TestTabs, metrics
from scripting import testFont, formatFontReport


class GlyphNannyFontTestWindow(BaseWindowController):

    def __init__(self):
        testTabs = TestTabs("auto")
        height = 90 + testTabs.height
        width = 270

        self.w = vanilla.Window((width, height), "Glyph Nanny")

        # Tests

        self.w.testTabs = testTabs

        # Options

        self.w.ignoreOverlapCheckBox = vanilla.CheckBox(
            "auto",
            "Ignore Outline Overlaps"
        )

        # Buttons

        self.w.testCurrentFontButton = vanilla.Button(
            "auto",
            "Test Current Font",
            callback=self.testCurrentFontButtonCallback
        )

        rules = [
            "H:|-margin-[testTabs]-margin-|",
            "H:|-margin-[ignoreOverlapCheckBox]-margin-|",
            "H:|-margin-[testCurrentFontButton]-margin-|",
            "V:|"
                "-margin-"
                "[testTabs]"
                "-spacing-"
                "[ignoreOverlapCheckBox]"
                "-margin-"
                "[testCurrentFontButton]"
                "-margin-"
              "|"
        ]

        self.w.addAutoPosSizeRules(rules, metrics)
        self.w.open()

    def testCurrentFontButtonCallback(self, sender):
        font = CurrentFont()
        if font is None:
            dialogs.message("There is no font to test.", "Open a font and try again.")
            return
        self._processFont(font)

    def _processFont(self, font):
        testStates = self.w.testTabs.get()
        ignoreOverlap = self.w.ignoreOverlapCheckBox.get()
        progressBar = self.startProgress(tickCount=len(font))
        tests = [
            testIdentifier
            for testIdentifier, testState in testStates.items()
            if testState
        ]
        if ignoreOverlap:
            fontToTest = font.copy()
            for glyph in font:
                glyph.removeOverlap()
        else:
            fontToTest = font
        try:
            report = testFont(
                font,
                tests,
                progressBar=progressBar
            )
        finally:
            progressBar.close()
        text = formatFontReport(report)
        FontReportWindow(font, text, report.keys())


class FontReportWindow(BaseWindowController):

    def __init__(self, font, text, glyphsWithIssues):
        self.font = font
        self.glyphsWithIssues = glyphsWithIssues
        title = "Glyph Nanny Report: Unsaved Font"
        if font.path is not None:
            title = "Glyph Nanny Report: %s" % os.path.basename(font.path)
        self.w = vanilla.Window(
            (600, 400),
            title=title,
            minSize=(200, 200)
        )
        self.w.reportView = vanilla.TextEditor(
            "auto",
            text
        )
        self.w.markButton = vanilla.Button(
            "auto",
            "Mark Glyphs",
            callback=self.markButtonCallback
        )

        rules = [
            "H:|-margin-[reportView]-margin-|",
            "H:[markButton]-margin-|",
            "V:|"
                "-margin-"
                "[reportView]"
                "-spacing-"
                "[markButton]"
                "-margin-"
              "|"
        ]
        self.w.addAutoPosSizeRules(rules, metrics)

        self.w.open()

    def markButtonCallback(self, sender):
        for name in self.font.keys():
            if name in self.glyphsWithIssues:
                color = (1, 0, 0, 0.5)
            else:
                color = None
            self.font[name].mark = color


if __name__ == "__main__":
    GlyphNannyFontTestWindow()
