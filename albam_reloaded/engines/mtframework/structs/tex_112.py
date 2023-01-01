# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class Tex112(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.id_magic = self._io.read_bytes(4)
        if not self.id_magic == b"\x54\x45\x58\x00":
            raise kaitaistruct.ValidationNotEqualError(b"\x54\x45\x58\x00", self.id_magic, self._io, u"/seq/0")
        self.version = self._io.read_u2le()
        self.revision = self._io.read_u2le()
        self.num_mipmaps = self._io.read_u1()
        self.unk_01 = self._io.read_u1()
        self.unk_02 = self._io.read_u1()
        self.unk_03 = self._io.read_u1()
        self.width = self._io.read_u2le()
        self.height = self._io.read_u2le()
        self.reserved = self._io.read_u4le()
        self.format = (self._io.read_bytes(4)).decode(u"ascii")
        self.unk_04 = self._io.read_f4le()
        self.unk_05 = self._io.read_f4le()
        self.unk_06 = self._io.read_f4le()
        self.unk_07 = self._io.read_f4le()
        self.mipmap_offsets = [None] * (self.num_mipmaps)
        for i in range(self.num_mipmaps):
            self.mipmap_offsets[i] = self._io.read_u4le()

        self.dds_data = self._io.read_bytes_full()


