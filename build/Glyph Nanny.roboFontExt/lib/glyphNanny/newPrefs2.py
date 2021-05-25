import vanilla
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

def makeTestsTableDescription():
    columnDescriptions = [
        dict(
            identifier="state",
            cellDescription=dict(
                cellType="Checkbox"
            ),
            editable=True,
            width=16
        ),
        dict(
            identifier="title"
        )
    ]
    tableItems = []
    for i, (groupLevel, groupTests) in enumerate(groupLevels.items()):
        groupTitle = groupTitles[i]
        tableItems.append(
            groupTitle
        )
        testIdentifiers = groupLevels[groupLevel]
        testIdentifiers.sort()
        for testTitle, testIdentifier in testIdentifiers:
            value = defaults.getTestState(testIdentifier)
            item = dict(
                identifier=testIdentifier,
                title=testTitle,
                state=value
            )
            tableItems.append(item)
    testsTableDescription = dict(
        identifier="testStates",
        type="Table",
        columnDescriptions=columnDescriptions,
        items=tableItems,
        allowsGroupRows=True,
        showColumnTitles=False,
        alternatingRowColors=False,
        allowsSelection=False,
        allowsSorting=False,
        height=250
    )
    return testsTableDescription


class Test(ezui.WindowController):

    def build(self):
        # Live Report
        liveReportCheckboxDescription = dict(
            identifier="liveReport",
            type="Checkbox",
            text="Show Live Report",
            value=defaults.getDisplayLiveReport()
        )

        # Tests
        testsTableDescription = makeTestsTableDescription()

        # Colors
        informationColorWell = dict(
            identifier="informationColor",
            type="ColorWell",
            width=70,
            height=25,
            color=tuple(defaults.getColorInform())
        )
        reviewColorWell = dict(
            identifier="reviewColor",
            type="ColorWell",
            width=70,
            height=25,
            color=tuple(defaults.getColorReview())
        )
        insertColorWell = dict(
            identifier="insertColor",
            type="ColorWell",
            width=70,
            height=25,
            color=tuple(defaults.getColorInsert())
        )
        removeColorWell = dict(
            identifier="removeColor",
            type="ColorWell",
            width=70,
            height=25,
            color=tuple(defaults.getColorRemove())
        )

        rowDescriptions = [
            dict(
                itemDescriptions=[
                    informationColorWell,
                    dict(
                        type="Label",
                        text="Information"
                    )
                ]
            ),
            dict(
                itemDescriptions=[
                    reviewColorWell,
                    dict(
                        type="Label",
                        text="Review Something"
                    )
                ]
            ),
            dict(
                itemDescriptions=[
                    insertColorWell,
                    dict(
                        type="Label",
                        text="Insert Something"
                    )
                ]
            ),
            dict(
                itemDescriptions=[
                    removeColorWell,
                    dict(
                        type="Label",
                        text="Remove Something"
                    )
                ]
            ),
        ]
        columnDescriptions = [
            dict(
                width=70
            ),
            {}
        ]
        colorsGridDescription = dict(
            identifier="colors",
            type="Grid",
            rowDescriptions=rowDescriptions,
            columnPlacement="leading",
            rowPlacement="center"
        )

        # Titles
        reportTitlesCheckboxDescription = dict(
            identifier="reportTitles",
            type="Checkbox",
            text="Show Live Report",
            value=defaults.getDisplayTitles()
        )

        windowContent = dict(
            identifier="defaultsStack",
            type="VerticalStack",
            contentDescriptions=[
                liveReportCheckboxDescription,
                testsTableDescription,
                colorsGridDescription,
                reportTitlesCheckboxDescription,
            ],
            spacing=15
        )
        windowDescription = dict(
            type="Window",
            size=(270, "auto"),
            title="Glyph Nanny Preferences",
            contentDescription=windowContent
        )
        self.w = ezui.makeItem(
            windowDescription,
            controller=self
        )

    def started(self):
        self.w.open()

    def defaultsStackCallback(self, sender):
        values = sender.get()
        defaults.setColorInform(values["colors"]["informColor"])
        defaults.setColorReview(values["colors"]["informReview"])
        defaults.setColorInsert(values["colors"]["informInsert"])
        defaults.setColorRemove(values["colors"]["informRemove"])
        defaults.setDisplayLiveReport(values["reportTitles"])
        defaults.setDisplayTitles(values["reportTitles"])
        for testItem in values["testStates"]:
            if isinstance(testItem, ezui.TableGroupRow):
                continue
            defaults.setTestState(
                testItem["identifier"],
                testItem["state"]
            )
        self.xxxNotify()

    def xxxNotify(self):
        # XXX this will be replaced by something in mojo
        from lib.tools.notifications import PostNotification
        PostNotification("doodle.preferencesChanged")


Test()