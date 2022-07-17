import ezui
from mojo.events import postEvent
from . import defaults
from .testTabs import makeTestsTableDescription


class GlyphNannyDefaultsWindow(ezui.WindowController):

    def build(self):
        # Live Report
        liveReportCheckboxDescription = dict(
            identifier="liveReport",
            type="Checkbox",
            text="Show Live Report",
            value=defaults.getDisplayLiveReport()
        )

        # Test During Drag
        testDuringDragCheckboxDescription = dict(
            identifier="testDuringDrag",
            type="Checkbox",
            text="Test During Drag",
            value=defaults.getTestDuringDrag()
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
            text="Show Titles",
            value=defaults.getDisplayTitles()
        )

        windowContent = dict(
            identifier="defaultsStack",
            type="VerticalStack",
            contents=[
                liveReportCheckboxDescription,
                testDuringDragCheckboxDescription,
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
            content=windowContent
        )
        self.w = ezui.makeItem(
            windowDescription,
            controller=self
        )

    def started(self):
        self.w.open()

    def defaultsStackCallback(self, sender):
        values = sender.get()
        defaults.setColorInform(values["informationColor"])
        defaults.setColorReview(values["reviewColor"])
        defaults.setColorInsert(values["insertColor"])
        defaults.setColorRemove(values["removeColor"])
        defaults.setDisplayLiveReport(values["liveReport"])
        defaults.setTestDuringDrag(values["testDuringDrag"])
        defaults.setDisplayTitles(values["reportTitles"])
        for testItem in values["testStates"]:
            if isinstance(testItem, ezui.TableGroupRow):
                continue
            defaults.setTestState(
                testItem["identifier"],
                testItem["state"]
            )
        postEvent(
            defaults.defaultKeyStub + ".defaultsChanged"
        )

    haveShownTestDuringDragNote = False

    def testDuringDragCallback(self, sender):
        if not self.haveShownTestDuringDragNote:
            self.showMessage(
                "This change will take effect after RoboFont is restarted.",
                "You'll have to restart RoboFont yourself."
            )
            self.haveShownTestDuringDragNote = True
        stack = self.w.findItem("defaultsStack")
        self.defaultsStackCallback(stack)