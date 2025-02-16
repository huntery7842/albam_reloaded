from itertools import chain
import ntpath
import os

try:
    import bpy
    import addon_utils
    from mathutils import Matrix, Vector
    import numpy as np
except ImportError:
    pass

from ...exceptions import BuildMeshError, TextureError #my lines IDK where they originally imported

from ...engines.mtframework import Arc, Mod156, Tex112, KNOWN_ARC_BLENDER_CRASH, CORRUPTED_ARCS
from ...engines.mtframework.utils import (
    get_vertices_array,
    get_indices_array,
    get_non_deform_bone_indices,
    get_bone_parents_from_mod,
    transform_vertices_from_bbox,
    texture_code_to_blender_texture,

    )
from ...engines.mtframework.mappers import BONE_INDEX_TO_GROUP
from ...lib.misc import chunks
from ...lib.half_float import unpack_half_float
from ...lib.blender import strip_triangles_to_triangles_list
from ...lib.shader_group_node import create_shader_node_group
from ...registry import blender_registry


@blender_registry.register_function('import', identifier=b'ARC\x00')
def import_arc(blender_object, file_path, **kwargs):
    """Imports an arc file (Resident Evil 5 for only for now) into blender,
    extracting all files to a tmp dir and saving unknown/unused data
    to the armature (if any) for using in exporting
    """

    unpack_dir = kwargs.get('unpack_dir')
    if file_path.endswith(tuple(KNOWN_ARC_BLENDER_CRASH) + tuple(CORRUPTED_ARCS)):
        raise ValueError('The arc file provided is not supported yet, it might crash Blender')

    base_dir = os.path.basename(file_path).replace('.arc', '_arc_extracted')
    out = unpack_dir or os.path.join(os.path.expanduser('~'), '.albam', 're5', base_dir) #causing an error
    #out = os.path.join(os.path.expanduser('~'), '.albam', 're5', base_dir)
    if not os.path.isdir(out):
        os.makedirs(out)
    if not out.endswith(os.path.sep):
        out = out + os.path.sep

    arc = Arc(file_path=file_path)
    # make sure we have an empty dir (from previous imports)
    if (bpy.context.scene.albam_export_settings.clear_temp_foder_bool == True):
        existing_files = [os.path.join(root, f) for root, _, files in os.walk(out) for f in files]
        for f in existing_files:
            os.remove(f)

    arc.unpack(out)
    mod_files = [os.path.join(root, f) for root, _, files in os.walk(out)
                 for f in files if f.endswith('.mod')]
    mod_folders = [os.path.dirname(mod_file.split(out)[-1]) for mod_file in mod_files]

    return {'files': mod_files,
            'kwargs': {'parent': blender_object,
                       'mod_folder': mod_folders[0],  # XXX will break if mods are in different folders
                       'base_dir': out,
                       },
            }


@blender_registry.register_function('import', identifier=b'MOD\x00')
def import_mod(blender_object, file_path, **kwargs):
    base_dir = kwargs.get('base_dir') # full path to _extracted folder

    mod = Mod156(file_path=file_path)
    textures = _create_blender_textures_from_mod(mod, base_dir)
    materials = _create_blender_materials_from_mod(mod, blender_object.name, textures)

    # To simplify, import only main level of detail meshes
    LODS_TO_IMPORT = (1, 255)
    blender_meshes = []
    meshes = [m for m in mod.meshes_array if m.level_of_detail in LODS_TO_IMPORT]
    for i, mesh in enumerate(meshes):
        name = _create_mesh_name(i, file_path)
        try:
            m = _build_blender_mesh_from_mod(mod, mesh, i, name, materials)
            blender_meshes.append(m)
        except BuildMeshError as err:
            # TODO: logging
            print(f'Error building mesh {i} for mod {file_path}')
            print('Details:', err)
        except Exception as err:
            print(f"unexpected error building mesh {name}: {err}")

    if mod.bone_count:
        armature_name = 'skel_{}'.format(blender_object.name)
        root = _create_blender_armature_from_mod(blender_object, mod, armature_name)
        root.show_in_front = True # set x-ray view for bones
    else:
        root = blender_object

    for mesh in blender_meshes:
        bpy.context.collection.objects.link(mesh)
        mesh.parent = root
        if mod.bone_count:
            modifier = mesh.modifiers.new(type="ARMATURE", name=blender_object.name)
            modifier.object = root
            modifier.use_vertex_groups = True


def _build_blender_mesh_from_mod(mod, mesh, mesh_index, name, materials):
    me_ob = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me_ob)

    imported_vertices = _import_vertices(mod, mesh)
    vertex_locations = imported_vertices['locations']
    vertex_normals = imported_vertices['normals']
    uvs_per_vertex = imported_vertices['uvs']
    uvs_per_vertex_2 = imported_vertices['uvs2']
    uvs_per_vertex_3 = imported_vertices['uvs3']
    vertex_colors = imported_vertices['vertex_colors']
    weights_per_bone = imported_vertices['weights_per_bone']
    indices = get_indices_array(mod, mesh)
    indices = strip_triangles_to_triangles_list(indices)
    faces = chunks(indices, 3)
    weights_per_bone = imported_vertices['weights_per_bone']

    assert min(indices) >= 0, "Bad face indices"  # Blender crashes if not
    me_ob.from_pydata(vertex_locations, [], faces)

    me_ob.create_normals_split()

    me_ob.validate(clean_customdata=False)
    me_ob.update(calc_edges=True)
    me_ob.polygons.foreach_set("use_smooth", [True] * len(me_ob.polygons))

    vert_normals = np.array(vertex_normals, dtype=np.float32)
    norms = np.linalg.norm(vert_normals, axis=1, keepdims=True)
    np.divide(vert_normals, norms, out=vert_normals, where=norms != 0)
    me_ob.normals_split_custom_set_from_vertices(vert_normals)
    me_ob.use_auto_smooth = True

    mesh_material = materials[mesh.material_index]
    if not mesh.use_cast_shadows and mesh_material.shadow_method: # code gets .use_cast_shadows from mesh's custom props
        mesh_material.shadow_method = 'NONE' # if use_cast_shadows is false and a material shadows is enabled, set it to NONE
    me_ob.materials.append(mesh_material)

    for bone_index, data in weights_per_bone.items():
        vg = ob.vertex_groups.new(name=str(bone_index))
        for vertex_index, weight_value in data:
            vg.add((vertex_index,), weight_value, 'ADD')

    if uvs_per_vertex:
        uv_layer = me_ob.uv_layers.new(name=name)
        per_loop_list = []
        for loop in me_ob.loops:
            offset = loop.vertex_index * 2
            per_loop_list.extend((uvs_per_vertex[offset], uvs_per_vertex[offset + 1]))
        uv_layer.data.foreach_set('uv', per_loop_list)

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
        uv_layer.data.foreach_set('uv', per_loop_list)
    
    # vertex colors import for static meshes 
    if mesh.vertex_format == 0 and mesh_material.unk_flag_8_bones_vertex:
        me_ob.vertex_colors.new(name="imported_colors")
        color_layer = me_ob.vertex_colors["imported_colors"]
        for poly in me_ob.polygons:
            # loop through all loops in the polygon
            for loop_index in poly.loop_indices:
                #print("loop index is {}".format(loop_index))
                # get the loop object
                loop = me_ob.loops[loop_index]
                # check if the loop's vertex index matches the desired one
                if vertex_colors[loop.vertex_index]:
                    # set the color of the loop to red
                    #color_layer.data[loop_index].color = (0.0, 1.0, 0.0, 1.0)
                    color_layer.data[loop_index].color = vertex_colors [loop.vertex_index]

    # Saving unknown metadata for export
    # TODO: use a util function
    for field_tuple in mesh._fields_:
        attr_name = field_tuple[0]
        if not attr_name.startswith('unk_'):
            continue
        attr_value = getattr(mesh, attr_name)
        setattr(me_ob, attr_name, attr_value)

    return ob


def _import_vertices(mod, mesh):
    return _import_vertices_mod156(mod, mesh)


def _import_vertices_mod156(mod, mesh):
    vertices_array = get_vertices_array(mod, mesh) # get vertices according to vertex format
    material_array = mod.materials_data_array

    if mesh.vertex_format != 0:
        locations = (transform_vertices_from_bbox(vf, mod)
                     for vf in vertices_array)
    else:
        locations = ((vf.position_x, vf.position_y, vf.position_z) for vf in vertices_array)

    locations = map(lambda t: (t[0] / 100, t[2] / -100, t[1] / 100), locations)
    # from [0, 255] o [-1, 1]
    normals = map(lambda v: (((v.normal_x / 255) * 2) - 1,
                             ((v.normal_y / 255) * 2) - 1,
                             ((v.normal_z / 255) * 2) - 1), vertices_array)
    # y up to z up
    normals = map(lambda n: (n[0], n[2] * -1, n[1]), normals)
    uvs = [(unpack_half_float(v.uv_x), (1- unpack_half_float(v.uv_y))) for v in vertices_array]
    sorted_vertex_colors = []
    # XXX: normalmap has uvs as well? and then this should be uv3?
    if mesh.vertex_format == 0:
        uvs2 = [(unpack_half_float(v.uv2_x), (unpack_half_float(v.uv2_y) * -1) +1) for v in vertices_array]
        # from [0, 255] to [0.0, 1]
        if material_array[mesh.material_index].unk_flag_8_bones_vertex:
            uvs3 = []
            vertex_colors = map (lambda v: ((v.uv3_x & 0xFF) / 255,
                                            (v.uv3_x>>8 & 0xFF) / 255,
                                            (v.uv3_y & 0xFF) / 255,
                                            (v.uv3_y>>8 & 0xFF) / 255
                                            ),vertices_array)
            vertex_colors = list(chain.from_iterable(vertex_colors))
            # pack colors to a list
            for vc in range(len(vertex_colors)//4):
                i = vc * 4
                b = vertex_colors[i]
                g = vertex_colors[(i+1)]
                r = vertex_colors[(i+2)]
                a = vertex_colors[(i+3)]
                sorted_vertex_colors.append((r, g, b, a))
        else:
            uvs3 = [(unpack_half_float(v.uv3_x), (unpack_half_float(v.uv3_y) * -1) + 1) for v in vertices_array]
    else:
        uvs2 = []
        uvs3 = []
    return {'locations': list(locations),
            'normals': list(normals),
            'uvs': list(chain.from_iterable(uvs)),
            'uvs2': list(chain.from_iterable(uvs2)),
            'uvs3': list(chain.from_iterable(uvs3)),
            'vertex_colors': list(sorted_vertex_colors),
            'weights_per_bone': _get_weights_per_bone(mod, mesh, vertices_array)
            }


def _get_path_to_albam():
    for mod in addon_utils.modules():
        if mod.bl_info['name'] == "Albam Reloaded":
            filepath = mod.__file__
            path = os.path.split(filepath)[0]
            return (path)
        else:
            pass

def _create_dummy_texture(i, path):
    texture_name_no_extension = os.path.splitext(os.path.basename(path))[0]
    texture_name_no_extension = str(i).zfill(2) + texture_name_no_extension
    texture = bpy.data.textures.new(texture_name_no_extension, type='IMAGE')
    texture.use_fake_user = True

    image_path = _get_path_to_albam()
    image_path = os.path.join(image_path, "resourses", "missing texture.dds")
    dummy_image = bpy.data.images.load(image_path)

    texture.image = dummy_image
    texture_node_name = texture_name_no_extension + ".dds"
    texture.image.name = texture_node_name
    return texture


def _create_blender_textures_from_mod(mod, base_dir):
    textures = [None]  # materials refer to textures in index-1
    # TODO: check why in Arc.header.file_entries[n].file_path it returns a bytes, and
    # here the whole array of chars

    for i, texture_path in enumerate(mod.textures_array):
        path = texture_path[:].decode('ascii').partition('\x00')[0] # relative path to a texture in the ARC archive without extension
        path = os.path.join(base_dir, *path.split(ntpath.sep))# full path to a texture
        path = '.'.join((path, 'tex')) # full path to a texture with .tex extension
        if not os.path.isfile(path):
            # TODO: log warnings, figure out 'rtex' format
            print('path {} does not exist'.format(path))
            # add a placeholder instead of the missing texure
            dummy_texture =_create_dummy_texture(i, path)
            textures.append(dummy_texture) 
            continue
        tex = Tex112(path)
        try:
            dds = tex.to_dds()
        except TextureError as err:
            # TODO: log this instead of printing it
            print('Error converting "{}"to dds: {}'.format(path, err))
            dummy_texture = _create_dummy_texture(i, path)
            textures.append(dummy_texture) 
            continue
        dds_path = path.replace('.tex', '.dds') # change extension in the full path
        with open(dds_path, 'wb') as w: #write bynary
            w.write(dds)
        image = bpy.data.images.load(dds_path, check_existing=True)
        texture_name_no_extension = os.path.splitext(os.path.basename(path))[0]
        #texture_name_no_extension = str(i).zfill(2) + texture_name_no_extension
        texture = bpy.data.textures.get(texture_name_no_extension)
        # Create a texture data block if not exist
        if not texture:
            texture = bpy.data.textures.new(texture_name_no_extension, type='IMAGE') # bpy.data.textures['00pl0200_09AllHair_BM']
            texture.use_fake_user = True # Set fake user to prevent removing after saving to .blend
            texture.image = image 
        textures.append(texture) #create a list with bpy.data.textures

        # saving meta data for export
        # TODO: use a util function
        for field_tuple in tex._fields_:
            attr_name = field_tuple[0]
            if not attr_name.startswith('unk_'):
                continue
            attr_value = getattr(tex, attr_name)
            setattr(texture, attr_name, attr_value)

    return textures


def _create_blender_materials_from_mod(mod, model_name, textures):
    '''textures: bpy.data.textures'''
    materials = []
    existed_textures = []
    if not bpy.data.node_groups.get("MT Framework shader"):
        shader_node = create_shader_node_group()

    for i, material in enumerate(mod.materials_data_array):
        blender_material = bpy.data.materials.new('{}_{}'.format(model_name, str(i).zfill(2)))
        blender_material.use_nodes = True
        blender_material.blend_method = 'CLIP' # set transparency method 'OPAQUE', 'CLIP', 'HASHED', 'BLEND'
        #blender_material.alpha_treshhold = 0.33

        node_to_delete = blender_material.node_tree.nodes.get("Principled BSDF")
        if node_to_delete:
            blender_material.node_tree.nodes.remove( node_to_delete )
        #principled_node.inputs['Specular'].default_value = 0.2 # change specular
        shader_node_group = blender_material.node_tree.nodes.new('ShaderNodeGroup')
        shader_node_group.node_tree = bpy.data.node_groups["MT Framework shader"]
        shader_node_group.name = "MTFrameworkGroup"
        shader_node_group.width = 300
        material_output = blender_material.node_tree.nodes.get("Material Output")
        material_output.location = (400, 0)

        link = blender_material.node_tree.links.new
        link(shader_node_group.outputs[0], material_output.inputs[0])

        # unknown data for export, registered already
        # TODO: do this with a util function
        for field_tuple in material._fields_: # add custom properties to material
            attr_name = field_tuple[0]
            if not attr_name.startswith('unk_'):
                continue
            attr_value = getattr(material, attr_name)
            setattr(blender_material, attr_name, attr_value)
        materials.append(blender_material)

        for texture_code, tex_index in enumerate(material.texture_indices):
            if not tex_index:
                continue
            try:
                texture_target = textures[tex_index]
            except IndexError:
                # TODO
                print('tex_index {} not found. Texture len(): {}'.format(tex_index, len(textures)))
                continue
            if not texture_target:
                # This means the conversion failed before
                # TODO: logging
                continue
            #if texture_code == 6:
            #    print('texture_code not supported', texture_code)
            #    continue
            texture_node = blender_material.node_tree.nodes.new('ShaderNodeTexImage') 
            texture_code_to_blender_texture(texture_code, texture_node, blender_material)
            texture_node.image = texture_target.image # set bpy.data.textures[].image as a texures for ShaderNodeTexImage
            if  texture_code  == 1 or texture_code  == 7: # change color settings for normal and detail maps
                texture_node.image.colorspace_settings.name = 'Non-Color'

    return materials


def _create_blender_armature_from_mod(blender_object, mod, armature_name):
    armature = bpy.data.armatures.new(armature_name)
    armature_ob = bpy.data.objects.new(armature_name, armature)
    armature_ob.parent = blender_object

    #set to Object mode
    if bpy.context.mode != 'OBJECT': 
        bpy.ops.object.mode_set(mode='OBJECT')
    # deselect all objects
    for i in bpy.context.scene.objects:
        i.select_set(False)
    bpy.context.collection.objects.link(armature_ob)
    bpy.context.view_layer.objects.active = armature_ob
    armature_ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')

    blender_bones = []
    non_deform_bone_indices = get_non_deform_bone_indices(mod)

    for i, bone in enumerate(mod.bones_array): # add counter to the array
        blender_bone = armature.edit_bones.new(str(i))

        if i in non_deform_bone_indices:
            blender_bone.use_deform = False
        parents = get_bone_parents_from_mod(bone, mod.bones_array)
        if not parents:
            blender_bone.head = Vector((bone.location_x / 100,
                                        bone.location_z * -1 / 100,
                                        bone.location_y / 100))
            blender_bone.tail = Vector((blender_bone.head[0], blender_bone.head[1], blender_bone.head[2] + 0.01))
        else:
            chain = [i] + parents
            wtm = Matrix.Translation((0, 0, 0))
            for bi in reversed(chain):
                b = mod.bones_array[bi]
                wtm = wtm @ Matrix.Translation((b.location_x / 100, b.location_z / 100 * -1, b.location_y / 100))
            blender_bone.head = wtm.to_translation()
            blender_bone.parent = blender_bones[bone.parent_index]

        blender_bone.tail = Vector((blender_bone.head[0], blender_bone.head[1], blender_bone.head[2] + 0.01))
        blender_bones.append(blender_bone)


    assert len(blender_bones) == len(mod.bones_array)


    bpy.ops.object.mode_set(mode='OBJECT')
    assert len(armature.bones) == len(mod.bones_array)

    _create_bone_groups(armature_ob, mod)
    return armature_ob


def _create_bone_groups(armature_ob, mod):
    bone_groups_cache = {
        'BONE_GROUP_MAIN': {
            'color_set': 'THEME03',
            'name': 'Main',
            'layer': 1,
            },
        'BONE_GROUP_ARMS': {
            'color_set': 'THEME02',
            'name': 'Arms',
            'layer': 2,
            },
        'BONE_GROUP_LEGS': {
            'color_set': 'THEME05',
            'name': 'Legs',
            'layer': 3,
            },
        'BONE_GROUP_HANDS': {
            'color_set': 'THEME06',
            'name': 'Hands',
            'layer': 4,
            },
        'BONE_GROUP_HAIR': {
            'color_set': 'THEME07',
            'name': 'Hair',
            'layer': 5,
            },
        'BONE_GROUP_FACIAL_BASIC': {
            'color_set': 'THEME02',
            'name': 'Facial Basic',
            'layer': 6,
            },
        'BONE_GROUP_FACIAL': {
            'color_set': 'THEME01',
            'name': 'Facial',
            'layer': 7,
            },
        'BONE_GROUP_ACCESORIES': {
            'color_set': 'THEME14',
            'name': 'Accessories',
            'layer': 8,
            },
        'OTHER': {
            'color_set': 'THEME20',
            'name': 'Other',
            'layer': 9,
            },
    }

    bpy.ops.object.mode_set(mode='POSE')
    for i, bone in enumerate(armature_ob.pose.bones):
        source_bone = mod.bones_array[i]
        anim_index = source_bone.anim_map_index
        bone.bone_group = _get_or_create_bone_group(anim_index, armature_ob, i, bone_groups_cache)
    bpy.ops.object.mode_set(mode='OBJECT')


def _get_or_create_bone_group(bone_anim_index, armature_ob, bone_index, bone_groups_cache):
    bone_group_name = BONE_INDEX_TO_GROUP.get(bone_anim_index, 'OTHER')

    bone_group_cache = bone_groups_cache.get(bone_group_name) or bone_groups_cache['OTHER']
    layer_index = bone_group_cache['layer']
    _move_bone_to_layers(armature_ob, bone_index, 0, layer_index)

    if bone_group_cache.get('bl_group'):
        return bone_group_cache['bl_group']

    bl_bone_group = armature_ob.pose.bone_groups.new(name=bone_group_cache['name'])
    bl_bone_group.color_set = bone_group_cache['color_set']
    bone_group_cache['bl_group'] = bl_bone_group

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
    if not mod.bone_count or not hasattr(vertices_array[0], 'bone_indices'):
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

    return f'{mesh_name}_{mesh_index}'
