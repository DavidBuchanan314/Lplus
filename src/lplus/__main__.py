import asyncio

from .session import TorrentSession
from .peer import PeerSession

async def main():
	async with TorrentSession("ubuntu-24.04.1-live-server-amd64.iso.torrent") as ts:
		ipv4_peers = [p for p in ts.peerlist if "." in p.ip_addr]
		print(ipv4_peers)
		assert(len(ipv4_peers) >= 1)
		async with PeerSession(ts, ipv4_peers[0]) as ps:
			print("connected to peer")
			res = await ps.request(0, 0, 2**14)
			print("got piece!", len(res))
			while True:
				ts.print_status()
				await asyncio.sleep(1)

if __name__ == "__main__":
	asyncio.run(main())
