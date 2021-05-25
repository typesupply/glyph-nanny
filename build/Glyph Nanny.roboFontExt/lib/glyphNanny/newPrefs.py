import ezui
from glyphNanny.tests.registry import testRegistry
from glyphNanny import defaults

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


class Test(ezui.WindowController):

    def build(self):
        paneDescriptions = []
        for i, (groupLevel, groupTests) in enumerate(groupLevels.items()):
            groupTitle = groupTitles[i]
            testIdentifiers = groupLevels[groupLevel]
            testIdentifiers.sort()
            checkboxes = dict(
                type="Checkboxes",
                identifier=groupLevel,
                checkboxDescriptions=[]
            )
            for testTitle, testIdentifier in testIdentifiers:
                value = defaults.getTestState(testIdentifier)
                checkbox = dict(
                    identifier=testIdentifier,
                    text=testTitle,
                    value=value
                )
                checkboxes["checkboxDescriptions"].append(checkbox)
            paneDescription = dict(
                type="Pane",
                identifier=f"{groupLevel}Pane",
                text=groupTitle,
                closed=True,
                contentDescription=checkboxes
            )
            paneDescriptions.append(paneDescription)

        # pane1Description = dict(
        #     type="Pane",
        #     identifier="pane1",
        #     text="Pane 1",
        #     contentDescription=dict(
        #         type="VerticalStack",
        #         contentDescriptions=[
        #             dict(
        #                 type="PushButton",
        #                 text="Button 1"
        #             ),
        #             dict(
        #                 type="PushButton",
        #                 text="Button 2"
        #             )
        #         ]
        #     )
        # )

        windowContent = dict(
            type="ScrollingVerticalStack",
            contentDescriptions=paneDescriptions
        )
        windowDescription = dict(
            type="Window",
            size=(270, 400),
            title="Glyph Nanny Preferences",
            contentDescription=windowContent
        )
        self.w = ezui.makeItem(
            windowDescription
        )

    def started(self):
        self.w.open()


Test()