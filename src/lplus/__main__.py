import asyncio
import hashlib

from tqdm import tqdm

from .metainfo import MetaInfo
from . import tracker
from . import peer
from .bitmap import Bitmap

async def main():
	test = open("ubuntu-24.04.1-live-server-amd64.iso.torrent", "rb")
	meta = MetaInfo.from_bencoded(test)
	print("announce:     ", meta.announce)
	print("name:         ", meta.info.name)
	print("length:       ", meta.info.length)
	print("piece_length: ", meta.info.piece_length)
	print("infohash:     ", meta.info_hash.hex())
	print()

	saved_pieces = Bitmap(len(meta.info.pieces))

	with open(meta.info.name, "ab+") as file: # TODO: sanitise the path!!!!
		file.truncate(meta.info.length)

		for i, expected in tqdm(enumerate(meta.info.pieces), desc="Verifying local pieces"):
			file.seek(i * meta.info.piece_length)
			piece = file.read(meta.info.piece_length) # last read will be truncated
			hash_now = hashlib.sha1(piece).digest()
			saved_pieces[i] = hash_now == expected

		print(f"{saved_pieces.num_set_bits}/{saved_pieces.length} pieces already saved")

		#peerlist = await tracker.get_peerlist(meta)
		#for peer in peerlist:
		#	print(peer)

if __name__ == "__main__":
	asyncio.run(main())
