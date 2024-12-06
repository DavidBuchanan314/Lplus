import asyncio
from enum import Enum
from typing import BinaryIO, Self, Set, Tuple, Dict, TYPE_CHECKING
from dataclasses import dataclass

from .metainfo import MetaInfo

if TYPE_CHECKING:
	from .session import TorrentSession

from .bitmap import Bitmap

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

PROTOCOL_MAGIC = b"\x13BitTorrent protocol"

@dataclass
class PeerInfo:
	ip_addr: str
	port: int
	peer_id: bytes

# TODO: make this abstraction work for *listening* on a port, too
class PeerSession:
	def __init__(self, ts: "TorrentSession", peer: PeerInfo) -> None:
		self.ts = ts
		self.peer = peer
		self.choked = True  # choked = "I don't want to send right now"
		self.interested = False # interested = "I want to receive data"

		self.peer_pieces = Bitmap(len(self.ts.meta.info.pieces))
		self.peer_choked = True
		self.peer_interested = False

		self.inflight_requests: Dict[Tuple[int, int, int], asyncio.Queue[bytes]] = {} # (index, begin, length)

	async def request(self, index: int, begin: int, length: int) -> bytes:
		req = (index, begin, length)
		if req in self.inflight_requests:
			raise Exception("there's a request for that already in-flight")
		q = asyncio.Queue()
		self.inflight_requests[req] = q
		try:
			# TODO: wrap in timeout?
			await self._send_message(MsgType.REQUEST, b"".join(i.to_bytes(4, "big") for i in req))
			print("sent request for piece")
			return await q.get()
		finally:
			del self.inflight_requests[req]

	async def set_choked(self, is_choked: bool):
		await self._send_message(MsgType.CHOKE if is_choked else MsgType.UNCHOKE, b"")

	async def set_interested(self, is_interested: bool):
		await self._send_message(MsgType.INTERESTED if is_interested else MsgType.NOT_INTERESTED, b"")

	async def __aenter__(self) -> Self:
		await self._connect()
		await self._handshake()
		self.recv_task = asyncio.create_task(self._recvloop())
		return self

	async def __aexit__(self, exc_type, exc, tb):
		self.writer.close()
		self.recv_task.cancel()
		try:
			await self.recv_task
		except asyncio.CancelledError:
			pass

	async def _connect(self) -> None:
		self.reader, self.writer = await asyncio.open_connection(self.peer.ip_addr, self.peer.port)
		print("connected")
	
	async def _handshake(self) -> None:
		self.writer.write(PROTOCOL_MAGIC)
		self.writer.write(bytes(8)) # reserved bytes
		self.writer.write(self.ts.meta.info_hash)
		self.writer.write(self.ts.peer_id)
		
		magic_recv = await self.reader.readexactly(len(PROTOCOL_MAGIC))
		if magic_recv != PROTOCOL_MAGIC:
			raise ValueError("handshake: bad magic")
		rsvd = await self.reader.readexactly(8)
		if any(rsvd):
			print("WARNING: nonzero reserved bytes:", rsvd.hex())
		hash_recv = await self.reader.readexactly(20)
		if hash_recv != self.ts.meta.info_hash:
			raise ValueError("handshake infohash did not match")
		peer_recv = await self.reader.readexactly(20)
		if peer_recv != self.peer.peer_id:
			raise ValueError("remote peer id did not match")
		
		print(f"handshook with {self.peer}")

		await self._send_message(MsgType.BITFIELD, self.ts.saved_pieces.buffer)
	
	async def _send_message(self, msgtype: MsgType, payload: bytes) -> None:
		# TODO: prevent these getting sent prematurely?
		self.writer.write((1 + len(payload)).to_bytes(4, "big"))
		self.writer.write(bytes([msgtype.value]))
		self.writer.write(payload)
		await self.writer.drain()

	async def _recvloop(self):
		while True:
			msg_len = int.from_bytes(await self.reader.readexactly(4), "big")
			if msg_len == 0:
				print("keepalive")
				continue
			
			msgtype = MsgType((await self.reader.readexactly(1))[0])
			payload = await self.reader.readexactly(msg_len - 1)

			print("recvd", msgtype)
			
			if msgtype == MsgType.CHOKE:
				assert(len(payload) == 0)
				self.peer_choked = True
			elif msgtype == MsgType.UNCHOKE:
				assert(len(payload) == 0)
				self.peer_choked = False
			elif msgtype == MsgType.INTERESTED:
				assert(len(payload) == 0)
				self.peer_interested = True
			elif msgtype == MsgType.NOT_INTERESTED:
				assert(len(payload) == 0)
				self.peer_interested = False
			elif msgtype == MsgType.HAVE:
				assert(len(payload) == 4)
				have_piece = int.from_bytes(payload, "big")
				self.peer_pieces[have_piece] = True
			elif msgtype == MsgType.BITFIELD:
				assert(len(payload) == len(self.peer_pieces.buffer))
				self.peer_pieces.buffer = bytearray(payload) # XXX: this invalidates the num_bits_set counter!!!
			elif msgtype == MsgType.REQUEST:
				pass # TODO: respond to requests!!!
			elif msgtype == MsgType.PIECE:
				index = int.from_bytes(payload[:4], "big")
				begin = int.from_bytes(payload[4:8], "big")
				piece = payload[8:]
				request = (index, begin, len(piece))
				if request not in self.inflight_requests:
					print("received a piece we weren't expecting, discarding")
					continue
				self.inflight_requests[request].put_nowait(piece)
			elif msgtype == MsgType.CANCEL:
				pass # TODO: care about this
			else:
				raise NotImplementedError(f"unreachable??? {msgtype}")
