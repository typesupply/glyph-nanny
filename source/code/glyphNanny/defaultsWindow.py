import AppKit
import vanilla
import defaults
from testTabs import TestTabs, metrics


class GlyphNannyDefaultsWindow:

    def __init__(self):
        testTabs = TestTabs(
            "auto",
            callback=self.testStateCallback
        )

        width = 270
        height = 250 + testTabs.height
        self.w = vanilla.Window(
            (width, height),
            "Glyph Nanny Preferences"
        )

        # Live Report

        self.w.displayLiveReportCheckbox = vanilla.CheckBox(
            "auto",
            "Show Live Report",
            value=defaults.getDisplayLiveReport(),
            callback=self.displayLiveReportCheckboxCallback
        )

        # Tests

        self.w.testStatesGroup = testTabs

        # Colors

        self.w.colorGroup = vanilla.VerticalStackGroup(
            "auto",
            spacing=10
        )
        colors = [
            ("Information",      defaults.getColorInform(), defaults.setColorInform),
            ("Review Something", defaults.getColorReview(), defaults.setColorReview),
            ("Insert Something", defaults.getColorInsert(), defaults.setColorInsert),
            ("Remove Something", defaults.getColorRemove(), defaults.setColorRemove)
        ]
        self.colorSetters = {}
        for title, color, setMethod in colors:
            group = ColorGroup(
                color=color,
                title=title,
                callback=self.colorGroupCallback
            )
            self.colorSetters[group] = setMethod
            self.w.colorGroup.addView(group)

        # Titles

        self.w.displayTitlesCheckbox = vanilla.CheckBox(
            "auto",
            "Show Report Titles",
            value=defaults.getDisplayTitles(),
            callback=self.displayTitlesCheckboxCallback
        )

        rules = [
            "H:|-margin-[displayLiveReportCheckbox]-margin-|",
            "H:|-margin-[testStatesGroup]-margin-|",
            "H:|-margin-[colorGroup]-margin-|",
            "H:|-margin-[displayTitlesCheckbox]-margin-|",

            "V:|"
                "-margin-"
                "[displayLiveReportCheckbox]"
                "-spacing-"
                "[testStatesGroup]"
                "-spacing-"
                "[colorGroup]"
                "-spacing-"
                "[displayTitlesCheckbox]"
                "-margin-"
              "|"
        ]
        self.w.addAutoPosSizeRules(rules, metrics)

        self.w.open()

    def xxxNotify(self):
        # XXX this will be replaced by something in mojo
        from lib.tools.notifications import PostNotification
        PostNotification("doodle.preferencesChanged")

    def displayLiveReportCheckboxCallback(self, sender):
        defaults.setDisplayLiveReport(sender.get())
        self.xxxNotify()

    def displayTitlesCheckboxCallback(self, sender):
        defaults.setDisplayTitles(sender.get())
        self.xxxNotify()

    def colorGroupCallback(self, sender):
        setMethod = self.colorSetters[sender]
        value = sender.get()
        setMethod(value)
        self.xxxNotify()

    def testStateCallback(self, sender):
        states = sender.get()
        for testIdentifier, state in states.items():
            defaults.setTestState(testIdentifier, state)
        self.xxxNotify()


metrics["colorGroupTitlePosition"] = 4

class ColorGroup(vanilla.Group):

    def __init__(self, color, title, callback):
        super().__init__("auto")
        self.callback = callback
        self.colorWell = vanilla.ColorWell(
            "auto",
            color=AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(*color),
            callback=self.colorWellCallback
        )
        self.title = vanilla.TextBox(
            "auto",
            title
        )
        rules = [
            "H:|[colorWell(==70)]-spacing-[title]",
            "V:|[colorWell(==25)]|",
            "V:|-colorGroupTitlePosition-[title]|",
        ]
        self.addAutoPosSizeRules(rules, metrics)

    def colorWellCallback(self, sender):
        self.callback(self)

    def get(self):
        color = self.colorWell.get()
        color = color.getRed_green_blue_alpha_(None, None, None, None)
        return color


if __name__ == "__main__":
    GlyphNannyDefaultsWindow()
