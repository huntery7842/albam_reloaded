import importlib
import os
import sys

import bpy

from albam_reloaded.blender_ui import classes_to_register


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

ALBAM_DIR = os.path.dirname(__file__)
VENDOR_DIR = os.path.join(ALBAM_DIR, 'albam_vendor')


def register():
    sys.path.insert(0, VENDOR_DIR)
    # Load registered functions into the blender_registry
    importlib.import_module("albam_reloaded.engines.mtframework.archive")
    for cls in classes_to_register:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes_to_register):
        bpy.utils.unregister_class(cls)
    sys.path.remove(VENDOR_DIR)
