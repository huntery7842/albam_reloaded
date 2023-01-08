# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class Mrl(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.id_magic = self._io.read_bytes(4)
        if not self.id_magic == b"\x4D\x52\x4C\x00":
            raise kaitaistruct.ValidationNotEqualError(b"\x4D\x52\x4C\x00", self.id_magic, self._io, u"/seq/0")
        self.version = self._io.read_u4le()
        self.num_materials = self._io.read_u4le()
        self.num_textures = self._io.read_u4le()
        self.unk_01 = self._io.read_u4le()
        self.ofs_textures = self._io.read_u4le()
        self.ofs_materials = self._io.read_u4le()
        self.textures = [None] * (self.num_textures)
        for i in range(self.num_textures):
            self.textures[i] = Mrl.TextureSlot(self._io, self, self._root)

        self.materials = [None] * (self.num_materials)
        for i in range(self.num_materials):
            self.materials[i] = Mrl.Material(self._io, self, self._root)


    class ResourceBinding(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.resource_type = self._io.read_u4le()
            self.resource_index = self._io.read_u4le()
            self.unk_01 = self._io.read_u4le()


    class TextureSlot(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.unk_01 = [None] * (4)
            for i in range(4):
                self.unk_01[i] = self._io.read_u1()

            self.unk_02 = self._io.read_u4le()
            self.unk_03 = self._io.read_u4le()
            self.texture_path = (KaitaiStream.bytes_terminate(self._io.read_bytes(64), 0, False)).decode(u"ascii")


    class Material(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.unk_01 = self._io.read_u4le()
            self.name_hash_crcjam32 = self._io.read_u4le()
            self.size_data = self._io.read_u4le()
            self.unk_04 = self._io.read_u4le()
            self.unk_05 = [None] * (4)
            for i in range(4):
                self.unk_05[i] = self._io.read_u1()

            self.unk_06 = [None] * (4)
            for i in range(4):
                self.unk_06[i] = self._io.read_u1()

            self.num_resources = self._io.read_u1()
            self.unk_07 = [None] * (3)
            for i in range(3):
                self.unk_07[i] = self._io.read_u1()

            self.unk_08 = [None] * (4)
            for i in range(4):
                self.unk_08[i] = self._io.read_u1()

            self.unk_09 = [None] * (4)
            for i in range(4):
                self.unk_09[i] = self._io.read_u1()

            self.unk_10 = self._io.read_u4le()
            self.unk_11 = self._io.read_u4le()
            self.unk_12 = self._io.read_u4le()
            self.unk_13 = self._io.read_u4le()
            self.ofs_data = self._io.read_u4le()
            self.unk_15 = self._io.read_u4le()

        @property
        def resources(self):
            if hasattr(self, '_m_resources'):
                return self._m_resources if hasattr(self, '_m_resources') else None

            _pos = self._io.pos()
            self._io.seek(self.ofs_data)
            self._m_resources = [None] * (self.num_resources)
            for i in range(self.num_resources):
                self._m_resources[i] = Mrl.ResourceBinding(self._io, self, self._root)

            self._io.seek(_pos)
            return self._m_resources if hasattr(self, '_m_resources') else None



