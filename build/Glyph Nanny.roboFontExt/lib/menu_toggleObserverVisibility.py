from glyphNanny import defaults

state = defaults.getDisplayLiveReport()
defaults.setDisplayLiveReport(not state)

# XXX this will be replaced by something in mojo
from lib.tools.notifications import PostNotification
PostNotification("doodle.preferencesChanged")