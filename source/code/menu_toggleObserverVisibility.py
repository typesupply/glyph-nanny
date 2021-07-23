from mojo.events import postEvent
from glyphNanny import defaults

state = defaults.getDisplayLiveReport()
defaults.setDisplayLiveReport(not state)
postEvent(
    defaults.defaultKeyStub + ".defaultsChanged"
)