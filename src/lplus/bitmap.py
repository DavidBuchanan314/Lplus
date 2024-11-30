from typing import Tuple

class Bitmap:
	def __init__(self, length: int):
		self.buffer = bytearray((length + 7) // 8)
		self.length = length
		self.num_set_bits = 0

	def _get_index(self, n: int) -> Tuple[int, int]:
		if n >= self.length:
			raise IndexError("index out of range")
		byte_idx, bit_idx = divmod(n, 8)
		return byte_idx, 7 - bit_idx  # protocol has reversed bit-endianness, I think...

	def __getitem__(self, item: int) -> bool:
		byte_idx, bit_idx = self._get_index(item)
		return bool((self.buffer[byte_idx] >> bit_idx) & 1)

	def __setitem__(self, item: int, value: bool) -> None:
		byte_idx, bit_idx = self._get_index(item)
		val = self.buffer[byte_idx]
		self.num_set_bits += value - ((self[item] >> bit_idx) & 1) # keep track of total
		self.buffer[byte_idx] = (val & ~(1 << bit_idx)) | (int(value) << bit_idx)
