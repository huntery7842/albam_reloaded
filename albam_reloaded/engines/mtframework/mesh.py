import ctypes
import io
from itertools import chain
import os

import bpy
from mathutils import Matrix, Vector

from albam_reloaded.exceptions import BuildMeshError
from albam_reloaded.lib.blender import strip_triangles_to_triangles_list
from albam_reloaded.lib.half_float import unpack_half_float
from albam_reloaded.lib.misc import chunks
from albam_reloaded.lib.structure import get_size
from . import Mod156, BONE_INDEX_TO_GROUP
from .material import build_blender_materials
from .structs.arc import EXTENSION_TO_FILE_ID
from .structs.mod_156 import VERTEX_FORMATS_TO_CLASSES


def build_blender_model(arc, mod_file_entry):
    bl_mod_container_name = mod_file_entry.file_path.decode()
    bl_mod_container = bpy.data.objects.new(bl_mod_container_name, None)
    mod_type = EXTENSION_TO_FILE_ID['mod']

    mod_buffer = arc.get_file(mod_file_entry.file_path, mod_type)
    mod = Mod156(file_path=io.BytesIO(mod_buffer))

    materials = build_blender_materials(arc, mod, bl_mod_container_name)
    skeleton = build_blender_armature(mod, bl_mod_container)
    meshes_parent = skeleton or bl_mod_container

    LODS_TO_IMPORT = (1, 255)
    meshes = [m for m in mod.meshes_array if m.level_of_detail in LODS_TO_IMPORT]
    for i, mesh in enumerate(meshes):
        bl_mesh_name = f'{bl_mod_container_name}_{i}'
        try:
            bl_mesh_ob = build_blender_mesh(mod, mesh, i, bl_mesh_name, materials)
            bl_mesh_ob.parent = meshes_parent
            if skeleton:
                modifier = bl_mesh_ob.modifiers.new(type="ARMATURE", name="armature")
                modifier.object = meshes_parent
                modifier.use_vertex_groups = True
        except Exception as err:
            print(f'[{bl_mod_container_name}] error building mesh {i} {err}')
            raise

    return bl_mod_container


def build_blender_mesh(mod, mesh, mesh_index, name, materials):
    me_ob = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me_ob)

    imported_vertices = _import_vertices(mod, mesh)
    vertex_locations = imported_vertices["locations"]
    vertex_normals = imported_vertices["normals"]
    uvs_per_vertex = imported_vertices["uvs"]
    uvs_per_vertex_2 = imported_vertices["uvs2"]
    uvs_per_vertex_3 = imported_vertices["uvs3"]
    weights_per_bone = imported_vertices["weights_per_bone"]
    indices = get_indices_array(mod, mesh)
    indices = strip_triangles_to_triangles_list(indices)
    faces = chunks(indices, 3)
    weights_per_bone = imported_vertices["weights_per_bone"]

    assert min(indices) >= 0, "Bad face indices"  # Blender crashes if not
    me_ob.from_pydata(vertex_locations, [], faces)

    me_ob.create_normals_split()

    me_ob.validate(clean_customdata=False)
    me_ob.update(calc_edges=True)
    me_ob.polygons.foreach_set("use_smooth", [True] * len(me_ob.polygons))

    loop_normals = []
    for loop in me_ob.loops:
        loop_normals.append(vertex_normals[loop.vertex_index])

    me_ob.normals_split_custom_set_from_vertices(vertex_normals)
    me_ob.use_auto_smooth = True

    try:
        mesh_material = materials[mesh.material_index]
        if not mesh.use_cast_shadows and mesh_material.shadow_method:
            mesh_material.shadow_method = "NONE"
        me_ob.materials.append(mesh_material)
    except IndexError:
        print("material not found")

    for bone_index, data in weights_per_bone.items():
        vg = ob.vertex_groups.new(name=str(bone_index))
        for vertex_index, weight_value in data:
            vg.add((vertex_index,), weight_value, "ADD")

    if uvs_per_vertex:
        uv_layer = me_ob.uv_layers.new(name=name)
        per_loop_list = []
        for loop in me_ob.loops:
            offset = loop.vertex_index * 2
            per_loop_list.extend((uvs_per_vertex[offset], uvs_per_vertex[offset + 1]))
        uv_layer.data.foreach_set("uv", per_loop_list)

    # Checking material until we find a better way. Taken from max script
    has_light_map = mod.materials_data_array[mesh.material_index].texture_indices[3] > 0
    has_normal_map = mod.materials_data_array[mesh.material_index].texture_indices[1] > 0
    if has_light_map:
        if has_normal_map:
            source_uvs = uvs_per_vertex_3
        else:
            source_uvs = uvs_per_vertex_2
        uv_layer = me_ob.uv_layers.new(name="lightmap")
        per_loop_list = []
        for loop in me_ob.loops:
            offset = loop.vertex_index * 2
            per_loop_list.extend((source_uvs[offset], source_uvs[offset + 1]))
        uv_layer.data.foreach_set("uv", per_loop_list)
    return ob


def _import_vertices(mod, mesh):
    vertices_array = get_vertices_array(mod, mesh)

    if mesh.vertex_format != 0:
        locations = (transform_vertices_from_bbox(vf, mod) for vf in vertices_array)
    else:
        locations = ((vf.position_x, vf.position_y, vf.position_z) for vf in vertices_array)

    locations = map(lambda t: (t[0] / 100, t[2] / -100, t[1] / 100), locations)
    # from [0, 255] o [-1, 1]
    normals = map(
        lambda v: (
            ((v.normal_x / 255) * 2) - 1,
            ((v.normal_y / 255) * 2) - 1,
            ((v.normal_z / 255) * 2) - 1,
        ),
        vertices_array,
    )
    # y up to z up
    normals = map(lambda n: (n[0], n[2] * -1, n[1]), normals)

    uvs = [(unpack_half_float(v.uv_x), unpack_half_float(v.uv_y) * -1) for v in vertices_array]
    # XXX: normalmap has uvs as well? and then this should be uv3?
    if mesh.vertex_format == 0:
        uvs2 = [
            (unpack_half_float(v.uv2_x), unpack_half_float(v.uv2_y) * -1) for v in vertices_array
        ]
        uvs3 = [
            (unpack_half_float(v.uv3_x), unpack_half_float(v.uv3_y) * -1) for v in vertices_array
        ]
    else:
        uvs2 = []
        uvs3 = []

    return {
        "locations": list(locations),
        "normals": list(normals),
        # TODO: investigate why uvs don't appear above the image in the UV editor
        "uvs": list(chain.from_iterable(uvs)),
        "uvs2": list(chain.from_iterable(uvs2)),
        "uvs3": list(chain.from_iterable(uvs3)),
        "weights_per_bone": _get_weights_per_bone(mod, mesh, vertices_array),
    }


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
    non_deform_bone_indices = get_non_deform_bone_indices(mod)

    for i, bone in enumerate(mod.bones_array):  # add counter to the array
        blender_bone = armature.edit_bones.new(str(i))

        if i in non_deform_bone_indices:
            blender_bone.use_deform = False
        parents = get_bone_parents_from_mod(bone, mod.bones_array)
        if not parents:
            blender_bone.head = Vector(
                (bone.location_x / 100, bone.location_z * -1 / 100, bone.location_y / 100)
            )
            blender_bone.tail = Vector(
                (blender_bone.head[0], blender_bone.head[1], blender_bone.head[2] + 0.01)
            )
        else:
            chain = [i] + parents
            wtm = Matrix.Translation((0, 0, 0))
            for bi in reversed(chain):
                b = mod.bones_array[bi]
                wtm = wtm @ Matrix.Translation(
                    (b.location_x / 100, b.location_z / 100 * -1, b.location_y / 100)
                )
            blender_bone.head = wtm.to_translation()
            blender_bone.parent = blender_bones[bone.parent_index]

        blender_bone.tail = Vector(
            (blender_bone.head[0], blender_bone.head[1], blender_bone.head[2] + 0.01)
        )
        blender_bones.append(blender_bone)

    assert len(blender_bones) == len(mod.bones_array)

    bpy.ops.object.mode_set(mode="OBJECT")
    assert len(armature.bones) == len(mod.bones_array)

    _create_bone_groups(armature_ob, mod)
    return armature_ob


def _create_bone_groups(armature_ob, mod):
    bone_groups_cache = {
        "BONE_GROUP_MAIN": {
            "color_set": "THEME03",
            "name": "Main",
            "layer": 1,
        },
        "BONE_GROUP_ARMS": {
            "color_set": "THEME02",
            "name": "Arms",
            "layer": 2,
        },
        "BONE_GROUP_LEGS": {
            "color_set": "THEME05",
            "name": "Legs",
            "layer": 3,
        },
        "BONE_GROUP_HANDS": {
            "color_set": "THEME06",
            "name": "Hands",
            "layer": 4,
        },
        "BONE_GROUP_HAIR": {
            "color_set": "THEME07",
            "name": "Hair",
            "layer": 5,
        },
        "BONE_GROUP_FACIAL_BASIC": {
            "color_set": "THEME02",
            "name": "Facial Basic",
            "layer": 6,
        },
        "BONE_GROUP_FACIAL": {
            "color_set": "THEME01",
            "name": "Facial",
            "layer": 7,
        },
        "BONE_GROUP_ACCESORIES": {
            "color_set": "THEME14",
            "name": "Accessories",
            "layer": 8,
        },
        "OTHER": {
            "color_set": "THEME20",
            "name": "Other",
            "layer": 9,
        },
    }

    bpy.ops.object.mode_set(mode="POSE")
    for i, bone in enumerate(armature_ob.pose.bones):
        source_bone = mod.bones_array[i]
        anim_index = source_bone.anim_map_index
        bone.bone_group = _get_or_create_bone_group(anim_index, armature_ob, i, bone_groups_cache)
    bpy.ops.object.mode_set(mode="OBJECT")


def _get_or_create_bone_group(bone_anim_index, armature_ob, bone_index, bone_groups_cache):
    bone_group_name = BONE_INDEX_TO_GROUP.get(bone_anim_index, "OTHER")

    bone_group_cache = bone_groups_cache.get(bone_group_name) or bone_groups_cache["OTHER"]
    layer_index = bone_group_cache["layer"]
    _move_bone_to_layers(armature_ob, bone_index, 0, layer_index)

    if bone_group_cache.get("bl_group"):
        return bone_group_cache["bl_group"]

    bl_bone_group = armature_ob.pose.bone_groups.new(name=bone_group_cache["name"])
    bl_bone_group.color_set = bone_group_cache["color_set"]
    bone_group_cache["bl_group"] = bl_bone_group

    return bl_bone_group


def _move_bone_to_layers(armature_ob, bone_index, *layer_indices):
    layers = [False] * 32
    for layer_index in layer_indices:
        layers[layer_index] = True
    armature_ob.data.bones[bone_index].select = True
    bpy.ops.pose.bone_layers(layers=layers)
    armature_ob.data.bones[bone_index].select = False


def _get_weights_per_bone(mod, mesh, vertices_array):
    weights_per_bone = {}
    if not mod.bone_count or not hasattr(vertices_array[0], "bone_indices"):
        return weights_per_bone
    bone_palette = mod.bone_palette_array[mesh.bone_palette_index]
    for vertex_index, vertex in enumerate(vertices_array):
        for bi, bone_index in enumerate(vertex.bone_indices):
            if bone_index >= bone_palette.unk_01:
                real_bone_index = mod.bones_animation_mapping[bone_index]
            else:
                try:
                    real_bone_index = bone_palette.values[bone_index]
                except IndexError:
                    # Behaviour not observed in original files so far
                    real_bone_index = bone_index
            if bone_index + vertex.weight_values[bi] == 0:
                continue
            bone_data = weights_per_bone.setdefault(real_bone_index, [])
            bone_data.append((vertex_index, vertex.weight_values[bi] / 255))
    return weights_per_bone


def _create_mesh_name(index, file_path):
    mesh_name = os.path.basename(file_path)
    mesh_index = str(index).zfill(4)

    return f"{mesh_name}_{mesh_index}"


def get_vertices_array(mod, mesh):
    try:
        VF = VERTEX_FORMATS_TO_CLASSES[mesh.vertex_format]
    except KeyError:
        raise TypeError("Unrecognized vertex format: {}".format(hex(mesh.vertex_format)))
    if mod.version == 156:
        position = max(mesh.vertex_index_start_1, mesh.vertex_index_start_2) * mesh.vertex_stride
        if mesh.vertex_index_start_2 > mesh.vertex_index_start_1:
            vertex_count = mesh.vertex_index_end - mesh.vertex_index_start_2 + 1
            # TODO: research the content of mesh.vertex_index_start_1 and what it means in this case
            # So far it looks it contains only garbage; all vertices have the same values.
            # It's unknown why they exist for, and why they count for mesh.vertex_count
            # The imported meshes here will have a different mesh count than the original.
        else:
            vertex_count = mesh.vertex_count
    elif mod.version == 210:
        position = mesh.vertex_index * ctypes.sizeof(VF)
        vertex_count = mesh.vertex_count
    else:
        raise TypeError("Unsupported mod version: {}".format(mod.version))
    offset = ctypes.addressof(mod.vertex_buffer)
    offset += mesh.vertex_offset
    offset += position
    return (VF * vertex_count).from_address(offset)


def get_indices_array(mod, mesh):
    offset = ctypes.addressof(mod.index_buffer)
    position = mesh.face_offset * 2 + mesh.face_position * 2
    index_buffer_size = get_size(mod, "index_buffer")
    if position > index_buffer_size:
        raise BuildMeshError(
            "Error building mesh in get_indices_array (out of bounds reference)"
            "Size of mod.indices_buffer: {} mesh.face_offset: {}, mesh.face_position: {}".format(
                index_buffer_size, mesh.face_offset, mesh.face_position
            )
        )
    offset += position
    return (ctypes.c_ushort * mesh.face_count).from_address(offset)


def get_non_deform_bone_indices(mod):
    bone_indices = {i for i, _ in enumerate(mod.bones_array)}

    active_bone_indices = set()

    for mesh_index, mesh in enumerate(mod.meshes_array):
        for vi, vert in enumerate(get_vertices_array(mod, mesh)):
            for bone_index in getattr(vert, "bone_indices", []):
                try:
                    real_bone_index = mod.bone_palette_array[mesh.bone_palette_index].values[
                        bone_index
                    ]
                except IndexError:
                    # Behavior not observed on original files
                    real_bone_index = bone_index
                active_bone_indices.add(real_bone_index)

    return bone_indices.difference(active_bone_indices)


def vertices_export_locations(xyz_tuple, model_bounding_box):
    x, y, z = xyz_tuple

    x -= model_bounding_box.min_x
    x /= model_bounding_box.max_x - model_bounding_box.min_x
    x *= 32767

    y -= model_bounding_box.min_y
    y /= model_bounding_box.max_y - model_bounding_box.min_y
    y *= 32767

    z -= model_bounding_box.min_z
    z /= model_bounding_box.max_z - model_bounding_box.min_z
    z *= 32767

    return (round(x), round(y), round(z))


def transform_vertices_from_bbox(vertex_format, mod):
    x = vertex_format.position_x
    y = vertex_format.position_y
    z = vertex_format.position_z

    x = x / 32767 * (mod.box_max_x - mod.box_min_x) + mod.box_min_x
    y = y / 32767 * (mod.box_max_y - mod.box_min_y) + mod.box_min_y
    z = z / 32767 * (mod.box_max_z - mod.box_min_z) + mod.box_min_z

    return (x, y, z)


def get_bone_parents_from_mod(bone, bones_array):
    parents = []
    parent_index = bone.parent_index
    child_bone = bone
    if parent_index != 255:
        parents.append(parent_index)
    while parent_index != 255:
        child_bone = bones_array[child_bone.parent_index]
        parent_index = child_bone.parent_index
        if parent_index != 255:
            parents.append(parent_index)
    return parents
