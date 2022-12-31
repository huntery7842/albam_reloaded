import os

import bpy
from albam_reloaded.registry import blender_registry
from . import Arc, KNOWN_ARC_BLENDER_CRASH, CORRUPTED_ARCS
from .mesh import build_blender_model
from .structs.arc import EXTENSION_TO_FILE_ID


@blender_registry.register_function("import", identifier=b"ARC\x00")
def import_arc(file_path):
    if file_path.endswith(tuple(KNOWN_ARC_BLENDER_CRASH) + tuple(CORRUPTED_ARCS)):
        raise ValueError("The arc file provided is not supported yet, it might crash Blender")

    bl_arc_container = bpy.data.objects.new(os.path.basename(file_path), None)
    arc = Arc(file_path=file_path)
    mod_type = EXTENSION_TO_FILE_ID['mod']
    mod_file_entries = arc.get_file_entries_by_type(mod_type)

    for mod_file_entry in mod_file_entries:
        bl_mod_container = build_blender_model(arc, mod_file_entry)
        bl_mod_container.parent = bl_arc_container

    return bl_arc_container
