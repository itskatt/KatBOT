"""Utility"""
import os
import re

from .time_ import ctimestamp, gettime

__all__ = ["ctimestamp", "gettime"]

EMBED_COLOUR = 0x7cdef9

EMOJI_REGEX = re.compile(r"<(?P<animated>a?):(?P<name>[^\s]+):(?P<id>[0-9]*)>")
URL_REGEX = re.compile(r"(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()"
                       r"<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};"
                       r":'\".,<>?«»“”‘’]))")

BINS = [
    "https://mystb.in/",
    "https://hastebin.com/",
    "https://paste.pydis.com/",
    "https://wastebin.travitia.xyz/"
]


class SgetError(Exception):
    pass


class _DataPathContainer:
    file = ""

    def setfile(self, file):
        self.file = file


datapath_container = _DataPathContainer()


def datapath(*path):
    filepath = os.path.dirname(os.path.abspath(datapath_container.file))

    return os.path.join(filepath, "katbot", "data", *path)
