import ezui
from .tests.registry import testRegistry
from . import defaults

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