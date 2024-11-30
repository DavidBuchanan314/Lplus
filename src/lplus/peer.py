import asyncio
from enum import Enum
from typing import BinaryIO

from .metainfo import MetaInfo

class MsgType(Enum):
	CHOKE = 0
	UNCHOKE = 1
	INTERESTED = 2
	NOT_INTERESTED = 3
	HAVE = 4
	BITFIELD = 5
	REQUEST = 6
	PIECE = 7
	CANCEL = 8

PROTOCOL_MAGIC = b"19BitTorrent protocol"
