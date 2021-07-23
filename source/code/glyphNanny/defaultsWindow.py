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
        defaults.setColorInform(values["colors"]["informationColor"])
        defaults.setColorReview(values["colors"]["reviewColor"])
        defaults.setColorInsert(values["colors"]["insertColor"])
        defaults.setColorRemove(values["colors"]["removeColor"])
        defaults.setDisplayLiveReport(values["reportTitles"])
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
