import defcon

testRegistry = {}

fallbackDestructiveNotifications = {
    defcon.Glyph : ["Glyph.Changed"],
    defcon.Contour : ["Contour.Changed"]
}

def registerTest(
        identifier=None,
        level=None,
        title=None,
        description=None,
        testFunction=None,
        defconClass=None,
        destructiveNotifications=None
    ):
    representationName = "GlyphNanny." + identifier
    if destructiveNotifications is None:
        destructiveNotifications = fallbackDestructiveNotifications.get(defconClass, None)
    defcon.registerRepresentationFactory(
        cls=defconClass,
        name=representationName,
        factory=testFunction,
        destructiveNotifications=destructiveNotifications
    )
    testRegistry[identifier] = dict(
        level=level,
        description=description,
        title=title,
        representationName=representationName
    )
