import sys
import atexit

class Cursor:
  _hidden = False  # Tracking-Variable, um mehrfaches `hide()` zu vermeiden

  @classmethod
  def hide(cls):
    """Hide cursor and register `show()` for Exit."""
    if not cls._hidden:
      sys.stdout.write("\033[?25l")
      sys.stdout.flush()
      atexit.register(cls.show)  # Automatische Wiederherstellung bei Exit
      cls._hidden = True

  @classmethod
  def show(cls):
    """Show cursor."""
    if cls._hidden:
      sys.stdout.write("\033[?25h")
      sys.stdout.flush()
      cls._hidden = False
