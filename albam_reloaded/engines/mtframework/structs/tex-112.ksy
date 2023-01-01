meta:
  endian: le
  file-extension: tex
  id: tex_112
  ks-version: 0.9
  title: MTFramework texture format

seq:
  - {id: id_magic, contents: [0x54, 0x45, 0x58, 0x00]}
  - {id: version, type: u2}
  - {id: revision, type: u2}
  - {id: num_mipmaps, type: u1}
  - {id: unk_01, type: u1}
  - {id: unk_02, type: u1}
  - {id: unk_03, type: u1}
  - {id: width, type: u2}
  - {id: height, type: u2}
  - {id: reserved, type: u4}
  - {id: format, type: str, encoding: ascii, size: 4}
  - {id: unk_04, type: f4}
  - {id: unk_05, type: f4}
  - {id: unk_06, type: f4}
  - {id: unk_07, type: f4}
  - {id: mipmap_offsets, type: u4, repeat: expr, repeat-expr: num_mipmaps}
  # TODO: instance of every mipmap on-demand
  - {id: dds_data, size-eos: true}
