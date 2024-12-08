import aiohttp
import yarl
import os
import socket
from urllib.parse import urlencode
from typing import List

from . import bencode
from .metainfo import MetaInfo
from .peer import PeerInfo


async def get_peerlist(meta: MetaInfo, peer_id: bytes) -> List[PeerInfo]:
	async with aiohttp.ClientSession() as session: # TODO: reuse sessions? (would require passing it in)
		params = {
			"info_hash": meta.info_hash,
			"peer_id": peer_id,
			#"ip": "TODO?",
			"port": 42069,
			"uploaded": 0,
			"downloaded": 0,
			"left": 2773874688,
			"event": "started",
			#"key": "djackjasdlfkajhdflakjhsdfl",
			"compact": 1,
			#"numwant": 100
		}
		# we have to encode manually to bypass aiohttp "requoting"
		url = meta.announce + "?" + urlencode(params)
		async with session.get(yarl.URL(url, encoded=True)) as resp:
			if not resp.ok:
				print(await resp.read())
				raise Exception("http error")
			res = await resp.read()
			body = bencode.parse(res)
			if isinstance(body[b"peers"], list): # not-compact mode
				return [
					PeerInfo(
						ip_addr=peer[b"ip"].decode(),
						port=int(peer[b"port"])
					)
					for peer in body[b"peers"]
				]

			assert(isinstance(body[b"peers"], bytes))
			assert(len(body[b"peers"]) % 6 == 0)
			peers = [
				PeerInfo(
					ip_addr=socket.inet_ntoa(body[b"peers"][i:i+4]),
					port=int.from_bytes(body[b"peers"][i+4:i+6])
				)
				for i in range(0, len(body[b"peers"]), 6)
			]

			if b"peers6" not in body:
				return peers

			assert(isinstance(body[b"peers6"], bytes))
			assert(len(body[b"peers6"]) % 18 == 0)
			peers6 = [
				PeerInfo(
					ip_addr=socket.inet_ntop(socket.AF_INET6, body[b"peers6"][i:i+16]),
					port=int.from_bytes(body[b"peers6"][i+16:i+18])
				)
				for i in range(0, len(body[b"peers6"]), 18)
			]

			return peers + peers6
