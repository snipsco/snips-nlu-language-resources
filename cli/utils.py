from __future__ import unicode_literals

import shutil
from contextlib import contextmanager
from pathlib import Path
from tempfile import mkdtemp

TEMPLATE_PATH = Path(__file__).parent.parent / "template"


@contextmanager
def temp_dir():
    tmp_dir = mkdtemp()
    try:
        yield Path(tmp_dir)
    finally:
        shutil.rmtree(tmp_dir)


def get_entity_short_name(entity_name):
    # snips/musicArtist -> musicartist
    return entity_name[6:].lower()


def get_supported_entities(language):
    if language != "fr":
        return set()
    return {
        "snips/musicAlbum",
        "snips/musicArtist",
        "snips/musicTrack"
    }
