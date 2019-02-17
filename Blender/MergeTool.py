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

import bpy
import bgl
import gpu
from gpu_extras.batch import batch_for_shader

bl_info = {
    "name": "Merge Tool",
    "category": "User",
    "author": "Andreas Strømberg",
    "blender": (2, 80, 0)
}


def draw_callback_px(self, context):
    if self.started:
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glLineWidth(2)

        coords = [self.start_vertex, self.end_vertex]
        shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": coords})
        shader.bind()
        shader.uniform_float("color", (1, 0, 0, 1))
        batch.draw(shader)

    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)


def main(context, event, started):
    """Run this function on left mouse, execute the ray cast"""
    coord = event.mouse_region_x, event.mouse_region_y

    if started:
        result = bpy.ops.view3d.select(extend=True, location=coord)
    else:
        result = bpy.ops.view3d.select(extend=False, location=coord)

    if result == {'PASS_THROUGH'}:
        bpy.ops.mesh.select_all(action='DESELECT')


class MergeTool(bpy.types.Operator):
    """Modal object selection with a ray cast"""
    bl_idname = "object.merge_tool"
    bl_label = "Merge Tool Operator"
    bl_options = {'REGISTER', 'UNDO'}

    def __init__(self):
        self.started = None
        self.start_vertex = None
        self.end_vertex = None
        self._handle = None

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            # allow navigation
            return {'PASS_THROUGH'}
        elif event.type == 'MOUSEMOVE':
            if self.started:
                self.end_vertex = (event.mouse_region_x, event.mouse_region_y)

        elif event.type == 'LEFTMOUSE':
            main(context, event, self.started)
            if not self.started:
                if context.object.data.total_vert_sel == 1:
                    self.start_vertex = (event.mouse_region_x, event.mouse_region_y)
                    self.end_vertex = (event.mouse_region_x, event.mouse_region_y)
                    self.started = True
            elif context.object.data.total_vert_sel == 2:
                bpy.ops.mesh.merge(type='LAST')
                bpy.ops.ed.undo_push(message="Add an undo step *function may be moved*")
                self.started = False

            return {'RUNNING_MODAL'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.space_data.type == 'VIEW_3D':
            args = (self, context)

            self.start_vertex = (0, 0)
            self.end_vertex = (0, 0)
            self.started = False
            self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')

            context.window_manager.modal_handler_add(self)

            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}


def register():
    bpy.utils.register_class(MergeTool)


def unregister():
    bpy.utils.unregister_class(MergeTool)


if __name__ == "__main__":
    register()
