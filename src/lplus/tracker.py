import aiohttp
import yarl
import os
from urllib.parse import urlencode
from typing import List

from . import bencode
from .metainfo import MetaInfo
from .peer import PeerInfo


async def get_peerlist(meta: MetaInfo) -> List[PeerInfo]:
	async with aiohttp.ClientSession() as session: # TODO: reuse sessions? (would require passing it in)
		params = {
			"info_hash": meta.info_hash,
			"peer_id": os.urandom(20), # TODO: persist this!
			#"ip": "TODO?",
			"port": 42069,
			"uploaded": 0,
			"downloaded": 0,
			"left": 2773874688,
			"event": "started",
			#"key": "djackjasdlfkajhdflakjhsdfl",
			#"compact": 1,
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
			return [
				PeerInfo(
					ip_addr=peer[b"ip"].decode(),
					port=int(peer[b"port"]),
					peer_id=peer[b"peer id"]
				)
				for peer in body[b"peers"]
			]
