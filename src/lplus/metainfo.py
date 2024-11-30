from dataclasses import dataclass
from typing import BinaryIO, List
import hashlib

from . import bencode

@dataclass
class Info:
	name: str
	piece_length: int
	pieces: List[bytes]
	length: int
	# TODO: handle multi-file case

	@classmethod
	def from_dict(cls, value: dict):
		name = value[b"name"].decode()
		piece_length = value[b"piece length"]
		pieces_raw = value[b"pieces"]
		length = value[b"length"]
		assert(piece_length > 0)
		assert(length >= 0)
		assert(type(pieces_raw) is bytes)
		assert((len(pieces_raw) % 20) == 0)
		pieces = [pieces_raw[i:i+20] for i in range(0, len(pieces_raw), 20)]
		expected_piece_count = (length + piece_length - 1) // piece_length # round up
		assert(len(pieces) == expected_piece_count)
		return cls(
			name=name,
			piece_length=piece_length,
			pieces=pieces,
			length=length,
		)


@dataclass
class MetaInfo:
	announce: str
	info: Info
	info_hash: bytes

	@classmethod
	def from_bencoded(cls, stream: BinaryIO):
		parsed = bencode.parse(stream)
		info_dict = parsed[b"info"]
		info_bytes = bencode.serialise(info_dict)
		info_hash = hashlib.sha1(info_bytes).digest()
		return cls(
			announce=parsed[b"announce"].decode(),
			info=Info.from_dict(info_dict),
			info_hash=info_hash
		)
