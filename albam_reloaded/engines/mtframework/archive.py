import os

from albam_reloaded.registry import blender_registry
from . import Arc, KNOWN_ARC_BLENDER_CRASH, CORRUPTED_ARCS


@blender_registry.register_function("import", identifier=b"ARC\x00")
def import_arc(blender_object, file_path, **kwargs):
    """Imports an arc file (Resident Evil 5 for only for now) into blender,
    extracting all files to a tmp dir and saving unknown/unused data
    to the armature (if any) for using in exporting
    """

    unpack_dir = kwargs.get("unpack_dir")
    if file_path.endswith(tuple(KNOWN_ARC_BLENDER_CRASH) + tuple(CORRUPTED_ARCS)):
        raise ValueError("The arc file provided is not supported yet, it might crash Blender")

    base_dir = os.path.basename(file_path).replace(".arc", "_arc_extracted")
    out = unpack_dir or os.path.join(
        os.path.expanduser("~"), ".albam", "re5", base_dir
    )  # causing an error
    # out = os.path.join(os.path.expanduser('~'), '.albam', 're5', base_dir)
    if not os.path.isdir(out):
        os.makedirs(out)
    if not out.endswith(os.path.sep):
        out = out + os.path.sep

    arc = Arc(file_path=file_path)
    arc.unpack(out)

    mod_files = [
        os.path.join(root, f)
        for root, _, files in os.walk(out)
        for f in files
        if f.endswith(".mod")
    ]
    mod_folders = [os.path.dirname(mod_file.split(out)[-1]) for mod_file in mod_files]

    return {
        "files": mod_files,
        "kwargs": {
            "parent": blender_object,
            "mod_folder": mod_folders[0],  # XXX will break if mods are in different folders
            "base_dir": out,
        },
    }
