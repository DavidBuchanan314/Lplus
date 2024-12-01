import hashlib
from typing import Self
import time
import os

from tqdm import tqdm

from .metainfo import MetaInfo
from . import tracker
from . import peer
from .bitmap import Bitmap


class TorrentSession:
	uploaded: int = 0
	downloaded: int = 0

	def __init__(self, torrent_path: str):
		self.meta = MetaInfo.from_bencoded(open(torrent_path, "rb"))

		print("announce:     ", self.meta.announce)
		print("name:         ", self.meta.info.name)
		print("length:       ", self.meta.info.length)
		print("piece length: ", self.meta.info.piece_length)
		print("infohash:     ", self.meta.info_hash.hex())
		print()

		self.saved_pieces = Bitmap(len(self.meta.info.pieces))
		self.peer_id = os.urandom(20)
		self.start_time = time.time()

	async def __aenter__(self) -> Self:
		self.file = open(self.meta.info.name, "ab+") # TODO: sanitise the path!!!!
		self.file.truncate(self.meta.info.length)

		# TODO: make this async
		for i, expected in tqdm(enumerate(self.meta.info.pieces), desc="Verifying local pieces"):
			self.file.seek(i * self.meta.info.piece_length)
			piece = self.file.read(self.meta.info.piece_length) # last read will be truncated
			hash_now = hashlib.sha1(piece).digest()
			self.saved_pieces[i] = hash_now == expected

		self.peerlist = await tracker.get_peerlist(self.meta, self.peer_id)

		for peer in self.peerlist:
			print(peer)
		
		return self
	
	async def __aexit__(self, exc_type, exc, tb):
		self.file.close()
		# TODO: other cleanup
	
	def lplus_ratio(self) -> float:
		if self.downloaded == 0:
			return float("inf")
		return self.uploaded / self.downloaded

	def print_status(self):
		print()
		print("Status:")
		print(f"{int(time.time() - self.start_time)} seconds elapsed")
		print(f"{self.saved_pieces.num_set_bits}/{self.saved_pieces.length} pieces saved ({self.saved_pieces.num_set_bits/self.saved_pieces.length*100:.2f}%)")
		print(f"{self.uploaded} bytes up, {self.downloaded} bytes down (ratio: {self.lplus_ratio()})")
		print(f"{len(self.peerlist)} peers")
