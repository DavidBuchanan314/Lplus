from .metainfo import MetaInfo

if __name__ == "__main__":
	test = open("ubuntu-24.04.1-live-server-amd64.iso.torrent", "rb")
	info = MetaInfo.from_bencoded(test)
	print("announce:", info.announce)
	print("name:    ", info.info.name)
