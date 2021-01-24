import vanilla
from . import defaults
from .tests.registry import testRegistry

metrics = dict(
    margin=15,
    leading=10,
    spacing=10
)

class TestTabs(vanilla.Group):

    def __init__(self, posSize, callback=None):
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
        groupLevels = {}
        for testIdentifier, testData in testRegistry.items():
            level = testData["level"]
            if level not in groupLevels:
                groupLevels[level] = []
            groupLevels[level].append((testData["title"], testIdentifier))

        count = max([len(tests) for tests in groupLevels.values()])
        height = 40 + (count * 30)
        self.height = height

        self.box = vanilla.Box((0, 10, 0, height - 20))

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
            testIdentifiers = groupLevels[groupLevel]
            testIdentifiers.sort()
            for testTitle, testIdentifier in testIdentifiers:
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
        if self.callback is not None:
            self.callback(self)

    def get(self):
        values = {
            testIdentifier : checkBox.get()
            for testIdentifier, checkBox in self.checkBoxes.items()
        }
        return values
