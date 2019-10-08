# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


bl_info = {
    "name": "Duplicate Along Curve",
    "category": "Object",
    "description": "Select a curve and an object, to duplicate object along curve.",
    "author": "Andreas Strømberg",
    "wiki_url": "https://github.com/Stromberg90/Scripts/tree/master/Blender",
    "tracker_url": "https://github.com/Stromberg90/Scripts/issues",
    "blender": (2, 80, 0),
    "version": (1, 0)
}

import bpy


def main(context):
    if bpy.context.selected_objects[1].type == 'MESH' and bpy.context.selected_objects[0].type == 'CURVE':
        selected_curve = bpy.context.selected_objects[0]
        selected_object = bpy.context.selected_objects[1]
    elif bpy.context.selected_objects[1].type == 'CURVE' and bpy.context.selected_objects[0].type == 'MESH':
        selected_curve = bpy.context.selected_objects[1]
        selected_object = bpy.context.selected_objects[0]
    else:
        return

    bpy.ops.object.transform_apply(scale=True)

    bpy.ops.object.select_all(action='DESELECT')
    selected_object.select_set(True)
    context.view_layer.objects.active = selected_object

    array_modifier = selected_object.modifiers.new(name='DUPLICATE_ARRAY', type='ARRAY')
    array_modifier.fit_type = 'FIT_CURVE'
    array_modifier.curve = selected_curve

    curve_modifier = selected_object.modifiers.new(name='DUPLICATE_CURVE', type='CURVE')
    curve_modifier.object = selected_curve

    selected_object.location = selected_curve.location


class DuplicateAlongCurve(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.duplicate_along_curve"
    bl_label = "Duplicate Along Curve"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if len(context.selected_objects) == 2:
            return context.active_object is not None
        else:
            return False

    def execute(self, context):
        main(context)
        return {'FINISHED'}


def register():
    bpy.utils.register_class(DuplicateAlongCurve)


def unregister():
    bpy.utils.unregister_class(DuplicateAlongCurve)


if __name__ == "__main__":
    register()
