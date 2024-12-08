import hashlib
from typing import Self, Dict
import random
import asyncio
import time
import io
import os

from tqdm import tqdm

from .metainfo import MetaInfo
from . import tracker
from . import peer
from .bitmap import Bitmap


class TorrentSession:
	uploaded: int = 0
	downloaded: int = 0
	peer_sessions: Dict[peer.PeerInfo, peer.PeerSession] = {}

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
		try:  # TODO: sanitise the path!!!!
			self.file = open(self.meta.info.name, "rb+")
		except FileNotFoundError:
			self.file = open(self.meta.info.name, "wb+")
		
		# check if it needs truncating (wrong size)
		self.file.seek(0, io.SEEK_END)
		print("tell", self.file.tell(), self.meta.info.length)
		if self.file.tell() != self.meta.info.length:
			print("truncating file")
			self.file.truncate(self.meta.info.length)

		self.file.seek(0)

		# TODO: make this async
		for i, expected in tqdm(enumerate(self.meta.info.pieces), desc="Verifying local pieces"):
			#self.file.seek(i * self.meta.info.piece_length)
			piece = self.file.read(self.meta.info.piece_length) # last read will be truncated
			hash_now = hashlib.sha1(piece).digest()
			self.saved_pieces[i] = hash_now == expected
		
		print(f"{self.saved_pieces.num_set_bits}/{self.saved_pieces.length} pieces already saved")
		#exit()

		self.peerlist = await tracker.get_peerlist(self.meta, self.peer_id)

		async def attach_peer(peerinfo):
			print("connecting to", peerinfo)
			session = peer.PeerSession(self, peerinfo, timeout=10)
			try:
				await session.__aenter__()
				self.peer_sessions[peerinfo] = session
				await session.set_interested(True) # say we want to send
			except asyncio.TimeoutError:
				print("timeout")
			except Exception as e:
				print(e)

		await asyncio.gather(*map(attach_peer, self.peerlist[:32])) # hardcoded 32 max peers for now (some won't connect...)

		self.leech_task = asyncio.create_task(self.leech_workloop())

		return self
	
	async def __aexit__(self, exc_type, exc, tb):
		self.file.close()
		self.leech_task.cancel()
		try:
			await self.leech_task
		except asyncio.CancelledError:
			pass
		print("shutting down peer connections")
		for peerinfo in list(self.peer_sessions): # avoid modification during iteration!
			await self.drop_peer(peerinfo)
	
	async def drop_peer(self, peerinfo: peer.PeerInfo):
		await self.peer_sessions.pop(peerinfo).__aexit__(None, None, None)
	
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
		print(f"{len(self.peer_sessions)} peers")

	async def leech_workloop(self):
		# TODO: use a proper queue
		pieces_to_download = list(range(len(self.meta.info.pieces)))
		random.shuffle(pieces_to_download)
		while pieces_to_download:
			current_piece = pieces_to_download.pop(0)
			if current_piece in self.saved_pieces:
				continue # we already have it
			print("trying to download piece", current_piece)
			peers = list(self.peer_sessions.items())
			random.shuffle(peers) # randomise which peers we're leeching from
			for peerinfo, peer_session in peers:
				if not peer_session.peer_choked and (current_piece in peer_session.peer_pieces):
					break
			else:
				print(f"could not find peer offering piece {current_piece}, putting it back in the queue")
				pieces_to_download.append(current_piece)
				await asyncio.sleep(0.1) # avoid a tight loop if no peers have anything
				continue

			print(f"decided to download piece {current_piece} from {peerinfo}")

			# TODO: concurrent piece downloads from multiple peers
			try:
				expected_piece_length = min(self.meta.info.piece_length, self.meta.info.length - (current_piece * self.meta.info.piece_length))
				tasks = []
				for i in range(0, expected_piece_length, 2**14):
					length_to_read = min(2**14, expected_piece_length - i)
					#print("trying to read", length_to_read)
					tasks.append(peer_session.request(current_piece, i, length_to_read))
				results = await asyncio.gather(*tasks)
				piece = b"".join(results)
				assert(len(piece) == expected_piece_length)
			except TimeoutError:
				print("timeout!")
				if peer_session.recv_task.done():
					print(f"dropping {peerinfo} due to {peer_session.recv_task.exception()}")
					await self.drop_peer(peerinfo)
				pieces_to_download.append(current_piece)
				continue
			except ConnectionResetError:
				print(f"connection to {peerinfo} died")
				# TODO: drop peer?
				pieces_to_download.append(current_piece)
				continue

			hash_calc = hashlib.sha1(piece).digest()

			if hash_calc != self.meta.info.pieces[current_piece]:
				print("hash calc failed!!!") # TODO: drop the peer?
				print(f"calculated piece hash {hash_calc.hex()}")
				print(f"expected piece hash {self.meta.info.pieces[current_piece].hex()}")
				pieces_to_download.append(current_piece)
				continue

			print(f"saving {len(piece)} bytes to offset {current_piece * self.meta.info.piece_length}")
			self.file.seek(current_piece * self.meta.info.piece_length)
			self.file.write(piece)
			self.file.flush()
			self.saved_pieces[current_piece] = True

			# TODO: tell the peers we got the piece
		
		print("All pieces downloaded!!!")
		while True:
			await asyncio.sleep(1)
