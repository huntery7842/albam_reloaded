import os

import bpy

from albam_reloaded.registry import blender_registry
from albam_reloaded.lib.blender import (
    show_message_box,
    split_UV_seams_operator,
    select_invalid_meshes_operator,
    transfer_normals,
)


class ALBAM_PT_ImportExportPanel(bpy.types.Panel):
    """UI Albam subpanel in 3D view"""

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Albam"
    bl_idname = "ALBAM_PT_UI_Panel"
    bl_label = "Albam"

    def draw(self, context):  # pragma: no cover
        self.layout.operator("albam_import.item", text="Import")


class ALBAM_PT_ToolsPanel(bpy.types.Panel):
    """UI Tool subpanel in 3D view"""

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Albam"
    bl_idname = "ALBAM_PT_TOOLS_Panel"
    bl_label = "Tools"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        scn = context.scene
        layout = self.layout
        layout.operator("albam_tools.fix_leaked_texures", text="Fix leaked textures")
        layout.operator("albam_tools.select_invalid_meshes", text="Select invalid meshes")
        layout.operator("albam_tools.remove_empty_vertex_groups", text="Remove empty vertex groups")
        layout.operator("albam_tools.transfer_normals", text="Transfer normals")
        layout.prop(scn, "albam_scene_meshes", text="from")


class AlbamImportOperator(bpy.types.Operator):
    """Import button operator"""

    DIRECTORY = bpy.props.StringProperty(subtype="DIR_PATH")
    FILES = bpy.props.CollectionProperty(name="adf", type=bpy.types.OperatorFileListElement)
    FILTER_GLOB = bpy.props.StringProperty(default="*.arc", options={"HIDDEN"})

    bl_idname = "albam_import.item"
    bl_label = "import item"
    directory: DIRECTORY
    files: FILES
    filter_glob: FILTER_GLOB

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        to_import = [
            os.path.join(self.directory, f.name) for f in self.files
        ]  # combine path to file and file name list to a new list
        for file_path in to_import:
            self._import_file(file_path=file_path)

        return {"FINISHED"}

    @staticmethod
    def _import_file(file_path):

        with open(file_path, "rb") as f:
            data = f.read()
        id_magic = data[:4]

        func = blender_registry.import_registry.get(id_magic)  # find header in dictionary
        if not func:
            raise TypeError(f"File not supported for import. Id magic: {id_magic}")

        # TODO: proper logging/raising and rollback if failure
        bl_container = func(file_path)

        bpy.context.collection.objects.link(bl_container)
        for child in bl_container.children_recursive:
            try:
                # already linked
                bpy.context.collection.objects.link(child)
            except RuntimeError:
                pass


class AlbamFixLeakedTexuresOperator(bpy.types.Operator):
    """Fix leaked texures button operator"""

    bl_idname = "albam_tools.fix_leaked_texures"
    bl_label = "fix leaked textures"

    @classmethod
    def poll(self, context):  # pragma: no cover
        if not bpy.context.selected_objects:
            return False
        return True

    def execute(self, context):
        selection = bpy.context.selected_objects
        selected_meshes = [obj for obj in selection if obj.type == "MESH"]
        if selected_meshes:
            split_UV_seams_operator(selected_meshes)
        else:
            show_message_box(message="There is no mesh in the selection")
        return {"FINISHED"}


class AlbamSelectInvalidMeshesOperator(bpy.types.Operator):
    """Select meshes with more than 32 influences"""

    bl_idname = "albam_tools.select_invalid_meshes"
    bl_label = "select invalid meshes"

    def execute(self, context):
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass
        selection = bpy.context.scene.objects
        scene_meshes = [obj for obj in selection if obj.type == "MESH"]
        if scene_meshes:
            select_invalid_meshes_operator(scene_meshes)
        else:
            show_message_box(message="There is no mesh in the scene")
        return {"FINISHED"}


class AlbamRemoveEmptyVertexGroupsOperator(bpy.types.Operator):
    """Remove vertex groups with 0 skin weighs"""

    bl_idname = "albam_tools.remove_empty_vertex_groups"
    bl_label = "remove empty vertex groups"

    def execute(self, context):
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass
        selection = bpy.context.scene.objects
        scene_meshes = [obj for obj in selection if obj.type == "MESH"]

        for ob in scene_meshes:
            ob.update_from_editmode()

            vgroup_used = {i: False for i, k in enumerate(ob.vertex_groups)}

            for v in ob.data.vertices:
                for g in v.groups:
                    if g.weight > 0.0:
                        vgroup_used[g.group] = True

            for i, used in sorted(vgroup_used.items(), reverse=True):
                if not used:
                    ob.vertex_groups.remove(ob.vertex_groups[i])
        show_message_box(message="Removing complete")
        return {"FINISHED"}


class AlbamTransferNormalsOperator(bpy.types.Operator):
    """Transfer normals from a unified mesh to its parts"""

    bl_idname = "albam_tools.transfer_normals"
    bl_label = "transfer normals"

    @classmethod
    def poll(self, context):  # pragma: no cover
        source_obj = context.scene.albam_scene_meshes
        # if not bpy.context.selected_objects or source_obj.type == 'MESH':
        if source_obj is None or not bpy.context.selected_objects:
            return False
        if source_obj.type != "MESH":
            return False
        return True

    def execute(self, context):
        selection = bpy.context.selected_objects
        source_obj = context.scene.albam_scene_meshes
        # for obj in bpy.data.objects:
        #     if obj.type == 'MESH':
        #        if obj.data == source_obj:
        #            source_obj = obj

        target_objs = [obj for obj in selection if obj.type == "MESH"]
        if target_objs and source_obj:
            transfer_normals(source_obj, target_objs)
        else:
            show_message_box(message="There is no mesh in selection")
        return {"FINISHED"}


classes_to_register = (
    ALBAM_PT_ImportExportPanel,
    ALBAM_PT_ToolsPanel,
    AlbamImportOperator,
    AlbamFixLeakedTexuresOperator,
    AlbamSelectInvalidMeshesOperator,
    AlbamRemoveEmptyVertexGroupsOperator,
)
