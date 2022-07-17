import os
from vanilla import dialogs
import ezui
from defconAppKit.windows.baseWindow import BaseWindowController
from fontParts.world import CurrentFont
from .testTabs import makeTestsTableDescription
from .scripting import testFont, formatFontReport


class GlyphNannyFontTestWindow(ezui.WindowController):

    def build(self):
        # Tests
        testsTableDescription = makeTestsTableDescription()

        # Overlaps
        ignoreOverlapCheckBox = dict(
            identifier="ignoreOverlap",
            type="Checkbox",
            text="Ignore Outline Overlaps"
        )

        # Test
        testCurrentFontButton = dict(
            identifier="testCurrentFontButton",
            type="PushButton",
            text="Test Current Font"
        )

        windowContent = dict(
            identifier="settingsStack",
            type="VerticalStack",
            contents=[
                testsTableDescription,
                ignoreOverlapCheckBox,
                testCurrentFontButton,
            ],
            spacing=15
        )
        windowDescription = dict(
            type="Window",
            size=(270, "auto"),
            title="Glyph Nanny",
            content=windowContent
        )
        self.w = ezui.makeItem(
            windowDescription,
            controller=self
        )

    def started(self):
        self.w.open()

    def testCurrentFontButtonCallback(self, sender):
        font = CurrentFont()
        if font is None:
            dialogs.message("There is no font to test.", "Open a font and try again.")
            return
        self._processFont(font)

    def _processFont(self, font):
        values = self.w.findItem("settingsStack")
        tests = []
        for testItem in self.w.findItem("testStates").get():
            if isinstance(testItem, ezui.TableGroupRow):
                continue
            identifier = testItem["identifier"]
            state = testItem["state"]
            if state:
                tests.append(identifier)
        ignoreOverlap = self.w.findItem("ignoreOverlap").get()
        # progressBar = self.startProgress(tickCount=len(font))
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
                # progressBar=progressBar
            )
        finally:
            pass
            # progressBar.close()
        text = formatFontReport(report)
        FontReportWindow(font, text, report.keys())


class FontReportWindow(ezui.WindowController):

    def build(self, font, text, glyphsWithIssues):
        self.font = font
        self.glyphsWithIssues = glyphsWithIssues
        title = "Glyph Nanny Report: Unsaved Font"
        if font.path is not None:
            title = "Glyph Nanny Report: %s" % os.path.basename(font.path)

        textEditorDescription = dict(
            type="TextEditor",
            text=text,
            height=">=150"
        )
        markButtonDescription = dict(
            identifier="markButton",
            type="PushButton",
            text="Mark Glyphs"
        )

        windowContent = dict(
            type="VerticalStack",
            contents=[
                textEditorDescription,
                markButtonDescription
            ]
        )
        windowDescription = dict(
            type="Window",
            size=(600, "auto"),
            minSize=(200, 200),
            title=title,
            content=windowContent
        )
        self.w = ezui.makeItem(
            windowDescription,
            controller=self
        )

    def started(self):
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
