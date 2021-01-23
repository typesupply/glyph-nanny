import AppKit
import vanilla
import defaults
from tests.registry import testRegistry

metrics = dict(
    margin=15,
    leading=10,
    spacing=10
)


class GlyphNannyPrefsWindow:

    def __init__(self):
        self.w = vanilla.Window(
            (270, 485),
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

        self.w.testStatesGroup = TestTabs(
            "auto",
            callback=self.testStateCallback
        )

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

    def displayLiveReportCheckboxCallback(self, sender):
        defaults.setDisplayLiveReport(sender.get())

    def displayTitlesCheckboxCallback(self, sender):
        defaults.setDisplayTitles(sender.get())

    def colorGroupCallback(self, sender):
        setMethod = self.colorSetters[sender]
        value = sender.get()
        setMethod(value)

    def testStateCallback(self, sender):
        states = sender.get()
        for testIdentifier, state in states.items():
            defaults.setTestState(testIdentifier, state)


class TestTabs(vanilla.Group):

    def __init__(self, posSize, callback):
        super().__init__(posSize)
        self.callback = callback

        groups = [
            ("glyphInfo", "Glyph Info Tests"),
            ("glyph", "Glyph Tests"),
            ("metrics", "Metrics Tests"),
            ("contour", "Contour Tests"),
            ("segment", "Segment Tests"),
            ("point", "Point Tests")
        ]
        groupTitles = [title for (level, title) in groups]

        self.box = vanilla.Box((0, 10, 0, 225))

        self.tabSelectorFlex1 = vanilla.Group("auto")
        self.tabSelectorPopUpButton = vanilla.PopUpButton(
            "auto",
            groupTitles,
            callback=self.tabSelectorPopUpButtonCallback
        )
        self.tabSelectorFlex2 = vanilla.Group("auto")

        self.box.tabs = vanilla.Tabs(
            (0, 15, 0, 0),
            groupTitles,
            showTabs=False
        )
        self.checkBoxes = {}
        for i, (groupLevel, groupTitle) in enumerate(groups):
            tab = self.box.tabs[i]
            tab.stackGroup = vanilla.VerticalStackGroup(
                (0, 0, 0, 0),
                spacing=0,
                alignment="leading",
                edgeInsets=(0, 10, 0, -10)
            )
            sorter = []
            for testIdentifier, testData in testRegistry.items():
                if testData["level"] != groupLevel:
                    continue
                sorter.append((testIdentifier, testData["title"]))
            sorter.sort()
            for testIdentifier, testTitle in sorter:
                value = defaults.getTestState(testIdentifier)
                checkBox = vanilla.CheckBox(
                    "auto",
                    testTitle,
                    value=value,
                    callback=self.checkBoxCallback
                )
                tab.stackGroup.addView(checkBox, gravity="top")
                self.checkBoxes[testIdentifier] = checkBox

        rules = [
            "H:|[tabSelectorFlex1][tabSelectorPopUpButton][tabSelectorFlex2(==tabSelectorFlex1)]|",
            "V:|"
                "[tabSelectorFlex1(==0)]",
            "V:|"
                "[tabSelectorFlex2(==tabSelectorFlex1)]",
            "V:|"
                "[tabSelectorPopUpButton]"
        ]
        self.addAutoPosSizeRules(rules, metrics)

    def tabSelectorPopUpButtonCallback(self, sender):
        index = sender.get()
        self.box.tabs.set(index)

    def checkBoxCallback(self, sender):
        self.callback(self)

    def get(self):
        values = {
            testIdentifier : checkBox.get()
            for testIdentifier, checkBox in self.checkBoxes.items()
        }
        return values


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
            "V:|[title]|",
        ]
        self.addAutoPosSizeRules(rules, metrics)

    def colorWellCallback(self, sender):
        self.callback(self)

    def get(self):
        color = self.colorWell.get()
        color = color.getRed_green_blue_alpha_(None, None, None, None)
        return color


if __name__ == "__main__":
    GlyphNannyPrefsWindow()