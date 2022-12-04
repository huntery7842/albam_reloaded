import importlib

try:
    import bpy
except ImportError:
    pass
from albam_reloaded.blender import (
    classes_to_register,
    AlbamImportedItemName,
    AlbamImportedItem,
    AlbamExportSettings,
)
from albam_reloaded.registry import blender_registry

# Load import/export functions into the blender_registry
importlib.import_module('albam_reloaded.engines.mtframework.blender_import')
importlib.import_module('albam_reloaded.engines.mtframework.blender_export')


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

    for prop_name, prop_cls_name, default in blender_registry.bpy_props.get("material", []):
        prop_cls = getattr(bpy.props, prop_cls_name)
        kwargs = {}
        if default:
            kwargs["default"] = default
        prop_instance = prop_cls(**kwargs)
        setattr(bpy.types.Material, prop_name, prop_instance)

    # Setting custom texture properties
    for prop_name, prop_cls_name, default in blender_registry.bpy_props.get("texture", []):
        prop_cls = getattr(bpy.props, prop_cls_name)
        kwargs = {}
        if default:
            kwargs["default"] = default
        prop_instance = prop_cls(**kwargs)
        setattr(bpy.types.Texture, prop_name, prop_instance)

    # Setting custom mesh properties
    for prop_name, prop_cls_name, default in blender_registry.bpy_props.get("mesh", []):
        prop_cls = getattr(bpy.props, prop_cls_name)
        kwargs = {}
        if default:
            kwargs["default"] = default
        prop_instance = prop_cls(**kwargs)
        setattr(bpy.types.Mesh, prop_name, prop_instance)

    """ Classic blender 2.80 registration of classes"""
    from bpy.utils import register_class

    for cls in classes_to_register:
        register_class(cls)
    bpy.types.Scene.albam_item_to_export = bpy.props.StringProperty()
    bpy.types.Scene.albam_items_imported = bpy.props.CollectionProperty(
        type=AlbamImportedItemName
    )  # register name property for scene
    bpy.types.Object.albam_imported_item = bpy.props.PointerProperty(
        type=AlbamImportedItem
    )  # register new object properties
    bpy.types.Scene.albam_export_settings = bpy.props.PointerProperty(
        type=blender.AlbamExportSettings
    )
    bpy.types.Scene.albam_scene_meshes = bpy.props.PointerProperty(
        type=bpy.types.Object
    )
    bpy.types.Scene.albam_export_settings = bpy.props.PointerProperty(
        type=AlbamExportSettings
    )


def unregister():
    """Classic blender 2.80 unregistration of classes"""
    from bpy.utils import unregister_class

    for cls in reversed(classes_to_register):
        unregister_class(cls)

    del bpy.types.Scene.albam_item_to_export
    del bpy.types.Scene.albam_items_imported
    del bpy.types.Object.albam_imported_item
    del bpy.types.Scene.albam_export_settings


if __name__ == "__main__":
    register()
