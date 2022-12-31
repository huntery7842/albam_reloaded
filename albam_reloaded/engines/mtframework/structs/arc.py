from ctypes import Structure, sizeof, c_int, c_uint, c_char, c_short, c_ubyte
import ntpath
import os
import zlib

from albam_reloaded.lib.structure import DynamicStructure

PADDING_SIZE = 32768


class FileEntry(Structure):
    MAX_FILE_PATH = 64

    _fields_ = (
        ("file_path", c_char * MAX_FILE_PATH),
        ("file_type", c_int),
        ("zsize", c_uint),
        ("size", c_uint, 24),
        ("flags", c_uint, 8),
        ("offset", c_uint),
    )


def get_padding(size):
    return (PADDING_SIZE - size % PADDING_SIZE) % PADDING_SIZE


def get_padding_from_struct(tmp_struct):
    return get_padding(sizeof(tmp_struct))


def get_data_length(tmp_struct, file_path=None):
    if file_path:
        try:
            length = os.path.getsize(file_path) - sizeof(tmp_struct)
        except TypeError:
            # XXX: inefficient?
            length = len(file_path.getbuffer()) - sizeof(tmp_struct)
    else:
        length = len(tmp_struct.data)
    return length


class Arc(DynamicStructure):
    ID_MAGIC = b"ARC"

    _fields_ = (
        ("id_magic", c_char * 4),
        ("version", c_short),
        ("files_count", c_short),
        ("file_entries", lambda s: FileEntry * s.files_count),
        ("padding", lambda s: c_ubyte * get_padding_from_struct(s)),
        ("data", lambda s, f: c_ubyte * get_data_length(s, f)),
    )

    def unpack(self, output_dir="."):
        data = memoryview(self.data)
        offset = 0
        output_dir = os.path.abspath(output_dir)
        for i in range(self.files_count):
            fe = self.file_entries[i]
            file_path = self._get_path(fe.file_path, fe.file_type, output_dir)
            file_dir = os.path.dirname(file_path)
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)
            with open(file_path, "wb") as w:
                w.write(zlib.decompress(data[offset : offset + fe.zsize]))
            offset += fe.zsize

    def get_file_entries_by_type(self, file_type):
        filtered = []
        for fe in self.file_entries:
            if fe.file_type == file_type:
                filtered.append(fe)
        return filtered

    def get_file(self, file_path, file_type):
        file_ = None

        for fe in self.file_entries:
            if fe.file_path == file_path and fe.file_type == file_type:
                data = memoryview(self.data)
                extra = sizeof(self.padding) + sizeof(self.file_entries) + 8
                file_ = zlib.decompress(
                    data[fe.offset - extra: fe.offset + fe.zsize - extra]
                )
                break
        return file_

    @classmethod
    def from_dir(cls, source_path):
        file_paths = {
            os.path.join(root, f) for root, _, files in os.walk(source_path) for f in files
        }
        files_count = len(file_paths)
        file_entries = (FileEntry * files_count)()
        size_so_far = 8 + sizeof(file_entries)
        padding = get_padding(size_so_far)
        current_offset = size_so_far + padding
        data = bytearray()
        for i, file_path in enumerate(sorted(file_paths)):
            with open(file_path, "rb") as f:
                chunk = zlib.compress(f.read())
            data.extend(chunk)
            ext = os.path.splitext(file_path)[1].replace(".", "")
            file_entries[i] = FileEntry(
                file_path=cls._set_path(source_path, file_path),
                file_type=EXTENSION_TO_FILE_ID.get(ext) or 0,
                flags=64,  # always compressing
                size=os.path.getsize(file_path),
                zsize=len(chunk),
                offset=current_offset,
            )
            current_offset += len(chunk)

        data = (c_ubyte * len(data)).from_buffer(data)
        return cls(
            id_magic=cls.ID_MAGIC,
            version=7,
            files_count=files_count,
            file_entries=file_entries,
            data=data,
        )

    @staticmethod
    def _get_path(file_path, file_type_id, output_path):
        file_extension = FILE_ID_TO_EXTENSION.get(file_type_id) or str(file_type_id)
        file_path = file_path.decode("ascii")
        file_path = ".".join((file_path, file_extension))
        parts = file_path.split(ntpath.sep)
        file_path = os.path.join(output_path, *parts)
        return file_path

    @staticmethod
    def _set_path(source_path, file_path):
        source_path = (
            source_path + os.path.sep if not source_path.endswith(os.path.sep) else source_path
        )
        file_path = file_path.replace(source_path, "")
        file_path = os.path.splitext(file_path)[0]
        parts = file_path.split(os.path.sep)
        return ntpath.join("", *parts).encode("ascii")


# Maps the hash id of each file type that the format accept
# and its corresponding extension. If the type is used throughout
# This list was provided by users in the Xentax forums.
# To do: search the users and credit them.

FILE_ID_TO_EXTENSION = {
    0x22FA09: "hpe",
    0x26E7FF: "ccl",
    0x86B80F: "plexp",
    0xFDA99B: "ntr",
    0x2358E1A: "spkg",
    0x2373BA7: "spn",
    0x2833703: "efs",
    0x58A15856: "mod",
    0x315E81F: "sds",
    0x437BCF2: "grw",
    0x4B4BE62: "tmd",
    0x525AEE2: "wfp",
    0x5A36D08: "qif",
    0x69A1911: "olp",
    0x737E28B: "rst",
    0x7437CCE: "base",
    0x79B5F3E: "pci",
    0x7B8BCDE: "fca",
    0x7F768AF: "gii",
    0x89BEF2C: "sap",
    0xA74682F: "rnp",
    0xC4FCAE4: "PldefendParam",
    0xD06BE6B: "tmn",
    0xECD7DF4: "sca",
    0x11C35522: "gr2",
    0x12191BA1: "epv",
    0x12688D38: "pjp",
    0x12C3BFA7: "cpl",
    0x133917BA: "mss",
    0x14428EAE: "gce",
    0x15302EF4: "lot",
    0x157388D3: "itl",
    0x15773620: "nmr",
    0x167DBBFF: "stq",
    0x1823137D: "mlm",
    0x19054795: "nml",
    0x199C56C0: "ocl",
    0x1B520B68: "zon",
    0x1BCC4966: "srq",
    0x1C2B501F: "atr",
    0x1EB3767C: "spr",
    0x2052D67E: "sn2",
    0x215896C2: "statusparam",
    0x2282360D: "jex",
    0x22948394: "gui",
    0x22B2A2A2: "PlNeckPos",
    0x232E228C: "rev",
    0x241F5DEB: "tex",
    0x242BB29A: "gmd",
    0x257D2F7C: "swm",
    0x2749C8A8: "mrl",
    0x271D08FE: "ssq",
    0x272B80EA: "prp",
    0x276DE8B7: "e2d",
    0x2A37242D: "gpl",
    0x2A4F96A8: "rbd",
    0x2B0670A5: "map",
    0x2B303957: "gop",
    0x2B40AE8F: "equ",
    0x2CE309AB: "joblvl",
    0x2D12E086: "srd",
    0x2D462600: "gfd",
    0x30FC745F: "smx",
    0x312607A4: "bll",
    0x31B81AA5: "qr",
    0x325AACA5: "shl",
    0x32E2B13B: "edp",
    0x33B21191: "esp",
    0x354284E7: "lvl",
    0x358012E8: "vib",
    0x36019854: "bed",
    0x39A0D1D6: "sms",
    0x39C52040: "lcm",
    0x3A947AC1: "cql",
    0x3BBA4E33: "qct",
    0x3D97AD80: "amr",
    0x3E356F93: "stc",
    0x3E363245: "chn",
    0x3FB52996: "imx",
    0x4046F1E1: "ajp",
    0x437662FC: "oml",
    0x4509FA80: "itemlv",
    0x456B6180: "cnsshake",
    0x472022DF: "aIPlactParam",
    0x48538FFD: "ist",
    0x48C0AF2D: "msl",
    0x49B5A885: "ssc",
    0x4B704CC0: "mia",
    0x4C0DB839: "sdl",
    0x4CA26828: "bmse",
    0x4E397417: "ean",
    0x4E44FB6D: "fpe",
    0x4EF19843: "nav",
    0x4FB35A95: "aor",
    0x50F3D713: "skl",
    0x5175C242: "geo2",
    0x51FC779F: "sbc",
    0x522F7A3D: "fcp",
    0x52DBDCD6: "rdd",
    0x535D969F: "ctc",
    0x5802B3FF: "ahc",
    0x59D80140: "ablparam",
    0x5A61A7C8: "fed",
    0x5A7FEA62: "ik",
    0x5B334013: "bap",
    0x5EA7A3E9: "sky",
    0x5F36B659: "way",
    0x5F88B715: "epd",
    0x60BB6A09: "hed",
    0x6186627D: "wep",
    0x619D23DF: "shp",
    0x628DFB41: "gr2s",
    0x63747AA7: "rpi",
    0x63B524A7: "ltg",
    0x64387FF1: "qlv",
    0x65B275E5: "sce",
    0x66B45610: "fsm",
    0x671F21DA: "stp",
    0x69A5C538: "dwm",
    0x6D0115ED: "prt",
    0x6D5AE854: "efl",
    0x6DB9FA5F: "cmc",
    0x6EE70EFF: "pcf",
    0x6F302481: "plw",
    0x6FE1EA15: "spl",
    0x72821C38: "stm",
    0x73850D05: "arc",
    0x754B82B4: "ahs",
    0x76820D81: "lmt",
    0x76DE35F6: "rpn",
    0x7808EA10: "rtex",
    0x7817FFA5: "fbik_human",
    0x7AA81CAB: "eap",
    0x7BEC319A: "sps",
    0x7DA64808: "qmk",
    0x7E1C8D43: "pcs",
    0x7E33A16C: "spc",
    0x7E4152FF: "stg",
    0x17A550D: "lom",
    0x253F147: "hit",
    0x39D71F2: "rvt",
    0xDADAB62: "oba",
    0x10C460E6: "msg",
    0x176C3F95: "los",
    0x19A59A91: "lnk",
    0x1BA81D3C: "nck",
    0x1ED12F1B: "glp",
    0x1EFB1B67: "adh",
    0x2447D742: "idm",
    0x266E8A91: "lku",
    0x2C4666D1: "smh",
    0x2DC54131: "cdf",
    0x30ED4060: "pth",
    0x36E29465: "hkx",
    0x38F66FC3: "seg",
    0x430B4FF4: "ptl",
    0x46810940: "egv",
    0x4D894D5D: "cmi",
    0x4E2FEF36: "mtg",
    0x4F16B7AB: "hri",
    0x50F9DB3E: "bfx",
    0x5204D557: "shp",
    0x538120DE: "eng",
    0x557ECC08: "aef",
    0x585831AA: "pos",
    0x5898749C: "bgm",
    0x60524FBB: "shw",
    0x60DD1B16: "lsp",
    0x758B2EB7: "cef",
    0x7D1530C2: "sngw",
    0x46FB08BA: "bmt",
    0x285A13D9: "vzo",
    0x4323D83A: "stex",
    0x6A5CDD23: "occ",
}

EXTENSION_TO_FILE_ID = {ext_desc: h for h, ext_desc in FILE_ID_TO_EXTENSION.items()}
