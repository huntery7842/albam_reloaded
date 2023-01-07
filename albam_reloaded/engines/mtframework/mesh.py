from collections import namedtuple
import io
from struct import unpack

import bpy
from kaitaistruct import KaitaiStream
from mathutils import Matrix

from albam_reloaded.lib.blender import strip_triangles_to_triangles_list
from albam_reloaded.lib.misc import chunks
from . import EXTENSION_TO_FILE_ID
from .material import build_blender_materials
from .structs.mod_156 import Mod156

MOD_CLASS_MAPPER = {
    156: Mod156,
}


def build_blender_model(arc, mod_file_entry):
    LODS_TO_IMPORT = (1, 255)

    bl_mod_container_name = mod_file_entry.file_path
    bl_mod_container = bpy.data.objects.new(bl_mod_container_name, None)
    mod_type = EXTENSION_TO_FILE_ID['mod']

    mod_buffer = arc.get_file(mod_file_entry.file_path, mod_type)
    mod_version = mod_buffer[4]
    assert mod_version in MOD_CLASS_MAPPER, f"Unsupported version: {mod_version}"
    Mod = MOD_CLASS_MAPPER[mod_version]
    mod = Mod(KaitaiStream(io.BytesIO(mod_buffer)))
    bbox_data = _create_bbox_data(mod)
    skeleton = build_blender_armature(mod, bl_mod_container)
    materials = build_blender_materials(arc, mod, bl_mod_container_name)
    meshes_parent = skeleton or bl_mod_container

    for i, mesh in enumerate(m for m in mod.meshes if m.level_of_detail in LODS_TO_IMPORT):
        try:
            name = f'{bl_mod_container_name}_{str(i).zfill(2)}'
            bl_mesh_ob = build_blender_mesh(mod, mesh, name, bbox_data, mod_version == 156)
            bl_mesh_ob.parent = meshes_parent
            if skeleton:
                modifier = bl_mesh_ob.modifiers.new(type="ARMATURE", name="armature")
                modifier.object = meshes_parent
                modifier.use_vertex_groups = True
            if materials.get(mesh.idx_material):
                bl_mesh_ob.data.materials.append(materials[mesh.idx_material])
            else:
                print(f"[{bl_mod_container_name}] material {mesh.idx_material} not found")

        except Exception as err:
            print(f'[{bl_mod_container_name}] error building mesh {i} {err}')
            continue

    return bl_mod_container


def build_blender_mesh(mod, mesh, name, bbox_data, use_tri_strips=False):
    me_ob = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me_ob)

    locations = []
    normals = []
    uvs_1 = []
    uvs_2 = []
    uvs_3 = []
    weights_per_bone = {}

    for vertex_index, vertex in enumerate(mesh.vertices):
        _process_locations(vertex, locations, bbox_data)
        _process_normals(vertex, normals)
        _process_uvs(vertex, uvs_1, uvs_2, uvs_3)
        _process_weights(mod, mesh, vertex, vertex_index, weights_per_bone)

    indices = strip_triangles_to_triangles_list(mesh.indices) if use_tri_strips else mesh.indices
    # convert indices for this mesh only, so they start at zero
    indices = [tri_idx - mesh.vertex_position for tri_idx in indices]
    assert min(indices) >= 0, "Bad face indices"  # Blender crashes if not

    me_ob.from_pydata(locations, [], chunks(indices, 3))

    _build_normals(me_ob, normals)
    _build_uvs(me_ob, uvs_1, 'uv1')
    _build_uvs(me_ob, uvs_2, 'uv2')
    _build_uvs(me_ob, uvs_3, 'uv3')
    _build_weights(ob, weights_per_bone)

    return ob


def _process_locations(vertex, vertices_out, bbox_data):
    x = vertex.position.x
    y = vertex.position.y
    z = vertex.position.z
    w = getattr(vertex.position, 'w', None)
    if w:
        x = x / 32767 * bbox_data.width + bbox_data.min_x
        y = y / 32767 * bbox_data.height + bbox_data.min_y
        z = z / 32767 * bbox_data.depth + bbox_data.min_z

    # Y-up to z-up and cm to m
    vertices_out.append((x * 0.01, -z * 0.01, y * 0.01))


def _process_normals(vertex, normals_out):
    # from [0, 255] o [-1, 1]
    x = ((vertex.normal.x / 255) * 2) - 1
    y = ((vertex.normal.y / 255) * 2) - 1
    z = ((vertex.normal.z / 255) * 2) - 1
    # y up to z up
    normals_out.append((x, -z, y))


def _process_uvs(vertex, uvs_1_out, uvs_2_out, uvs_3_out):
    if not hasattr(vertex, 'uv'):
        return
    u = unpack('e', bytes(vertex.uv.u))[0]
    v = unpack('e', bytes(vertex.uv.v))[0]
    uvs_1_out.extend((u, -v))

    if not hasattr(vertex, 'uv2'):
        return
    u = unpack('e', bytes(vertex.uv2.u))[0]
    v = unpack('e', bytes(vertex.uv2.v))[0]
    uvs_2_out.extend((u, -v))

    if not hasattr(vertex, 'uv3'):
        return
    u = unpack('e', bytes(vertex.uv3.u))[0]
    v = unpack('e', bytes(vertex.uv3.v))[0]
    uvs_3_out.extend((u, -v))


def _process_weights(mod, mesh, vertex, vertex_index, weights_per_bone):
    if not hasattr(vertex, "bone_indices"):
        return

    bone_palette = mod.bones_mapping[mesh.bone_map_index]
    for bi, bone_index in enumerate(vertex.bone_indices):
        if bone_index >= bone_palette.unk_01:
            real_bone_index = mod.bones_animation_mapping[bone_index]
        else:
            try:
                real_bone_index = mod.bones_mapping[mesh.bone_map_index].indices[bone_index]
            except IndexError:
                # Behaviour not observed in original files so far
                real_bone_index = bone_index
        if bone_index + vertex.weight_values[bi] == 0:
            continue
        bone_data = weights_per_bone.setdefault(real_bone_index, [])
        bone_data.append((vertex_index, vertex.weight_values[bi] / 255))

    return weights_per_bone


def _build_normals(bl_mesh, normals):
    loop_normals = []
    bl_mesh.create_normals_split()
    bl_mesh.validate(clean_customdata=False)
    bl_mesh.update(calc_edges=True)
    bl_mesh.polygons.foreach_set("use_smooth", [True] * len(bl_mesh.polygons))

    for loop in bl_mesh.loops:
        loop_normals.append(normals[loop.vertex_index])
    bl_mesh.normals_split_custom_set_from_vertices(normals)
    bl_mesh.use_auto_smooth = True


def _build_uvs(bl_mesh, uvs, name='uv'):
    if not uvs:
        return
    uv_layer = bl_mesh.uv_layers.new(name=name)
    per_loop_list = []
    for loop in bl_mesh.loops:
        offset = loop.vertex_index * 2
        per_loop_list.extend((uvs[offset], uvs[offset + 1]))
    uv_layer.data.foreach_set("uv", per_loop_list)


def _build_weights(bl_obj, weights_per_bone):
    for bone_index, data in weights_per_bone.items():
        vg = bl_obj.vertex_groups.new(name=str(bone_index))
        for vertex_index, weight_value in data:
            vg.add((vertex_index,), weight_value, "ADD")


def build_blender_armature(mod, bl_object_parent):
    armature_name = bl_object_parent.name + "_skel"
    armature = bpy.data.armatures.new(armature_name)
    armature_ob = bpy.data.objects.new(armature_name, armature)
    armature_ob.parent = bl_object_parent
    armature_ob.show_in_front = True

    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for i in bpy.context.scene.objects:
        i.select_set(False)
    bpy.context.collection.objects.link(armature_ob)
    bpy.context.view_layer.objects.active = armature_ob
    armature_ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    blender_bones = []
    scale = 0.01
    # TODO: do it at blender level
    non_deform_bone_indices = get_non_deform_bone_indices(mod)
    for i, bone in enumerate(mod.bones):
        blender_bone = armature.edit_bones.new(str(i))
        blender_bone.parent = blender_bones[bone.idx_parent] if i != 0 else None
        blender_bone.use_deform = False if i in non_deform_bone_indices else True
        m = mod.inverse_bind_matrices[i]
        head = Matrix((
            (m.row_1.x, m.row_1.y, m.row_1.z, m.row_1.w),
            (m.row_2.x, m.row_2.y, m.row_2.z, m.row_2.w),
            (m.row_3.x, m.row_3.y, m.row_3.z, m.row_3.w),
            (m.row_4.x, m.row_4.y, m.row_4.z, m.row_4.w)
        )).inverted().transposed().to_translation()
        blender_bone.head = ([head[0] * scale, -head[2] * scale, head[1] * scale])
        blender_bone.tail = ([head[0] * scale, -head[2] * scale, (head[1] * scale) + 0.01])
        blender_bones.append(blender_bone)

    bpy.ops.object.mode_set(mode="OBJECT")
    return armature_ob


def _create_bbox_data(mod):
    BboxData = namedtuple('BboxData', (
        'min_x',
        'min_y',
        'min_z',
        'max_x',
        'max_y',
        'max_z',
        'width',
        'height',
        'depth',
        'dimension')
    )
    dimension = max(
        abs(mod.header.bbox_min.x),
        abs(mod.header.bbox_min.y),
        abs(mod.header.bbox_min.z)
    ) + max(
        abs(mod.header.bbox_max.x),
        abs(mod.header.bbox_max.y),
        abs(mod.header.bbox_max.z)
    )

    bbox_data = BboxData(
        min_x=mod.header.bbox_min.x,
        min_y=mod.header.bbox_min.y,
        min_z=mod.header.bbox_min.z,
        max_x=mod.header.bbox_max.x,
        max_y=mod.header.bbox_max.y,
        max_z=mod.header.bbox_max.z,
        width=mod.header.bbox_max.x - mod.header.bbox_min.x,
        height=mod.header.bbox_max.y - mod.header.bbox_min.y,
        depth=mod.header.bbox_max.z - mod.header.bbox_min.z,
        dimension=dimension
    )

    return bbox_data


def get_non_deform_bone_indices(mod):
    bone_indices = {i for i, _ in enumerate(mod.bones)}

    active_bone_indices = set()

    for mesh_index, mesh in enumerate(mod.meshes):
        for vi, vert in enumerate(mesh.vertices):
            for bone_index in getattr(vert, "bone_indices", []):
                try:
                    real_bone_index = mod.bones_mapping[mesh.bone_map_index].indices[
                        bone_index
                    ]
                except IndexError:
                    # Behavior not observed on original files
                    real_bone_index = bone_index
                active_bone_indices.add(real_bone_index)

    return bone_indices.difference(active_bone_indices)
