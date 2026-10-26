"""Writers for txt, EPUB, and FB2."""

from ficbook_dl.formats.epub import write_epub
from ficbook_dl.formats.fb2 import write_fb2
from ficbook_dl.formats.txt import write_txt

WRITERS = {
    "txt": write_txt,
    "epub": write_epub,
    "fb2": write_fb2,
}

__all__ = ["WRITERS", "write_epub", "write_fb2", "write_txt"]
