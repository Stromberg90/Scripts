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
    "name": "Context Select",
    "description": "Maya-style loop selection for vertices, edges, and faces.",
    "author": "Andreas Strømberg, nemyax, Chris Kohl",
    "version": (1, 4, 2),
    "blender": (2, 80, 0),
    "location": "",
    "warning": "",
    "wiki_url": "https://github.com/Stromberg90/Scripts/tree/master/Blender",
    "tracker_url": "https://github.com/Stromberg90/Scripts/issues",
    "category": "Mesh"
}

import bpy
import bmesh

# Clever trick. Manage class registration automatically instead of in a hand-written list.
classes = []


class ContextSelectPreferences(bpy.types.AddonPreferences):
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __name__

    select_linked_on_double_click: bpy.props.BoolProperty(
        name="Select Linked On Double Click", default=True)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "select_linked_on_double_click")
classes.append(ContextSelectPreferences)


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


class OBJECT_OT_context_select(bpy.types.Operator):
    bl_idname = "object.context_select"
    bl_label = "Context Select"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        if context.object.mode == ObjectMode.EDIT:
            # Checks if we are in vertex selection mode.
            if context.tool_settings.mesh_select_mode[0]:
                return maya_vert_select(context)

            # Checks if we are in edge selection mode.
            if context.tool_settings.mesh_select_mode[1]:
                bpy.ops.object.mode_set(mode='OBJECT')
                selected_edges = [
                    e for e in context.object.data.edges if e.select]

                # Switch back to edge mode
                bpy.ops.object.mode_set(mode='EDIT')
                context.tool_settings.mesh_select_mode = (False, True, False)

                if len(selected_edges) > 0:
                    return maya_edge_select(context)

            # Checks if we are in face selection mode.
            if context.tool_settings.mesh_select_mode[2]:
                if context.area.type == 'VIEW_3D':
                    return maya_face_select(context, prefs)
                elif context.area.type == 'IMAGE_EDITOR':
                    bpy.ops.uv.select_linked_pick(extend=False)

        return {'FINISHED'}
classes.append(OBJECT_OT_context_select)


def maya_vert_select(context):
    me = context.object.data
    bm = bmesh.from_edit_mesh(me)

    if len(bm.select_history) == 0:
        return {'CANCELLED'}

    selected_components = [e for e in bm.edges if e.select] + [f for f in bm.faces if f.select] + [v for v in bm.verts
                                                                                                   if v.select]

    active_vert = bm.select_history.active
    previous_active_vert = bm.select_history[len(bm.select_history) - 2]
    # Sanity check.  Make sure we're actually working with vertices.
    if type(active_vert) is not bmesh.types.BMVert or type(previous_active_vert) is not bmesh.types.BMVert:
        return {'CANCELLED'}

    select_vert(active_vert)

    neighbour_verts = get_neighbour_verts(bm)

    relevant_neighbour_verts = [
        v for v in neighbour_verts if not v == active_vert.index]

    select_vert(active_vert)
    if not previous_active_vert.index == active_vert.index:
        if previous_active_vert.index in relevant_neighbour_verts:
            previous_active_vert.select = True
            # Without flushing the next operator won't recognize that there's anything to convert from vert to edge?
            bm.select_flush_mode()
            bpy.ops.mesh.select_mode('INVOKE_DEFAULT', use_extend=False, use_expand=False, type='EDGE')
            
            active_edge = [e for e in bm.edges if e.select][0]
        
            if active_edge.is_boundary:
                boundary_edges = get_boundary_edge_loop(active_edge)
                for e in boundary_edges:
                    e.select = True
                bpy.ops.mesh.select_mode('INVOKE_DEFAULT', use_extend=False, use_expand=False, type='VERT')
            else:
                bpy.ops.mesh.loop_multi_select('INVOKE_DEFAULT', ring=False)
                bpy.ops.mesh.select_mode('INVOKE_DEFAULT', use_extend=False, use_expand=False, type='VERT')
    else:
        bm.select_history.add(active_vert)

    for component in selected_components:
        component.select = True

    bm.select_history.add(active_vert) #Re-add active_vert to history to keep it active.
    bm.select_flush_mode()
    bmesh.update_edit_mesh(me)
    return {'FINISHED'}


def maya_face_select(context, prefs):
    me = context.object.data
    bm = bmesh.from_edit_mesh(me)

    if len(bm.select_history) == 0:
        return {'CANCELLED'}

    selected_components = [e for e in bm.edges if e.select] + [f for f in bm.faces if f.select] + [v for v in bm.verts
                                                                                                   if v.select]

    active_face = bm.select_history.active
    previous_active_face = bm.select_history[len(bm.select_history) - 2]
    # Sanity check.  Make sure we're actually working with faces.
    if type(active_face) is not bmesh.types.BMFace or type(previous_active_face) is not bmesh.types.BMFace:
        return {'CANCELLED'}

    select_face(active_face)

    neighbour_faces = get_neighbour_faces(bm)

    relevant_neighbour_faces = [
        e for e in neighbour_faces if not e == active_face.index]

    select_face(active_face)

    bpy.ops.mesh.edgering_select('INVOKE_DEFAULT', ring=False)
    loop_faces = [f.index for f in bm.faces if f.select]

    select_face(active_face)

    # Must use ring=True because sometimes triangles touch against the active_face so loops won't complete.
    bpy.ops.mesh.loop_multi_select('INVOKE_DEFAULT', ring=True)
    # Must use Edge instead of Verts because if verts encompass a triangle it will select that face.
    bpy.ops.mesh.select_mode('INVOKE_DEFAULT', use_extend=False, use_expand=False, type='EDGE')
    bpy.ops.mesh.select_mode('INVOKE_DEFAULT', use_extend=False, use_expand=False, type='FACE')
    two_loop_faces = [f.index for f in bm.faces if f.select]

    select_face(active_face)

    if previous_active_face.index in loop_faces and not previous_active_face.index == active_face.index:
        if previous_active_face.index in relevant_neighbour_faces:
            bpy.ops.mesh.edgering_select('INVOKE_DEFAULT', ring=True)
        elif active_face.index in two_loop_faces:
            previous_active_face.select = True
            # Using topology distance seems to catch more cases which makes this slightly better?
            bpy.ops.mesh.shortest_path_select(use_face_step=False, use_topology_distance=True)
    elif previous_active_face.index in two_loop_faces and not previous_active_face.index == active_face.index: 
        if active_face.index in two_loop_faces:
            previous_active_face.select = True
            # Using topology distance seems to catch more cases which makes this slightly better?
            bpy.ops.mesh.shortest_path_select(use_face_step=False, use_topology_distance=True)
    else:
        if prefs.select_linked_on_double_click:
            bpy.ops.mesh.select_linked(delimit={'NORMAL'})

    for component in selected_components:
        component.select = True

    bm.select_history.add(active_face)
    bm.select_flush_mode()
    bmesh.update_edit_mesh(me)
    return {'FINISHED'}


def maya_edge_select(context):
    me = context.object.data
    bm = bmesh.from_edit_mesh(me)

    if len(bm.select_history) == 0:
        return {'CANCELLED'}

    selected_components = {e for e in bm.edges if e.select} | {f for f in bm.faces if f.select} | {v for v in bm.verts
                                                                                                   if v.select}

    active_edge = bm.select_history.active
    previous_active_edge = bm.select_history[len(bm.select_history) - 2]
    # Sanity check.  Make sure we're actually working with edges.
    if type(active_edge) is not bmesh.types.BMEdge or type(previous_active_edge) is not bmesh.types.BMEdge:
        return {'CANCELLED'}

    select_edge(active_edge)
    bpy.ops.mesh.edgering_select('INVOKE_DEFAULT', ring=True)
    ring_edges = {e.index for e in bm.edges if e.select}

    select_edge(active_edge)

    if not previous_active_edge.index == active_edge.index:
        if previous_active_edge.index in ring_edges:
            neighbour_edges = get_neighbour_edges(bm)

            relevant_neighbour_edges = {
                e for e in neighbour_edges if e in ring_edges and not e == active_edge.index}

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
                    bpy.ops.mesh.edgering_select(
                        'INVOKE_DEFAULT', ring=False)
                else:
                    previous_active_edge.select = True
                    bpy.ops.mesh.shortest_path_select()
                    
            elif active_edge.is_boundary:
                boundary_edges = get_boundary_edge_loop(active_edge)
                for e in boundary_edges:
                    e.select = True

                bm.select_history.clear()
    else:
        if active_edge.is_boundary:
            boundary_edges = get_boundary_edge_loop(active_edge)
            for e in boundary_edges:
                e.select = True
        else:
            bpy.ops.mesh.edgering_select('INVOKE_DEFAULT', ring=False)
            bm.select_history.clear()

    for component in selected_components:
        component.select = True

    bm.select_history.add(active_edge)
    bm.select_flush_mode()
    bmesh.update_edit_mesh(me)
    return {'FINISHED'}


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


# Takes a boundary edge and returns a list of other boundary edges
# that are contiguous with it in the same boundary "loop".
def get_boundary_edge_loop(active_edge):
    first_edge = active_edge
    cur_edge = active_edge
    final_selection = []

    while True:
        final_selection.append(cur_edge)
        edge_verts = cur_edge.verts
        new_edges = []

        # From vertices in the current edge get connected edges if they're boundary.
        new_edges = [e for v in edge_verts for e in v.link_edges[:] \
        if e.is_boundary and e != cur_edge and not e in final_selection]
        
        if len(new_edges) == 0 or new_edges[0] == first_edge:
            break
        else:
            cur_edge = new_edges[0]
    return final_selection


# Takes an edge and returns a loop of face indices (as a set) for the ring direction of that edge. NOTE: This is not being used in this commit.
def face_loop_from_edge(edge):
    prefs = bpy.context.preferences.addons[__name__].preferences
    loop = edge.link_loops[0]
    first_loop = loop
    cur_loop = loop
    face_list = set()  # Checking for membership in sets is faster than lists []
    going_forward = True
    dead_end = False
    while True:
        # Jump to next loop on the same edge and walk two loops forward (opposite edge)
        next_loop = cur_loop.link_loop_radial_next.link_loop_next.link_loop_next

        next_face = next_loop.face
        if next_face.index in face_list and prefs.terminate_self_intersects:
            dead_end = True
        elif next_face.index not in face_list:
            if len(next_face.verts) == 4:
                face_list.add(next_face.index)
            elif len(next_face.verts) != 4 and prefs.allow_non_quads_at_ends:
                face_list.add(next_face.index)

        # If this is true then we've looped back to the beginning and are done
        if next_loop == first_loop:
            break
        # If we reach a dead end because the next face is a tri or n-gon, or the next edge is boundary or nonmanifold.
        elif len(next_face.verts) != 4 or len(next_loop.edge.link_faces) != 2 or dead_end:
            # If going_forward then this is the first dead end and we want to go the other way
            if going_forward:
                going_forward = False
                dead_end = False
                # Return to the starting edge and go the other way
                if len(edge.link_loops) > 1:
                    next_loop = edge.link_loops[1]
                else:
                    break
            # If not going_forward then this is the last dead end and we're done
            else:
                break
        # Run this part always
        cur_loop = next_loop
    return face_list


# ##################### Loopanar defs ##################### # NOTE: These are not being used in this commit.

def loop_extension(edge, vert):
    candidates = vert.link_edges[:]
    # For certain topology link_edges and link_loops return different numbers.
    # So we have to use link_loops for our length test, otherwise somehow we get stuck in an infinite loop.
    if len(vert.link_loops) == 4 and vert.is_manifold:
        cruft = [edge]  # The next edge obviously can't be the current edge.
        for l in edge.link_loops:
            # The 'next' and 'prev' edges are perpendicular to the desired loop so we don't want them.
            cruft.extend([l.link_loop_next.edge, l.link_loop_prev.edge])
        # Therefore by process of elimination there are 3 unwanted edges in cruft and only 1 possible edge left.
        return [e for e in candidates if e not in cruft][0]
    else:
        return


def loop_end(edge):
    # What's going on here?  This looks like it's assigning both vertices at once from the edge.verts
    v1, v2 = edge.verts[:]
    # And returns only one of them dependong on the result from loop_extension?
    return not loop_extension(edge, v1) or not loop_extension(edge, v2)


def ring_extension(edge, face):
    if len(face.verts) == 4:
        # Get the only 2 verts that are not in the edge we start with.
        target_verts = [v for v in face.verts if v not in edge.verts]
        # Return the only edge that corresponds to those two verts back to partial_ring.
        return [e for e in face.edges if target_verts[0] in e.verts and target_verts[1] in e.verts][0]
    else:
        # Otherwise the face isn't a quad.. return nothing to partial_ring.
        return


def ring_end(edge):
    faces = edge.link_faces[:]
    border = len(faces) == 1  # If only one face is connected then this edge must be the border of the mesh.
    non_manifold = len(faces) > 2  # In manifold geometry one edge can only be connected to two faces.
    dead_ends = map(lambda x: len(x.verts) != 4, faces)
    return border or non_manifold or any(dead_ends)


def entire_loop(edge):
    e = edge
    v = edge.verts[0]
    loop = [edge]
    going_forward = True
    while True:
        ext = loop_extension(e, v)  # Pass the edge and its starting vert to loop_extension
        if ext:  # If loop_extension returns an edge, keep going.
            if going_forward:
                if ext == edge:  # infinite; we've reached our starting edge and are done
                    # Why are we returning the loop and edge twice?  Loop already has edge in it.  Why not just loop?
                    return [edge] + loop + [edge]
                else:  # continue forward
                    loop.append(ext)
            else:  # continue backward
                loop.insert(0, ext)
            v = ext.other_vert(v)
            e = ext
        else:  # finite and we've reached an end
            if going_forward:  # the first end
                going_forward = False
                e = edge
                v = edge.verts[1]
            else:  # the other end
                return loop  # Return the completed partial loop


def partial_ring(edge, face):
    part_ring = []
    e, f = edge, face
    while True:
        ext = ring_extension(e, f)  # Pass the edge and face to ring_extension
        if not ext:
            break
        part_ring.append(ext)
        if ext == edge:  # infinite; we've reached our starting edge and are done
            break
        if ring_end(ext):  # Pass the edge returned from ring_extension to check if it is the end.
            break
        else:
            f = [x for x in ext.link_faces if x != f][0]
            e = ext
    return part_ring  # return partial ring to entire_ring


def entire_ring(edge):
    fs = edge.link_faces  # Get faces connected to this edge.
    ring = [edge]
    # First check to see if there is ANY face connected to the edge (because Blender allows for floating edges.
    # If there's at least 1 face, then make sure only 2 faces are connected to 1 edge (manifold geometry) to continue.
    if len(fs) and len(fs) < 3:
        # ne must stand for Next Edge? Take the edge from the input, and a face from fs and pass it to partial_ring..
        dirs = [ne for ne in [partial_ring(edge, f) for f in fs] if ne]
        if dirs:
            if len(dirs) == 2 and set(dirs[0]) != set(dirs[1]):
                [ring.insert(0, e) for e in dirs[1]]
            ring.extend(dirs[0])
    return ring  # return ring back to complete_associated_rings


def complete_associated_loops(edges):
    loops = []
    for e in edges:
        if not any([e in l for l in loops]):
            loops.append(entire_loop(e))
    return loops


def complete_associated_rings(edges):
    rings = []
    for e in edges:
        # At first glance this line doesn't seem to matter because rings is empty but once we start
        # adding rings to it then I believe it's needed to prevent duplicates (why not a set?)
        if not any([e in r for r in rings]):
            rings.append(entire_ring(e))
    return rings  # return rings back to select_bounded_ring


def group_unselected(edges, ends):
    gaps = [[]]
    for e in edges:
        # if not e.select:  # We don't care about what's already selected.
        if e not in ends:  # We only care about the gap between the two ends that we used to start the selection.
            gaps[-1].extend([e])
        else:
            gaps.append([])
    return [g for g in gaps if g != []]


# Takes two separated loop edges and returns a set of indices for edges in the shortest loop between them.
def select_bounded_loop(edges):
    for l in complete_associated_loops(edges):
        gaps = group_unselected(l, edges)
        new_sel = set()
        if l[0] == l[-1]:  # loop is infinite
            sg = sorted(gaps,
                        key = lambda x: len(x),
                        reverse = True)
            if len(sg) > 1 and len(sg[0]) > len(sg[1]):  # single longest gap
                final_gaps = sg[1:]
            else:
                final_gaps = sg
        else:  # loop is finite
            tails = [g for g in gaps if any(map(lambda x: loop_end(x), g))]
            nontails = [g for g in gaps if g not in tails]
            if nontails:
                final_gaps = nontails
            else:
                final_gaps = gaps
        for g in final_gaps:
            for e in g:
                new_sel.add(e.index)
    return new_sel


# Takes two separated ring edges and returns a set of indices for edges in the shortest ring between them.
def select_bounded_ring(edges):
    for r in complete_associated_rings(edges):
        gaps = group_unselected(r, edges)
        new_sel = set()
        if r[0] == r[-1]:  # ring is infinite
            sg = sorted(gaps,
                        key = lambda x: len(x),
                        reverse = True)
            if len(sg) > 1 and len(sg[0]) > len(sg[1]):  # single longest gap
                final_gaps = sg[1:]
            else:  # Otherwise the lengths must be identical and there is no single longest gap?
                final_gaps = sg
        else:  # ring is finite
            # Tails = any group of unselected edges starting at one of the starting edges
            # and extending all the way to a dead end.
            tails = [g for g in gaps if any(map(lambda x: ring_end(x), g))]
            nontails = [g for g in gaps if g not in tails]  # Any group between the edges in starting edges.
            if nontails:
                final_gaps = nontails
            else:
                final_gaps = gaps
        for g in final_gaps:
            for e in g:
                new_sel.add(e.index)
    return new_sel


def register():
    for every_class in classes:
        bpy.utils.register_class(every_class)


def unregister():
    for every_class in classes:
        bpy.utils.unregister_class(every_class)


if __name__ == "__main__":
    register()
