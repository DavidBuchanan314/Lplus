from typing import BinaryIO, Optional
import io

DIGITS = b"0123456789"

BencodeTypes = bytes | int | list | dict

# returns None on encountering an e
def maybe_parse(stream: BinaryIO) -> Optional[BencodeTypes]:
	char = stream.read(1)

	if char in DIGITS: # reading "string" type (parsed as bytes)
		length = int(char)
		if length: # only length that's allowed to start with 0 is 0 itself
			while (nextchar := stream.read(1)) in DIGITS:
				length = (length * 10) + int(nextchar)
		if nextchar != b":":
			raise ValueError(f"expected ':', read {nextchar}")
		value = stream.read(length)
		if len(value) != length:
			raise ValueError("string underread")
		return value

	elif char == b"i": # integer
		first_digit = stream.read(1)
		if first_digit == b"-":
			sign = -1
			first_digit = stream.read(1)
		else:
			sign = 1
		
		if first_digit in DIGITS:
			value = int(first_digit)
		else:
			raise ValueError(f"expected digit, read {first_digit}")
		
		if value:
			while (nextchar := stream.read(1)) in DIGITS:
				value = (value * 10) + int(nextchar)
		if nextchar != b"e":
			raise ValueError(f"expected 'e', read {nextchar}")

		return value * sign
	
	elif char == b"l": # list
		value = []
		while (obj := maybe_parse(stream)) is not None:
			value.append(obj)
		return value
	
	elif char == b"d": # dict
		value = {}
		prevk = None
		while (k := maybe_parse(stream)) is not None:
			if not isinstance(k, bytes):
				raise ValueError("bad dict key type")
			if prevk is not None:
				if k <= prevk:
					raise ValueError("non-canonical dict key order")
			value[k] = definitely_parse(stream) # it would be invalid to end here
		return value

	elif char == b"e": # not a real type, used to detect end of lists/dicts
		return None

	else:
		raise ValueError("invalid data")


# like maybe_parse but it's not allowed to return None
def definitely_parse(stream: BinaryIO) -> BencodeTypes:
	res = maybe_parse(stream)
	if res is None:
		raise ValueError("unexpected 'e'")
	return res


# same as definitely_parse but we check we parsed all the way until the end of the stream
def parse(stream: BinaryIO | bytes) -> BencodeTypes:
	if isinstance(stream, bytes):
		stream = io.BytesIO(stream)
	res = definitely_parse(stream)
	trailer = stream.read(1)
	if trailer:
		raise ValueError("trailing bytes")
	return res


def serialise_into_stream(stream: BinaryIO, obj: BencodeTypes) -> None:
	match obj:
		case bytes():
			stream.write(str(len(obj)).encode())
			stream.write(b":")
			stream.write(obj)
		case int():
			stream.write(b"i")
			stream.write(str(obj).encode())
			stream.write(b"e")
		case list():
			stream.write(b"l")
			for item in obj:
				serialise_into_stream(stream, item)
			stream.write(b"e")
		case dict():
			stream.write(b"d")
			for k, v in sorted(obj.items()):
				if not isinstance(k, bytes):
					raise ValueError("bad dict key type")
				serialise_into_stream(stream, k)
				serialise_into_stream(stream, v)
			stream.write(b"e")
		case _:
			raise ValueError(f"don't know how to bencode {type(obj)}")


def serialise(obj: BencodeTypes) -> bytes:
	res = io.BytesIO()
	serialise_into_stream(res, obj)
	return res.getvalue()


if __name__ == "__main__":
	test = open("archlinux-2024.11.01-x86_64.iso.torrent", "rb").read()

	res = parse(io.BytesIO(test))
	print(res)

	roundtrip = io.BytesIO()
	serialise_into_stream(roundtrip, res)
	assert(test == roundtrip.getvalue())
