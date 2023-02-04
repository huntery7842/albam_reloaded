from enum import Enum
import io
import os
from pathlib import PureWindowsPath

import addon_utils
import bpy
from kaitaistruct import KaitaiStream

from albam_reloaded.lib.dds import DDSHeader
from . import EXTENSION_TO_FILE_ID
from .structs.tex_112 import Tex112
from .structs.tex_157 import Tex157
from .structs.mrl import Mrl


TEX_FORMAT_MAPPER = {
    19: b'DXT1',
    20: b'DXT1',
    23: b'DXT5',
    24: b'DXT5',
    24: b'DXT5',
    25: b'DXT5',
    31: b'DXT5',
    'DXT1': b'DXT1',
    'DXT5': b'DXT5',
}


TEX_VERSION_MAPPER = {
    156: Tex112,
    210: Tex157,
}


class TextureTypes(Enum):
    DIFFUSE = 1
    NORMAL = 2
    SPECULAR = 3
    LIGHTMAP = 4
    UNK_01 = 5
    ALPHAMAP = 6
    ENVMAP = 7
    NORMAL_DETAIL = 8


TEX_TYPE_MAPPER = {
    0x345dcdc3: TextureTypes.DIFFUSE,  # RER
    0x349dcdc3: TextureTypes.DIFFUSE,  # RE1
    0x347dcdc3: TextureTypes.DIFFUSE,  # RE6
    0x350dcdc3: TextureTypes.DIFFUSE,  # RE0
    0x34cdcdc3: TextureTypes.NORMAL,  # RE1
    0x34adcdc3: TextureTypes.NORMAL,  # RE6
    0x353dcdc3: TextureTypes.NORMAL,  # RE0
}


def build_blender_materials(arc, mod, name_prefix="material", mod_file_entry=None):
    materials = {}
    mrl = _infer_mrl(arc, mod_file_entry)
    if mod.header.version != 156 and not mrl:
        return materials

    textures = build_blender_textures(arc, mod, mrl)
    if mod.header.version == 156:
        src_materials = mod.materials
    else:
        src_materials = mrl.materials

    if not bpy.data.node_groups.get("MT Framework shader"):
        _create_shader_node_group()

    for idx_material, material in enumerate(src_materials):
        blender_material = bpy.data.materials.new(f"{name_prefix}_{str(idx_material).zfill(2)}")
        blender_material.use_nodes = True
        # set transparency method 'OPAQUE', 'CLIP', 'HASHED', 'BLEND'
        blender_material.blend_method = "CLIP"
        node_to_delete = blender_material.node_tree.nodes.get("Principled BSDF")
        blender_material.node_tree.nodes.remove(node_to_delete)
        # principled_node.inputs['Specular'].default_value = 0.2 # change specular
        shader_node_group = blender_material.node_tree.nodes.new("ShaderNodeGroup")
        shader_node_group.node_tree = bpy.data.node_groups["MT Framework shader"]
        shader_node_group.name = "MTFrameworkGroup"
        shader_node_group.width = 300
        material_output = blender_material.node_tree.nodes.get("Material Output")
        material_output.location = (400, 0)
        link = blender_material.node_tree.links.new
        link(shader_node_group.outputs[0], material_output.inputs[0])

        _assign_textures(material, blender_material, textures, from_mrl=bool(mrl))

        if not bool(mrl):
            materials[idx_material] = blender_material
        else:
            materials[material.name_hash_crcjam32] = blender_material

    return materials


def _assign_textures(mtfw_material, bl_material, textures, from_mrl=False):

    for texture_type in TextureTypes:

        tex_index = _find_texture_index(mtfw_material, texture_type, from_mrl)
        if tex_index == 0:
            continue
        try:
            texture_target = textures[tex_index]
        except IndexError:
            print(f"tex_index {tex_index} not found. Texture len(): {len(textures)}")
            continue
        if texture_target is None:
            # This means the conversion failed before
            continue
        if texture_type.value == 6:
            print("texture_type not supported", texture_type)
            continue
        texture_node = bl_material.node_tree.nodes.new("ShaderNodeTexImage")
        texture_code_to_blender_texture(texture_type.value, texture_node, bl_material)
        texture_node.image = texture_target
        # change color settings for normal and detail maps
        if texture_type.value == 2 or texture_type.value == 8:
            texture_node.image.colorspace_settings.name = "Non-Color"


def _find_texture_index(mtfw_material, texture_type, from_mrl=False):
    tex_index = 0

    if from_mrl is False:
        tex_index = mtfw_material.texture_slots[texture_type.value - 1]
    else:
        for resource in mtfw_material.resources:
            if TEX_TYPE_MAPPER.get(resource.resource_type) == texture_type:
                tex_index = resource.resource_index
                break
    return tex_index


def _get_path_to_albam():
    for mod in addon_utils.modules():
        if mod.bl_info["name"] == "Albam Reloaded":
            filepath = mod.__file__
            path = os.path.split(filepath)[0]
            return path
        else:
            pass


def build_blender_textures(arc, mod, mrl=None):
    textures = [None]  # materials refer to textures in index-1
    tex_type = EXTENSION_TO_FILE_ID['tex']

    src_textures = getattr(mod, 'textures', None) or getattr(mrl, 'textures', None)
    if not src_textures:
        return textures
    TexCls = TEX_VERSION_MAPPER[mod.header.version]

    for i, texture_slot in enumerate(src_textures):
        texture_path = getattr(texture_slot, 'texture_path', None) or texture_slot
        tex_buffer = arc.get_file(texture_path, tex_type)
        if not tex_buffer:
            print(f'texture_path {texture_path} not found in arc')
            textures.append(None)
            # TODO: handle missing texture
            continue
        tex = TexCls(KaitaiStream(io.BytesIO(tex_buffer)))
        try:
            dds_header = DDSHeader(
                dwHeight=tex.height,
                dwWidth=tex.width,
                dwMipMapCount=tex.num_mipmaps_per_image // tex.num_images,
                pixelfmt_dwFourCC=TEX_FORMAT_MAPPER[tex.compression_format],
            )
            dds_header.set_constants()
            dds_header.set_variables()
            dds = bytes(dds_header) + tex.dds_data
        except Exception as err:
            # TODO: log this instead of printing it
            print(f'Error converting "{texture_path}" to dds: {err}')
            textures.append(None)
            continue

        tex_name = PureWindowsPath(texture_path).name
        bl_image = bpy.data.images.new(f'{tex_name}.dds', tex.width, tex.height)
        bl_image.source = 'FILE'
        bl_image.pack(data=dds, data_len=len(dds))
        textures.append(bl_image)

    return textures


def _create_shader_node_group():
    """Creates shader node group to hide all nodes from users under the hood"""

    shader_group = bpy.data.node_groups.new("MT Framework shader", "ShaderNodeTree")
    group_inputs = shader_group.nodes.new("NodeGroupInput")
    group_inputs.location = (-2000, -200)

    # Create group inputs
    shader_group.inputs.new("NodeSocketColor", "Diffuse BM")
    shader_group.inputs.new("NodeSocketFloat", "Alpha BM")
    shader_group.inputs["Alpha BM"].default_value = 1
    shader_group.inputs.new("NodeSocketColor", "Normal NM")
    shader_group.inputs["Normal NM"].default_value = (1, 0.5, 1, 1)
    shader_group.inputs.new("NodeSocketFloat", "Alpha NM")
    shader_group.inputs["Alpha NM"].default_value = 0.5
    shader_group.inputs.new("NodeSocketColor", "Specular MM")
    # shader_group.inputs["Specular MM"].default_value = 1
    shader_group.inputs.new("NodeSocketColor", "Lightmap LM")
    shader_group.inputs.new("NodeSocketInt", "Use Lightmap")
    shader_group.inputs["Use Lightmap"].min_value = 0
    shader_group.inputs["Use Lightmap"].max_value = 1
    shader_group.inputs.new("NodeSocketColor", "Alpha Mask AM")
    shader_group.inputs.new("NodeSocketInt", "Use Alpha Mask")
    shader_group.inputs["Use Alpha Mask"].min_value = 0
    shader_group.inputs["Use Alpha Mask"].max_value = 1
    shader_group.inputs.new("NodeSocketColor", "Environment CM")
    shader_group.inputs.new("NodeSocketColor", "Detail DNM")
    shader_group.inputs["Detail DNM"].default_value = (1, 0.5, 1, 1)
    shader_group.inputs.new("NodeSocketFloat", "Alpha DNM")
    shader_group.inputs["Alpha DNM"].default_value = 0.5
    shader_group.inputs.new("NodeSocketInt", "Use Detail Map")
    shader_group.inputs["Use Detail Map"].min_value = 0
    shader_group.inputs["Use Detail Map"].max_value = 1

    # Create group outputs
    group_outputs = shader_group.nodes.new("NodeGroupOutput")
    group_outputs.location = (300, -90)
    shader_group.outputs.new("NodeSocketShader", "Surface")

    # Shader node
    bsdf_shader = shader_group.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf_shader.location = (0, -90)

    # Mix a diffuse map and a lightmap
    multiply_diff_light = shader_group.nodes.new("ShaderNodeMixRGB")
    multiply_diff_light.name = "mult_diff_and_light"
    multiply_diff_light.label = "Multiply with Lightmap"
    multiply_diff_light.blend_type = "MULTIPLY"
    multiply_diff_light.inputs[0].default_value = 0.8
    multiply_diff_light.location = (-450, -100)

    # RGB nodes
    normal_separate = shader_group.nodes.new("ShaderNodeSeparateRGB")
    normal_separate.name = "separate_normal"
    normal_separate.label = "Separate Normal"
    normal_separate.location = (-1700, -950)

    normal_combine = shader_group.nodes.new("ShaderNodeCombineRGB")
    normal_combine.name = "combine_normal"
    normal_combine.label = "Combine Normal"
    normal_combine.location = (-1500, -900)

    detail_separate = shader_group.nodes.new("ShaderNodeSeparateRGB")
    detail_separate.name = "separate_detail"
    detail_separate.label = "Separate Detail"
    detail_separate.location = (-1700, -1100)

    detail_combine = shader_group.nodes.new("ShaderNodeCombineRGB")
    detail_combine.name = "combine_detail"
    detail_combine.label = "Combine Detail"
    detail_combine.location = (-1500, -1050)

    separate_rgb_n = shader_group.nodes.new("ShaderNodeSeparateRGB")
    separate_rgb_n.name = "separate_rgb_n"
    separate_rgb_n.label = "Separate RGB N"
    separate_rgb_n.location = (-1250, -1050)

    separate_rgb_d = shader_group.nodes.new("ShaderNodeSeparateRGB")
    separate_rgb_d.name = "separate_rgb_d"
    separate_rgb_d.label = "Separate RGB D"
    separate_rgb_d.location = (-1250, -1250)

    combine_all_normals = shader_group.nodes.new("ShaderNodeCombineRGB")
    combine_all_normals.name = "combine_all_normals"
    combine_all_normals.label = "Combine All Normals"
    combine_all_normals.location = (-750, -1150)

    # Curve RGB for correct normal map display in blender
    invert_green = shader_group.nodes.new("ShaderNodeRGBCurve")
    invert_green.location = (-250, -1000)
    curve_g = invert_green.mapping.curves[1]
    curve_g.points[0].location = (1, 0)
    curve_g.points[1].location = (0, 1)
    invert_green.mapping.update()

    # Normalize normals nodes
    normalize_normals = shader_group.nodes.new("ShaderNodeVectorMath")
    normalize_normals.operation = "NORMALIZE"
    normalize_normals.name = "normalize_normals"
    normalize_normals.label = "Normalize Normals"
    normalize_normals.location = (-590, -1050)

    # Add nodes
    add_normals_red = shader_group.nodes.new("ShaderNodeMixRGB")
    add_normals_red.blend_type = "ADD"
    add_normals_red.name = "add_normals_red"
    add_normals_red.label = "Add Normals Red"
    add_normals_red.location = (-1000, -980)

    add_normals_green = shader_group.nodes.new("ShaderNodeMixRGB")
    add_normals_green.blend_type = "ADD"
    add_normals_green.name = "add_normals_green"
    add_normals_green.label = "Add Normals Green"
    add_normals_green.location = (-1000, -1200)

    add_normals_blue = shader_group.nodes.new("ShaderNodeMixRGB")
    add_normals_blue.blend_type = "ADD"
    add_normals_blue.name = "add_normals_blue"
    add_normals_blue.label = "Add Normals Blue"
    add_normals_blue.location = (-1000, -1420)

    # Invert node
    invert_spec = shader_group.nodes.new("ShaderNodeInvert")
    invert_spec.location = (-200, -350)

    # Normal node
    normal_map = shader_group.nodes.new("ShaderNodeNormalMap")  # create normal map node
    normal_map.inputs[0].default_value = 1.5
    normal_map.location = (-200, -720)

    # Logic gates
    use_lightmap = shader_group.nodes.new("ShaderNodeMixRGB")
    use_lightmap.name = "switch_lightmap"
    use_lightmap.label = "Lightmap Switcher"
    use_lightmap.location = (-200, -150)

    use_alpha_mask = shader_group.nodes.new("ShaderNodeMixRGB")
    use_alpha_mask.name = "switch_alpha_mask"
    use_alpha_mask.label = "Alpha Mask Switcher"
    use_alpha_mask.location = (-200, -500)

    use_detail_map = shader_group.nodes.new("ShaderNodeMixRGB")
    use_detail_map.name = "switch_detail_map"
    use_detail_map.label = "Detail Mask Switcher"
    use_detail_map.location = (-440, -825)

    # Link nodes
    link = shader_group.links.new

    link(bsdf_shader.outputs[0], group_outputs.inputs[0])
    link(group_inputs.outputs[0], multiply_diff_light.inputs[1])
    link(multiply_diff_light.outputs[0], use_lightmap.inputs[2])
    link(group_inputs.outputs[0], use_lightmap.inputs[1])
    link(use_lightmap.outputs[0], bsdf_shader.inputs[0])
    link(group_inputs.outputs[1], use_alpha_mask.inputs[1])
    link(use_alpha_mask.outputs[0], bsdf_shader.inputs[21])
    link(group_inputs.outputs[2], normal_separate.inputs[0])
    link(normal_separate.outputs[1], normal_combine.inputs[1])
    link(normal_separate.outputs[2], normal_combine.inputs[2])
    link(group_inputs.outputs[3], normal_combine.inputs[0])
    link(normal_combine.outputs[0], use_detail_map.inputs[1])
    link(normal_combine.outputs[0], separate_rgb_n.inputs[0])

    link(group_inputs.outputs[4], invert_spec.inputs[1])
    link(invert_spec.outputs[0], bsdf_shader.inputs[9])
    link(group_inputs.outputs[5], multiply_diff_light.inputs[2])
    link(group_inputs.outputs[6], use_lightmap.inputs[0])
    link(group_inputs.outputs[7], use_alpha_mask.inputs[2])  # use alpha mask > color 2
    link(group_inputs.outputs[8], use_alpha_mask.inputs[0])  # use alpha mask int

    link(group_inputs.outputs[10], detail_separate.inputs[0])
    link(group_inputs.outputs[11], detail_combine.inputs[0])
    link(detail_separate.outputs[1], detail_combine.inputs[1])
    link(detail_separate.outputs[2], detail_combine.inputs[2])
    link(detail_combine.outputs[0], separate_rgb_d.inputs[0])

    link(separate_rgb_n.outputs[0], add_normals_red.inputs[1])
    link(separate_rgb_d.outputs[0], add_normals_red.inputs[2])
    link(separate_rgb_n.outputs[1], add_normals_green.inputs[1])
    link(separate_rgb_d.outputs[1], add_normals_green.inputs[2])
    link(separate_rgb_n.outputs[2], add_normals_blue.inputs[1])
    link(separate_rgb_d.outputs[2], add_normals_blue.inputs[2])
    link(add_normals_red.outputs[0], combine_all_normals.inputs[0])
    link(add_normals_green.outputs[0], combine_all_normals.inputs[1])
    link(add_normals_blue.outputs[0], combine_all_normals.inputs[2])

    link(combine_all_normals.outputs[0], normalize_normals.inputs[0])
    link(normalize_normals.outputs[0], use_detail_map.inputs[2])
    link(use_detail_map.outputs[0], invert_green.inputs[1])
    link(invert_green.outputs[0], normal_map.inputs[1])
    link(normal_map.outputs[0], bsdf_shader.inputs[22])
    link(group_inputs.outputs[12], use_detail_map.inputs[0])

    return shader_group


def texture_code_to_blender_texture(texture_code, blender_texture_node, blender_material):
    """
    Function for detecting texture type and map it to blender shader sockets
    texture_code : index for detecting type of a texture
    blender_texture_node : image texture node
    blender_material : shader material
    """
    # blender_texture_node.use_map_alpha = True
    shader_node_grp = blender_material.node_tree.nodes.get("MTFrameworkGroup")
    link = blender_material.node_tree.links.new

    if texture_code == 1:
        # Diffuse _BM
        link(blender_texture_node.outputs["Color"], shader_node_grp.inputs[0])
        link(blender_texture_node.outputs["Alpha"], shader_node_grp.inputs[1])
        blender_texture_node.location = (-300, 350)
        # blender_texture_node.use_map_color_diffuse = True
    elif texture_code == 2:
        # Normal _NM
        blender_texture_node.location = (-300, 0)
        link(blender_texture_node.outputs["Color"], shader_node_grp.inputs[2])
        link(blender_texture_node.outputs["Alpha"], shader_node_grp.inputs[3])

    elif texture_code == 3:
        # Specular _MM
        blender_texture_node.location = (-300, -350)
        link(blender_texture_node.outputs["Color"], shader_node_grp.inputs[4])

    elif texture_code == 4:
        # Lightmap _LM
        blender_texture_node.location = (-300, -700)
        uv_map_node = blender_material.node_tree.nodes.new("ShaderNodeUVMap")
        uv_map_node.location = (-500, -700)
        uv_map_node.uv_map = "lightmap"
        link(uv_map_node.outputs[0], blender_texture_node.inputs[0])
        link(blender_texture_node.outputs["Color"], shader_node_grp.inputs[5])
        shader_node_grp.inputs[6].default_value = 1

    elif texture_code == 5:
        # Emissive mask ?
        blender_texture_node.location = (-300, -1050)

    elif texture_code == 6:
        # Alpha mask _AM
        blender_texture_node.location = (-300, -1400)
        link(blender_texture_node.outputs["Color"], shader_node_grp.inputs[7])
        shader_node_grp.inputs[8].default_value = 1

    elif texture_code == 8:
        # Detail normal map
        blender_texture_node.location = (-300, -1750)
        tex_coord_node = blender_material.node_tree.nodes.new("ShaderNodeTexCoord")
        tex_coord_node.location = (-700, -1750)
        mapping_node = blender_material.node_tree.nodes.new("ShaderNodeMapping")
        mapping_node.location = (-500, -1750)

        link(tex_coord_node.outputs[2], mapping_node.inputs[0])
        link(mapping_node.outputs[0], blender_texture_node.inputs[0])
        link(blender_texture_node.outputs["Color"], shader_node_grp.inputs[10])
        link(blender_texture_node.outputs["Alpha"], shader_node_grp.inputs[11])

        shader_node_grp.inputs[12].default_value = 1
        # TODO move it to function
        # Link the material properites value
        for x in range(3):
            d = mapping_node.inputs[3].driver_add("default_value", x)
            var1 = d.driver.variables.new()
            var1.name = "detail_multiplier"
            var1.targets[0].id_type = "MATERIAL"
            var1.targets[0].id = blender_material
            var1.targets[0].data_path = '["unk_detail_factor"]'
            d.driver.expression = var1.name
    else:
        print("texture_code not supported", texture_code)
        # TODO: 7 CM cubemap


def _infer_mrl(arc, mod_file_entry):
    """
    Assuming mrl file is next to the .mod file with
    the same name.
    It's not always like this, e.g. RE6
    """
    if not mod_file_entry:
        return
    mrl_type = EXTENSION_TO_FILE_ID['mrl']

    mrl_file = arc.get_file(mod_file_entry.file_path, mrl_type)
    if not mrl_file:
        return
    mrl = Mrl(KaitaiStream(io.BytesIO(mrl_file)))
    return mrl


def _handle_missing_texture(path, index):
    texture_name_no_extension = os.path.splitext(os.path.basename(path))[0]
    texture_name_no_extension = str(index).zfill(2) + texture_name_no_extension
    texture = bpy.data.textures.new(texture_name_no_extension, type="IMAGE")
    texture.use_fake_user = True

    image_path = _get_path_to_albam()
    image_path = os.path.join(image_path, "resourses", "missing texture.dds")
    dummy_image = bpy.data.images.load(image_path)

    texture.image = dummy_image
    texture_node_name = texture_name_no_extension + ".dds"
    texture.image.name = texture_node_name

    return texture
