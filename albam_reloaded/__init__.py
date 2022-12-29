import importlib

import bpy

from albam_reloaded.blender import classes_to_register

# Load import/export functions into the blender_registry
importlib.import_module("albam_reloaded.engines.mtframework.mesh")


bl_info = {
    "name": "Albam Reloaded",
    "author": "Sebastian Brachi",
    "version": (0, 3, 6),
    "blender": (2, 80, 0),
    "location": "Properties Panel",
    "description": "Import-Export multiple video-game formats",
    "wiki_url": "https://github.com/HenryOfCarim/albam_reloaded/wiki",
    "tracker_url": "https://github.com/HenryOfCarim/albam_reloaded/issues",
    "category": "Import-Export",
}


def register():
    for cls in classes_to_register:
        bpy.utils.register_class(cls)
    bpy.types.Scene.albam_scene_meshes = bpy.props.PointerProperty(type=bpy.types.Object)


def unregister():
    for cls in reversed(classes_to_register):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
