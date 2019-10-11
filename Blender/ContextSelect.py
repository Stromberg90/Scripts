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
import bmesh

bl_info = {
    "name": "Context Select",
    "category": "User",
    "author": "Andreas Strømberg",
    "wiki_url": "https://github.com/Stromberg90/Scripts/tree/master/Blender",
    "tracker_url": "https://github.com/Stromberg90/Scripts/issues",
    "blender": (2, 80, 0),
    "version": (1, 0, 1)
}

class ObjectMode:
    OBJECT = 'OBJECT'
    EDIT = 'EDIT'
    POSE = 'POSE'
    SCULPT = 'SCULPT'
    VERTEX_PAINT = 'VERTEX_PAINT'
    WEIGHT_PAINT = 'WEIGHT_PAINT'
    TEXTURE_PAINT = 'TEXTURE_PAINT'
    PARTICLE_EDIT = 'PARTICLE_EDIT'
    GPENCIL_EDIT = 'GPENCIL_EDIT'

def maya_vert_select(context):
    me = context.object.data
    bm = bmesh.from_edit_mesh(me)

    if len(bm.select_history) == 0:
        return

    selected_components = [e for e in bm.edges if e.select] + [f for f in bm.faces if f.select] + [v for v in bm.verts
                                                                                                   if v.select]

    active_vert = bm.select_history.active
    previous_active_vert = bm.select_history[len(bm.select_history) - 2]

    neighbour_verts = get_neighbour_verts(bm)

    relevant_neighbour_verts = [e for e in neighbour_verts if not e == active_vert.index]

    select_vert(active_vert)
    if not previous_active_vert.index == active_vert.index:
        if previous_active_vert.index in relevant_neighbour_verts:
            previous_active_vert.select = True
            bpy.ops.mesh.edgering_select('INVOKE_DEFAULT', ring=False)
    else:
        bm.select_history.add(active_vert)

    for component in selected_components:
        component.select = True

    bmesh.update_edit_mesh(me)


def maya_face_select(context):
    me = context.object.data
    bm = bmesh.from_edit_mesh(me)

    if len(bm.select_history) == 0:
        return

    selected_components = [e for e in bm.edges if e.select] + [f for f in bm.faces if f.select] + [v for v in bm.verts
                                                                                                   if v.select]

    active_face = bm.select_history.active
    previous_active_face = bm.select_history[len(bm.select_history) - 2]

    select_face(active_face)

    neighbour_faces = get_neighbour_faces(bm)

    relevant_neighbour_faces = [e for e in neighbour_faces if not e == active_face.index]

    select_face(active_face)

    bpy.ops.mesh.edgering_select('INVOKE_DEFAULT', ring=False)
    loop_faces = [f.index for f in bm.faces if f.select]

    select_face(active_face)

    if previous_active_face.index in loop_faces and not previous_active_face.index == active_face.index:
        if previous_active_face.index in relevant_neighbour_faces:
            bpy.ops.mesh.edgering_select('INVOKE_DEFAULT', ring=False)
        elif active_face.index in loop_faces:
            previous_active_face.select = True
            bpy.ops.mesh.shortest_path_select(use_face_step=True)
    else:
        bpy.ops.mesh.select_linked(delimit={'NORMAL'})

    for component in selected_components:
        component.select = True

    bm.select_history.add(active_face)
    bmesh.update_edit_mesh(me)


def maya_edge_select(context):
    me = context.object.data
    bm = bmesh.from_edit_mesh(me)

    if len(bm.select_history) == 0:
        return

    selected_components = {e for e in bm.edges if e.select} | {f for f in bm.faces if f.select} | {v for v in bm.verts
                                                                                                   if v.select}

    active_edge = bm.select_history.active
    previous_active_edge = bm.select_history[len(bm.select_history) - 2]

    select_edge(active_edge)
    bpy.ops.mesh.edgering_select('INVOKE_DEFAULT', ring=True)
    ring_edges = {e.index for e in bm.edges if e.select}

    select_edge(active_edge)

    if not previous_active_edge.index == active_edge.index:
        if previous_active_edge.index in ring_edges:
            neighbour_edges = get_neighbour_edges(bm)

            relevant_neighbour_edges = {e for e in neighbour_edges if e in ring_edges and not e == active_edge.index}

            select_edge(active_edge)
            if previous_active_edge.index in relevant_neighbour_edges:
                bpy.ops.mesh.edgering_select('INVOKE_DEFAULT', ring=True)
            else:
                previous_active_edge.select = True
                bpy.ops.mesh.shortest_path_select(use_face_step=True)

            bm.select_history.clear()

        else:
            bpy.ops.mesh.edgering_select('INVOKE_DEFAULT', ring=False)

            loop_edges = {e.index for e in bm.edges if e.select}

            if previous_active_edge.index in loop_edges:
                select_edge(active_edge)

                neighbour_edges = get_neighbour_edges(bm)

                relevant_neighbour_edges = {e for e in neighbour_edges if
                                            e in loop_edges and not e == active_edge.index}

                select_edge(active_edge)
                if previous_active_edge.index in relevant_neighbour_edges:
                    bpy.ops.mesh.edgering_select('INVOKE_DEFAULT', ring=False)
                else:
                    previous_active_edge.select = True
                    bpy.ops.mesh.shortest_path_select()

                bm.select_history.clear()
    else:
        bpy.ops.mesh.edgering_select('INVOKE_DEFAULT', ring=False)
        bm.select_history.clear()

    for component in selected_components:
        component.select = True

    bm.select_history.add(active_edge)
    bmesh.update_edit_mesh(me)


def get_neighbour_verts(bm):
    bpy.ops.mesh.select_more(use_face_step=False)
    neighbour_verts = [vert.index for vert in bm.verts if vert.select]
    return neighbour_verts


def get_neighbour_faces(bm):
    bpy.ops.mesh.select_more(use_face_step=False)
    neighbour_faces = [face.index for face in bm.faces if face.select]
    return neighbour_faces


def get_neighbour_edges(bm):
    bpy.ops.mesh.select_more(use_face_step=True)
    neighbour_edges = [e.index for e in bm.edges if e.select]
    return neighbour_edges


def select_edge(active_edge):
    bpy.ops.mesh.select_all(action='DESELECT')
    active_edge.select = True


def select_vert(active_vert):
    bpy.ops.mesh.select_all(action='DESELECT')
    active_vert.select = True


def select_face(active_face):
    bpy.ops.mesh.select_all(action='DESELECT')
    active_face.select = True


class OBJECT_OT_context_select(bpy.types.Operator):
    bl_idname = "object.context_select"
    bl_label = "Context Select"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        if context.object.mode == ObjectMode.EDIT:
            # Checks if we are in vertex selection mode.
            if context.tool_settings.mesh_select_mode[0]:
                maya_vert_select(context)

            # Checks if we are in edge selection mode.
            if context.tool_settings.mesh_select_mode[1]:
                bpy.ops.object.mode_set(mode='OBJECT')
                selected_edges = [e for e in context.object.data.edges if e.select]

                # Switch back to edge mode
                bpy.ops.object.mode_set(mode='EDIT')
                context.tool_settings.mesh_select_mode = (False, True, False)

                if len(selected_edges) > 0:
                    maya_edge_select(context)

            # Checks if we are in face selection mode.
            if context.tool_settings.mesh_select_mode[2]:
                if context.area.type == 'VIEW_3D':
                    maya_face_select(context)
                elif context.area.type == 'IMAGE_EDITOR':
                    bpy.ops.uv.select_linked_pick(extend=False)

        return {'FINISHED'}


def register():
    bpy.utils.register_class(OBJECT_OT_context_select)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_context_select)


if __name__ == "__main__":
    register()
