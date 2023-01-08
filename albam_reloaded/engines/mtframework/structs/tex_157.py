# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class Tex157(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.id_magic = self._io.read_bytes(4)
        if not self.id_magic == b"\x54\x45\x58\x00":
            raise kaitaistruct.ValidationNotEqualError(b"\x54\x45\x58\x00", self.id_magic, self._io, u"/seq/0")
        self.packed_data_1 = self._io.read_u4le()
        self.packed_data_2 = self._io.read_u4le()
        self.num_textures = self._io.read_u1()
        self.format = self._io.read_u1()
        self.unk_01 = self._io.read_u1()
        self.unk_02 = self._io.read_u1()
        self.mipmap_offsets = [None] * (self.num_mipmaps)
        for i in range(self.num_mipmaps):
            self.mipmap_offsets[i] = self._io.read_u4le()

        self.dds_data = self._io.read_bytes_full()

    @property
    def num_mipmaps(self):
        if hasattr(self, '_m_num_mipmaps'):
            return self._m_num_mipmaps if hasattr(self, '_m_num_mipmaps') else None

        self._m_num_mipmaps = (self.packed_data_2 & 63)
        return self._m_num_mipmaps if hasattr(self, '_m_num_mipmaps') else None

    @property
    def width(self):
        if hasattr(self, '_m_width'):
            return self._m_width if hasattr(self, '_m_width') else None

        self._m_width = ((self.packed_data_2 >> 6) & 8191)
        return self._m_width if hasattr(self, '_m_width') else None

    @property
    def height(self):
        if hasattr(self, '_m_height'):
            return self._m_height if hasattr(self, '_m_height') else None

        self._m_height = ((self.packed_data_2 >> 19) & 8191)
        return self._m_height if hasattr(self, '_m_height') else None


