import aiohttp
import yarl
import os
from urllib.parse import urlencode

from . import bencode
from .metainfo import MetaInfo


async def get_peerlist(meta: MetaInfo):
	async with aiohttp.ClientSession() as session:
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
			"numwant": 50
		}
		# we have to encode manually to bypass aiohttp "requoting"
		url = meta.announce + "?" + urlencode(params)
		async with session.get(yarl.URL(url, encoded=True)) as resp:
			print(resp.status)
			res = await resp.read()
			print(res)
			body = bencode.parse(res)
			# TODO: figure out what "compact" peerlists are all about
			return body[b"peers"] # TODO: convert these into nice objects?
