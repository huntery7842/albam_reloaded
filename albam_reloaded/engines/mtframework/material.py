import ntpath
import os

import addon_utils
import bpy

from albam_reloaded.exceptions import TextureError
from . import Tex112
from .utils import texture_code_to_blender_texture


def _create_blender_textures_from_mod(mod, base_dir):
    textures = [None]  # materials refer to textures in index-1
    # TODO: check why in Arc.header.file_entries[n].file_path it returns a bytes, and
    # here the whole array of chars

    for i, texture_path in enumerate(mod.textures_array):
        path = (
            texture_path[:].decode("ascii").partition("\x00")[0]
        )  # relative path to a texture in the ARC archive without extension
        path = os.path.join(base_dir, *path.split(ntpath.sep))  # full path to a texture
        path = ".".join((path, "tex"))  # full path to a texture with .tex extension
        if not os.path.isfile(path):
            # TODO: log warnings, figure out 'rtex' format
            print("path {} does not exist".format(path))
            # add a placeholder instead of the missing texure
            texture_name_no_extension = os.path.splitext(os.path.basename(path))[0]
            texture_name_no_extension = str(i).zfill(2) + texture_name_no_extension
            texture = bpy.data.textures.new(texture_name_no_extension, type="IMAGE")
            texture.use_fake_user = True

            image_path = _get_path_to_albam()
            image_path = os.path.join(image_path, "resourses", "missing texture.dds")
            dummy_image = bpy.data.images.load(image_path)

            texture.image = dummy_image
            texture_node_name = texture_name_no_extension + ".dds"
            texture.image.name = texture_node_name
            textures.append(texture)
            continue
        tex = Tex112(path)
        try:
            dds = tex.to_dds()
        except TextureError as err:
            # TODO: log this instead of printing it
            print('Error converting "{}"to dds: {}'.format(path, err))
            textures.append(None)
            continue
        dds_path = path.replace(".tex", ".dds")  # change extension in the full path
        with open(dds_path, "wb") as w:  # write bynary
            w.write(dds)
        image = bpy.data.images.load(dds_path, check_existing=True)
        texture_name_no_extension = os.path.splitext(os.path.basename(path))[0]
        texture_name_no_extension = str(i).zfill(2) + texture_name_no_extension
        texture = bpy.data.textures.get(texture_name_no_extension)
        # Create a texture data block if not exist
        if not texture:
            texture = bpy.data.textures.new(
                texture_name_no_extension, type="IMAGE"
            )  # bpy.data.textures['00pl0200_09AllHair_BM']
            texture.use_fake_user = True  # Set fake user to prevent removing after saving to .blend
            texture.image = image
        textures.append(texture)  # create a list with bpy.data.textures
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


def _create_blender_materials_from_mod(mod, model_name, textures):
    """textures: bpy.data.textures"""
    materials = []
    if not bpy.data.node_groups.get("MT Framework shader"):
        _create_shader_node_group()

    for i, material in enumerate(mod.materials_data_array):
        blender_material = bpy.data.materials.new("{}_{}".format(model_name, str(i).zfill(2)))
        blender_material.use_nodes = True
        blender_material.blend_method = (
            "CLIP"  # set transparency method 'OPAQUE', 'CLIP', 'HASHED', 'BLEND'
        )
        # blender_material.alpha_treshhold = 0.33

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
        materials.append(blender_material)

        for texture_code, tex_index in enumerate(material.texture_indices):
            if not tex_index:
                continue
            try:
                texture_target = textures[tex_index]
            except IndexError:
                # TODO
                print("tex_index {} not found. Texture len(): {}".format(tex_index, len(textures)))
                continue
            if not texture_target:
                # This means the conversion failed before
                # TODO: logging
                continue
            if texture_code == 6:
                print("texture_code not supported", texture_code)
                continue
            texture_node = blender_material.node_tree.nodes.new("ShaderNodeTexImage")
            texture_code_to_blender_texture(texture_code, texture_node, blender_material)
            texture_node.image = (
                texture_target.image
            )  # set bpy.data.textures[].image as a texures for ShaderNodeTexImage
            if (
                texture_code == 1 or texture_code == 7
            ):  # change color settings for normal and detail maps
                texture_node.image.colorspace_settings.name = "Non-Color"

    return materials


def _get_path_to_albam():
    for mod in addon_utils.modules():
        if mod.bl_info["name"] == "Albam Reloaded":
            filepath = mod.__file__
            path = os.path.split(filepath)[0]
            return path
        else:
            pass
