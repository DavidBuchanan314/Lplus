from typing import Tuple

class Bitmap:
	def __init__(self, length: int):
		self.buffer = bytearray((length + 7) // 8)
		self.length = length # length of the "virtual" bit array, in bits
		self.num_set_bits = 0

	def _get_index(self, n: int) -> Tuple[int, int]:
		if n >= self.length:
			raise IndexError("index out of range")
		byte_idx, bit_idx = divmod(n, 8)
		return byte_idx, 7 - bit_idx  # protocol has reversed bit-endianness, I think...

	def __getitem__(self, item: int) -> bool:
		byte_idx, bit_idx = self._get_index(item)
		return bool((self.buffer[byte_idx] >> bit_idx) & 1)

	def __contains__(self, item: int) -> bool:
		try:
			return self[item]
		except IndexError:
			return False

	def __setitem__(self, item: int, value: bool) -> None:
		byte_idx, bit_idx = self._get_index(item)
		val = self.buffer[byte_idx]
		self.num_set_bits += value - ((self[item] >> bit_idx) & 1) # keep track of total
		self.buffer[byte_idx] = (val & ~(1 << bit_idx)) | (int(value) << bit_idx)

	def set_buffer(self, buf: bytes) -> None:
		if len(buf) != len(self.buffer):
			raise ValueError("buffer length mismatch")
		self.buffer = bytearray(buf)
		padding_bits_mask = (1 << ((-self.length) % 8)) - 1
		self.buffer[-1] &= ~padding_bits_mask
		self.num_set_bits = int.from_bytes(self.buffer, "little").bit_count()
		# ^ the endianness used here doesn't affect the result, but matching
		# host endianness should marginally boost perf
