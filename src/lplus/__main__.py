import asyncio

from .session import TorrentSession

async def main():
	async with TorrentSession("The-Fanimatrix-(DivX-5.1-HQ).avi.torrent") as ts:
		try:
			while True:
				ts.print_status()
				for peer, session in ts.peer_sessions.items():
					print(peer, session.peer_pieces.num_set_bits / session.peer_pieces.length)
				await asyncio.sleep(1)
		except asyncio.CancelledError: # Ctrl+C
			print("bye")

if __name__ == "__main__":
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		pass
