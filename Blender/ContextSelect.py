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
    "version": (1, 5, 0),
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
        name="Select Linked On Double Click",
        description="Double clicking on a face or a vertex (if not part of a loop selection) "
                    + "will select all components for that contiguous mesh piece.",
        default=True)

    allow_non_quads_at_ends: bpy.props.BoolProperty(
        name="Allow Non-Quads At Start/End Of Face Loops",
        description="If a loop of faces terminates at a triangle or n-gon, "
                    + "allow that non-quad face to be added to the final loop selection, "
                    + "and allow using that non-quad face to begin a loop selection.",
        default=True)

    terminate_self_intersects: bpy.props.BoolProperty(
        name="Terminate Self-Intersects At Intersection",
        description="If a loop of faces circles around and crosses over itself, "
                    + "stop the selection at that location.",  # Currently only works with face loops.
        default=False)

    boundary_ignore_wires: bpy.props.BoolProperty(
        name="Ignore Wire Edges On Boundaries",
        description="If wire edges are attached to a boundary vertex the selection will ignore it, "
                    + "pass through, and continue selecting the boundary loop.",
        default=True)

    leave_edge_active: bpy.props.BoolProperty(
        name="Leave Edge Active After Selections",
        description="When selecting edge loops or edge rings, the active edge will remain active. "
                    + "NOTE: This changes the behavior of chained neighbour selections to be non-Maya like.",
        default=False)

    def draw(self, context):
        layout = self.layout
        layout.label(text="General Selection:")
        layout.prop(self, "select_linked_on_double_click")
        layout.label(text="Edge Selection:")
        layout.prop(self, "leave_edge_active")
        layout.prop(self, "boundary_ignore_wires")
        layout.label(text="Face Selection:")
        layout.prop(self, "allow_non_quads_at_ends")
        layout.prop(self, "terminate_self_intersects")
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
        if context.object.mode == ObjectMode.EDIT:
            # Checks if we are in vertex selection mode.
            if context.tool_settings.mesh_select_mode[0]:
                return maya_vert_select(context)

            # Checks if we are in edge selection mode.
            if context.tool_settings.mesh_select_mode[1]:
                return maya_edge_select(context)

            # Checks if we are in face selection mode.
            if context.tool_settings.mesh_select_mode[2]:
                if context.area.type == 'VIEW_3D':
                    return maya_face_select(context)
                elif context.area.type == 'IMAGE_EDITOR':
                    bpy.ops.uv.select_linked_pick(extend=False)
        return {'FINISHED'}
classes.append(OBJECT_OT_context_select)


def maya_vert_select(context):
    prefs = context.preferences.addons[__name__].preferences
    me = context.object.data
    bm = bmesh.from_edit_mesh(me)

    if len(bm.select_history) == 0:
        return {'CANCELLED'}

    selected_components = [v for v in bm.verts if v.select]

    active_vert = bm.select_history.active
    previous_active_vert = bm.select_history[len(bm.select_history) - 2]
    # Sanity check.  Make sure we're actually working with vertices.
    if type(active_vert) is not bmesh.types.BMVert or type(previous_active_vert) is not bmesh.types.BMVert:
        return {'CANCELLED'}

    relevant_neighbour_verts = get_neighbour_verts(active_vert)

    adjacent = False
    if previous_active_vert.index in relevant_neighbour_verts:
        adjacent = True

    if not previous_active_vert.index == active_vert.index:
        if adjacent:
            # Instead of looping through vertices we totally cheat and use the two adjacent vertices to get an edge
            # and then use that edge to get an edge loop. The select_flush_mode (which we must do anyway)
            # near the end of maya_vert_select will handle converting the edge loop back into vertices.
            active_edge = [e for e in active_vert.link_edges[:] if e in previous_active_vert.link_edges[:]][0]
            if active_edge.is_boundary:
                boundary_edges = get_boundary_edge_loop(active_edge)
                for i in boundary_edges:
                    bm.edges[i].select = True
            else:
                loop_edges = entire_loop(active_edge)
                for e in loop_edges:
                    e.select = True
        else:
            if prefs.select_linked_on_double_click:
                select_vert(active_vert)
                bpy.ops.mesh.select_linked()
    else:
        if prefs.select_linked_on_double_click:
            select_vert(active_vert)
            bpy.ops.mesh.select_linked()

    for component in selected_components:
        component.select = True

    bm.select_history.add(active_vert)  # Re-add active_vert to history to keep it active.
    bm.select_flush_mode()
    bmesh.update_edit_mesh(me)
    return {'FINISHED'}


def maya_face_select(context):
    prefs = context.preferences.addons[__name__].preferences
    me = context.object.data
    bm = bmesh.from_edit_mesh(me)

    if len(bm.select_history) == 0:
        return {'CANCELLED'}

    selected_components = [f for f in bm.faces if f.select]

    active_face = bm.select_history.active
    previous_active_face = bm.select_history[len(bm.select_history) - 2]
    # Sanity check.  Make sure we're actually working with faces.
    if type(active_face) is not bmesh.types.BMFace or type(previous_active_face) is not bmesh.types.BMFace:
        return {'CANCELLED'}

    relevant_neighbour_faces = get_neighbour_faces(active_face)

    if len(active_face.verts) != 4 and len(previous_active_face.verts) != 4:
        quads = (0, 0)
    elif len(active_face.verts) == 4 and len(previous_active_face.verts) == 4:
        quads = (1, 1)
    elif len(active_face.verts) == 4 and len(previous_active_face.verts) != 4:
        quads = (1, 0)
    elif len(active_face.verts) != 4 and len(previous_active_face.verts) == 4:
        quads = (0, 1)

    adjacent = False
    if previous_active_face.index in relevant_neighbour_faces:
        adjacent = True

    a_edges = active_face.edges
    p_edges = previous_active_face.edges
    if adjacent:
        ring_edge = [e for e in a_edges if e in p_edges][0]
    elif not adjacent:
        if quads == (1, 1) or quads == (1, 0) or quads == (0, 0):
            ring_edge = a_edges[0]
        elif quads == (0, 1):
            ring_edge = p_edges[0]

    corner_vert = ring_edge.verts[0]
    if quads == (1, 1) or quads == (1, 0) or quads == (0, 0):
        other_edge = [e for e in a_edges if e != ring_edge and
                     (e.verts[0].index == corner_vert.index or e.verts[1].index == corner_vert.index)][0]
    elif quads == (0, 1):
        other_edge = [e for e in p_edges if e != ring_edge and
                     (e.verts[0].index == corner_vert.index or e.verts[1].index == corner_vert.index)][0]

    if not previous_active_face.index == active_face.index and not quads == (0, 0):
        if adjacent and (quads == (1, 1) or prefs.allow_non_quads_at_ends):
            loop1_faces = face_loop_from_edge(ring_edge)
            for f in loop1_faces:  # We already have the loop, so just select it.
                bm.faces[f].select = True
        elif not adjacent and (quads == (1, 1) or prefs.allow_non_quads_at_ends):
            loop1_faces = face_loop_from_edge(ring_edge)
            # If we are lucky then both faces will be in the first loop and we won't even have to test a second loop.
            # (Save time on very dense meshes with LONG face loops.)
            if active_face.index in loop1_faces and previous_active_face.index in loop1_faces:
                select_face(active_face)
                previous_active_face.select = True
                # Using topology distance seems to catch more cases which makes this slightly better?
                bpy.ops.mesh.shortest_path_select(use_face_step=False, use_topology_distance=True)
            # If they weren't both in the first loop tested, try a second loop perpendicular to the first.
            else:
                loop2_faces = face_loop_from_edge(other_edge)
                if active_face.index in loop2_faces and previous_active_face.index in loop2_faces:
                    select_face(active_face)
                    previous_active_face.select = True
                    # Using topology distance seems to catch more cases which makes this slightly better?
                    bpy.ops.mesh.shortest_path_select(use_face_step=False, use_topology_distance=True)
                # If neither loop contains both faces, select linked.
                else:
                    if prefs.select_linked_on_double_click:
                        select_face(active_face)
                        bpy.ops.mesh.select_linked()
        else:  # Catchall for if not prefs.allow_non_quads_at_ends
            if prefs.select_linked_on_double_click:
                select_face(active_face)
                bpy.ops.mesh.select_linked()
    else:
        if prefs.select_linked_on_double_click:
            select_face(active_face)
            bpy.ops.mesh.select_linked()

    for component in selected_components:
        component.select = True

    bm.select_history.add(active_face)
    bm.select_flush_mode()
    bmesh.update_edit_mesh(me)
    return {'FINISHED'}


def maya_edge_select(context):
    prefs = context.preferences.addons[__name__].preferences
    me = context.object.data
    bm = bmesh.from_edit_mesh(me)

    if len(bm.select_history) == 0:
        return {'CANCELLED'}

    # Everything that is currently selected.
    selected_components = [e for e in bm.edges if e.select]

    active_edge = bm.select_history.active
    previous_active_edge = bm.select_history[len(bm.select_history) - 2]
    # Sanity check.  Make sure we're actually working with edges.
    if type(active_edge) is not bmesh.types.BMEdge or type(previous_active_edge) is not bmesh.types.BMEdge:
        return {'CANCELLED'}

    relevant_neighbour_edges = get_neighbour_edges(active_edge)
    opr_selection = [active_edge, previous_active_edge]

    adjacent = False
    if previous_active_edge.index in relevant_neighbour_edges:
        adjacent = True

    if not previous_active_edge.index == active_edge.index:
        if adjacent:
            # If a vertex is shared then the active_edge and previous_active_edge are physically connected.
            # We want to select a full edge loop.
            if any([v for v in active_edge.verts if v in previous_active_edge.verts]):
                if not active_edge.is_boundary:
                    loop_edges = entire_loop(active_edge)
                    for e in loop_edges:
                        e.select = True
                elif active_edge.is_boundary:
                    boundary_edges = get_boundary_edge_loop(active_edge)
                    for i in boundary_edges:
                        bm.edges[i].select = True
            # If they're not connected but still adjacent then we want a full edge ring.
            else:
                ring_edges = entire_ring(active_edge)
                for e in ring_edges:
                    e.select = True
        # If we're not adjacent we have to test for bounded selections.
        elif not adjacent:
            test_loop_edges = entire_loop(active_edge)
            if previous_active_edge in test_loop_edges:
                if not active_edge.is_boundary:
                    new_sel = select_bounded_loop(opr_selection)
                    for i in new_sel:
                        bm.edges[i].select = True
            # If we're not in the loop test selection, try a ring test selection.
            elif previous_active_edge not in test_loop_edges:
                test_ring_edges = entire_ring(active_edge)
                if previous_active_edge in test_ring_edges:
                    new_sel = select_bounded_ring(opr_selection)
                    for i in new_sel:
                        bm.edges[i].select = True
                # If we're not in the test_loop_edges and not in the test_ring_edges
                # we're adding a new loop selection somewhere else on the mesh.
                else:
                    if active_edge.is_boundary:
                        boundary_edges = get_boundary_edge_loop(active_edge)
                        for i in boundary_edges:
                            bm.edges[i].select = True
                    elif active_edge.is_wire:
                        bpy.ops.mesh.edgering_select('INVOKE_DEFAULT', ring=False)
                    else:
                        loop_edges = entire_loop(active_edge)
                        for e in loop_edges:
                            e.select = True
    # I guess clicking an edge twice makes the previous and active the same? Or maybe the selection history is
    # only 1 item long.  Therefore we must be selecting a new loop that's not related to any previous selected edge.
    else:
        if active_edge.is_boundary:
            boundary_edges = get_boundary_edge_loop(active_edge)
            for i in boundary_edges:
                bm.edges[i].select = True
        elif active_edge.is_wire:
            bpy.ops.mesh.edgering_select('INVOKE_DEFAULT', ring=False)
        else:
            loop_edges = entire_loop(active_edge)
            for e in loop_edges:
                e.select = True

    # Finally, in addition to the new selection we made, re-select anything that was selected back when we started.
    for component in selected_components:
        component.select = True

    # I have no idea why clearing history matters for edges and not for verts/faces, but it seems that it does.
    bm.select_history.clear()
    # Re-adding the active_edge to keep it active alters the way chained selections work
    # in a way that is not like Maya so it is a user preference now.
    if prefs.leave_edge_active:
        bm.select_history.add(active_edge)
    bm.select_flush_mode()
    bmesh.update_edit_mesh(me)
    return {'FINISHED'}


# Takes a vertex and return a set of indicies for adjacent vertices.
def get_neighbour_verts(vertex):
    edges = vertex.link_edges[:]
    relevant_neighbour_verts = {v.index for e in edges for v in e.verts[:] if v != vertex}
    return relevant_neighbour_verts


# Takes a face and return a set of indicies for connected faces.
def get_neighbour_faces(face):
    face_edges = face.edges[:]
    relevant_neighbour_faces = {f.index for e in face_edges for f in e.link_faces[:] if f != face}
    return relevant_neighbour_faces


# Takes an edge and return a set of indicies for nearby edges.
# Will return some 'oddball' or extra edges if connected topology is triangles or poles.
# This is no worse than the old bpy.ops.mesh.select_more(use_face_step=True) method (slightly better, even).
def get_neighbour_edges(edge):
    edge_loops = edge.link_loops[:]
    edge_faces = edge.link_faces[:]  # Check here for more than 2 connected faces?
    face_edges = {e for f in edge_faces for e in f.edges[:]}

    if len(edge_loops) == 0:
        ring_edges = []
    # For the next 2 elif checks, link_loop hopping is only technically accurate for quads.
    elif len(edge_loops) == 1:
        ring_edges = [edge_loops[0].link_loop_radial_next.link_loop_next.link_loop_next.edge.index]
    elif len(edge_loops) > 1:
        ring_edges = [edge_loops[0].link_loop_radial_next.link_loop_next.link_loop_next.edge.index,
                      edge_loops[1].link_loop_radial_next.link_loop_next.link_loop_next.edge.index]
    # loop_edges returns a lot of edges if 1 vert connected to a pole, such as the cap of a UV Sphere.
    # e not in face_edges coincidentally removes the starting edge which is what we wanted anyway.
    loop_edges = [e.index for v in edge.verts for e in v.link_edges[:] if e not in face_edges]

    relevant_neighbour_edges = set(ring_edges + loop_edges)
    return relevant_neighbour_edges


def select_edge(active_edge):
    bpy.ops.mesh.select_all(action='DESELECT')
    active_edge.select = True


def select_vert(active_vert):
    bpy.ops.mesh.select_all(action='DESELECT')
    active_vert.select = True


def select_face(active_face):
    bpy.ops.mesh.select_all(action='DESELECT')
    active_face.select = True


# Takes a boundary edge and returns a set of indices for other boundary edges
# that are contiguous with it in the same boundary "loop".
def get_boundary_edge_loop(edge):
    prefs = bpy.context.preferences.addons[__name__].preferences
    cur_edges = [edge]
    final_selection = set()
    visited_verts = set()
    while True:
        for e in cur_edges:
            final_selection.add(e.index)
        edge_verts = {v for e in cur_edges for v in e.verts[:]}
        if not prefs.boundary_ignore_wires:
            new_edges = []
            for v in edge_verts:
                if v.index not in visited_verts:
                    linked_edges = v.link_edges[:]
                    for e in linked_edges:
                        if not any([e for e in linked_edges if e.is_wire]):
                            if e.is_boundary and e.index not in final_selection:
                                new_edges.append(e)
                visited_verts.add(v.index)
        elif prefs.boundary_ignore_wires:
            new_edges = [e for v in edge_verts for e in v.link_edges[:]
                         if e.is_boundary and e.index not in final_selection]

        if len(new_edges) == 0:
            break
        else:
            cur_edges = new_edges
    return final_selection


# Takes an edge and returns a loop of face indices (as a set) for the ring direction of that edge.
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


# ##################### Loopanar defs ##################### #

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
