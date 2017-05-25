import bpy
import bgl

bl_info = {
    "name": "Merge Tool",
    "category": "User",
    "author": "Andreas Strømberg",
}


def draw_callback_px(self, context):

    # 50% alpha, 2 pixel width line
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor4f(1.0, 0.0, 0.0, 1.0)
    bgl.glLineWidth(2)

    bgl.glBegin(bgl.GL_LINES)
    if self.started:
        bgl.glVertex2i(self.start_vertex[0], self.start_vertex[1])
        bgl.glVertex2i(self.end_vertex[0], self.end_vertex[1])

    bgl.glEnd()

    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)


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

            context.window_manager.modal_handler_add(self)
            self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')

            self.started = False
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
