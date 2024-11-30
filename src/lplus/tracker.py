import aiohttp
import yarl
from urllib.parse import urlencode

from . import bencode

async def main():
	async with aiohttp.ClientSession() as session:
		params = {
			"info_hash": bytes.fromhex("41e6cd50ccec55cd5704c5e3d176e7b59317a3fb"),
			"peer_id": 'hQv3GcvOAQBBY-b0rsB4',
			#"ip": "TODO",
			"port": 42069,
			"uploaded": 0,
			"downloaded": 0,
			"left": 2773874688,
			"event": "started",
			#"key": "djackjasdlfkajhdflakjhsdfl",
			#"compact": 1,
			#"numwant": 50
		}
		# we have to encode manually to bypass aiohttp "requoting"
		url = "https://torrent.ubuntu.com/announce?" + urlencode(params)
		async with session.get(yarl.URL(url, encoded=True)) as resp:
			print(resp.status)
			res = await resp.read()
			print(res)
			body = bencode.parse(res)
			print(body)

if __name__ == "__main__":
	import asyncio
	asyncio.run(main())
