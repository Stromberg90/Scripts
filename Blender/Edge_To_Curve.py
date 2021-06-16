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
    "name": "Edges To Curve",
    "category": "Mesh",
    "location": "View3D > Edge menu or Context menu",
    "description": "Converts selected edges into curve with extrusion",
    "author": "Andreas Strømberg, Chris Kohl",
    "wiki_url": "https://github.com/Stromberg90/Scripts/tree/master/Blender",
    "tracker_url": "https://github.com/Stromberg90/Scripts/issues",
    "blender": (2, 80, 0),
    "version": (1, 0, 4),
}

import bpy


class MeshMode:
    VERTEX = (True, False, False)
    EDGE = (False, True, False)
    FACE = (False, False, True)


class ObjectMode:
    OBJECT = "OBJECT"
    EDIT = "EDIT"
    POSE = "POSE"
    SCULPT = "SCULPT"
    VERTEX_PAINT = "VERTEX_PAINT"
    WEIGHT_PAINT = "WEIGHT_PAINT"
    TEXTURE_PAINT = "TEXTURE_PAINT"
    PARTICLE_EDIT = "PARTICLE_EDIT"
    GPENCIL_EDIT = "GPENCIL_EDIT"


class EventType:
    MOUSEMOVE = "MOUSEMOVE"
    WHEELUPMOUSE = "WHEELUPMOUSE"
    WHEELDOWNMOUSE = "WHEELDOWNMOUSE"
    LEFTMOUSE = "LEFTMOUSE"
    RIGHTMOUSE = "RIGHTMOUSE"
    ESC = "ESC"


class ModalEdgeToCurve(bpy.types.Operator):
    bl_idname = "object.edge_to_curve"
    bl_label = "Edges To Curve"
    bl_description = "Takes selected mesh edges and converts them into a curve."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return (
            context.active_object.mode == ObjectMode.EDIT
            and context.active_object.type == "MESH"
            or context.active_object.type == "CURVE"
        )

    def execute(self, context):
        context.object.data.bevel_depth = self.value / 100.0
        context.object.data.bevel_resolution = self.resolution
        return {"FINISHED"}

    def modal(self, context, event):
        if event.type == EventType.MOUSEMOVE:  # Apply
            self.value = max(0, (event.mouse_x - self.start_value))
        elif event.type == EventType.WHEELUPMOUSE:
            self.resolution += 1
        elif event.type == EventType.WHEELDOWNMOUSE and self.resolution > 1:
            self.resolution -= 1
        elif event.type == EventType.LEFTMOUSE:  # Confirm
            if context.active_object.type != "CURVE":
                context.view_layer.objects.active = self.original_object
                bpy.ops.object.select_all(action="DESELECT")
                self.original_object.select_set(True)
                bpy.ops.object.mode_set(mode=ObjectMode.EDIT)
                context.tool_settings.mesh_select_mode = MeshMode.EDGE
            return {"FINISHED"}
        elif event.type in {EventType.RIGHTMOUSE, EventType.ESC}:  # Cancel
            if context.active_object.type == "CURVE":
                context.object.data.bevel_depth = 0
            else:
                bpy.ops.object.delete()
                context.view_layer.objects.active = self.original_object
                bpy.ops.object.select_all(action="DESELECT")
                self.original_object.select_set(True)
                bpy.ops.object.mode_set(mode=ObjectMode.EDIT)
                context.tool_settings.mesh_select_mode = MeshMode.EDGE
            return {"CANCELLED"}

        self.execute(context)
        return {"RUNNING_MODAL"}

    def invoke(self, context, event):
        self.value = 0.0
        self.start_value = event.mouse_x
        self.resolution = 2
        self.original_object = bpy.context.active_object
        if context.active_object.type == "CURVE":
            context.object.data.fill_mode = "FULL"
            context.object.data.bevel_resolution = self.resolution
            self.execute(context)
            context.window_manager.modal_handler_add(self)
            return {"RUNNING_MODAL"}

        else:
            if context.tool_settings.mesh_select_mode[0]:
                context.tool_settings.mesh_select_mode = MeshMode.EDGE
                if not context.object.data.total_vert_sel > 1:
                    return {"CANCELLED"}
                context.tool_settings.mesh_select_mode = MeshMode.VERTEX

            bpy.ops.mesh.duplicate()
            bpy.ops.mesh.separate()
            bpy.ops.object.mode_set(mode=ObjectMode.OBJECT)
            curve_object = context.selected_objects[-1]
            context.view_layer.objects.active = curve_object
            bpy.ops.object.select_all(action="DESELECT")
            curve_object.select_set(True)
            bpy.ops.object.convert(target="CURVE")
            context.object.data.fill_mode = "FULL"
            bpy.ops.object.shade_smooth()
            context.object.data.bevel_resolution = self.resolution
            self.execute(context)
            context.window_manager.modal_handler_add(self)
            return {"RUNNING_MODAL"}


def EdgeToCurveMenuItem(self, context):
    layout = self.layout
    layout.separator()
    layout.operator_context = "INVOKE_DEFAULT"
    layout.operator("object.edge_to_curve", text="Edges to Curve")


def register():
    bpy.utils.register_class(ModalEdgeToCurve)
    bpy.types.VIEW3D_MT_edit_mesh_edges.append(EdgeToCurveMenuItem)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(EdgeToCurveMenuItem)


def unregister():
    bpy.utils.unregister_class(ModalEdgeToCurve)
    bpy.types.VIEW3D_MT_edit_mesh_edges.remove(EdgeToCurveMenuItem)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(EdgeToCurveMenuItem)


if __name__ == "__main__":
    register()
