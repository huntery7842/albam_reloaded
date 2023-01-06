meta:
  endian: le
  file-extension: mod
  id: mod_21
  ks-version: 0.9
  title: MTFramework model format 210 and 211

seq:
  - {id: header, type: mod_header}
  - {id: bones, type: bone, repeat: expr, repeat-expr: header.num_bones}
  - {id: parent_space_matrices, type: matrix4x4, repeat: expr, repeat-expr: header.num_bones}
  - {id: inverse_bind_matrices, type: matrix4x4, repeat: expr, repeat-expr: header.num_bones}
  - {id: bone_map, size: 256, if: header.num_bones != 0}
  - {id: groups, type: group, repeat: expr, repeat-expr: header.num_groups}
  - {id: material_names, type: str, encoding: ascii, size: 128, repeat: expr, repeat-expr: header.num_material_names, if: header.version == 210}
  - {id: material_hashes, type: u4, repeat: expr, repeat-expr: header.num_material_hashes, if: header.version == 211}
  - {id: meshes, type: mesh, repeat: expr, repeat-expr: header.num_meshes}
  - {id: num_weight_bounds_211, type: u4, if: header.version == 211}
  - {id: weight_bounds_210, type: weight_bound, repeat: expr, repeat-expr: header.num_weight_bounds_210, if: header.version == 210}
  - {id: weight_bounds_211, type: weight_bound, repeat: expr, repeat-expr: num_weight_bounds_211, if: header.version == 211}
  - {id: vertex_buffer, size: header.size_vertex_buffer}
  - {id: index_buffer, size: header.num_faces * 2}
  # TODO: padding

types:

  mod_header:
    seq:
      - {id: ident, contents: [0x4d, 0x4f, 0x44, 0x00]}
      - {id: version, type: u1}
      - {id: revision, type: u1}
      - {id: num_bones, type: u2}
      - {id: num_meshes, type: u2}
      - {id: num_material_names, type: u2, if: version == 210}
      - {id: num_material_hashes, type: u2, if: version == 211}
      - {id: num_vertices, type: u4}
      - {id: num_faces, type: u4}
      - {id: num_edges, type: u4}
      - {id: size_vertex_buffer, type: u4}
      - {id: reserved_01, type: u4}
      - {id: num_groups, type: u4}
      - {id: offset_bones, type: u4}
      - {id: offset_groups, type: u4}
      - {id: offset_material, type: u4}
      - {id: offset_meshes, type: u4}
      - {id: offset_buffer_vertices, type: u4}
      - {id: offset_buffer_indices, type: u4}
      - {id: size_file, type: u4}
      - {id: bsphere, type: vec4}
      - {id: bbox_min, type: vec4}
      - {id: bbox_max, type: vec4}
      - {id: unk_01, type: u4}
      - {id: unk_02, type: u4}
      - {id: unk_03, type: u4}
      - {id: unk_04, type: u4}
      - {id: num_weight_bounds_210, type: u4, if: version == 210}


  mesh:
    seq:
      - {id: idx_group, type: u2}
      - {id: num_vertices, type: u2}
      - {id: index_group, type: u1}
      - {id: index_material, type: u2}
      - {id: level_of_detail, type: u1}
      - {id: type_mesh, type: u1}
      - {id: unk_class_mesh, type: u1}
      - {id: vertex_stride, type: u1}
      - {id: unk_render_mode, type: u1}
      - {id: vertex_position, type: u4}
      - {id: vertex_offset, type: u4}
      - {id: vertex_format, type: u4}
      - {id: face_position, type: u4}
      - {id: face_count, type: u4}
      - {id: face_offset, type: u4}
      - {id: bone_id_start, type: u1}
      - {id: num_unique_bone_ids, type: u1}
      - {id: mesh_index, type: u2}
      - {id: min_index, type: u2}
      - {id: max_index, type: u2}
      - {id: hash, type: u4}
    instances:
      indices:
        pos: _root.header.offset_buffer_indices + face_offset * 2 + face_position * 2
        repeat: expr
        repeat-expr: face_count
        type: u2


  vec3:
    seq:
      - {id: x, type: f4}
      - {id: y, type: f4}
      - {id: z, type: f4}

  vec4:
    seq:
      - {id: x, type: f4}
      - {id: y, type: f4}
      - {id: z, type: f4}
      - {id: w, type: f4}

  matrix4x4:
    seq:
      - {id: row_1, type: vec4}
      - {id: row_2, type: vec4}
      - {id: row_3, type: vec4}
      - {id: row_4, type: vec4}

  bone:
    seq:
      - {id: idx, type: u1}
      - {id: idx_parent, type: u1}
      - {id: idx_mirror, type: u1}
      - {id: idx_mapping, type: u1}
      - {id: unk_01, type: f4}
      - {id: parent_distance, type: f4}
      - {id: location, type: vec3}

  group:
    seq:
      - {id: group_index, type: u4}
      - {id: unk_02, type: f4}
      - {id: unk_03, type: f4}
      - {id: unk_04, type: f4}
      - {id: unk_05, type: f4}
      - {id: unk_06, type: f4}
      - {id: unk_07, type: f4}
      - {id: unk_08, type: f4}

  material:
    seq:
      - {id: unk_01, type: u2}
      - {id: unk_02, type: u2}
      - {id: unk_floats, type: f4, repeat: expr, repeat-expr: 30}

  weight_bound:
    seq:
      - {id: bone_id, type: u4}
      - {id: unk_01, type: vec3}
      - {id: bsphere, type: vec4}
      - {id: bbox_min, type: vec4}
      - {id: bbox_max, type: vec4}
      - {id: oabb_matrix, type: matrix4x4}
      - {id: oabb_dimension, type: vec4}
