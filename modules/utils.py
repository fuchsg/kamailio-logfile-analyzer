import atexit
import gzip
import magic
import os
from typing import Optional, IO
import sys

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

def get_filetype(filepath: str) -> str:
  """Get MIME-type of file"""
  if not os.path.exists(filepath):
    return ""
  mime = magic.Magic(mime=True)
  return mime.from_file(filepath)

def openlog(filepath:str, mode='rt', encoding='utf-8') -> Optional[IO]:
  """
    Opens file as one of the supported file types.
    Returns None, if the file is of unsupported type.
  """

  if not os.path.exists(filepath):
    return None  # File does not exist

  try:
    mime_type = get_filetype(filepath)

    if mime_type in ("application/gzip", "application/x-gzip"):
      return gzip.open(filepath, mode, encoding=encoding, errors="replace")

    if mime_type.startswith("text/") or mime_type in ("application/octet-stream", "application/json"):
      return open(filepath, mode, encoding=encoding, errors="replace")

    return None  # Unknown or unsupported file type
  except OSError:
    return None  # Error in opening the file
