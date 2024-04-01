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
    "description": "Context-aware loop selection for vertices, edges, and faces.",
    "author": "Andreas Strømberg, Chris Kohl",
    "version": (1, 6, 1),
    "blender": (2, 80, 0),
    "location": "",
    "warning": "",
    "wiki_url": "https://github.com/Stromberg90/Scripts/tree/master/Blender",
    "tracker_url": "https://github.com/Stromberg90/Scripts/issues",
    "category": "Mesh"
}

import bpy
import bmesh

classes = []
mouse_keymap = []


def cs_register_keymap_keys():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="Mesh", space_type='EMPTY')

#        kmi = km.keymap_items.new("object.context_select", 'LEFTMOUSE', 'DOUBLE_CLICK', ctrl=True)
#        kmi.properties.mode = 'SUB'
#        mouse_keymap.append((km, kmi))

        kmi = km.keymap_items.new("object.context_select", 'LEFTMOUSE', 'DOUBLE_CLICK', shift=True)
        kmi.properties.mode = 'ADD'
        mouse_keymap.append((km, kmi))

        kmi = km.keymap_items.new("object.context_select", 'LEFTMOUSE', 'DOUBLE_CLICK')
        kmi.properties.mode = 'SET'
        mouse_keymap.append((km, kmi))


def cs_unregister_keymap_keys():
    for km, kmi in mouse_keymap:
        km.keymap_items.remove(kmi)
    mouse_keymap.clear()


def cs_update_keymap(self, context):
    prefs = context.preferences.addons[__name__].preferences
    
    if prefs.add_keys_to_keymap:
        cs_register_keymap_keys()
    else:
        cs_unregister_keymap_keys()


class ContextSelectPreferences(bpy.types.AddonPreferences):
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __name__

    add_keys_to_keymap: bpy.props.BoolProperty(
        name="Add Keys to Key Map",
        description="Automatically append the add-on's keys to Blender's key map.",
        default=True,
        update=cs_update_keymap)

    select_linked_on_double_click: bpy.props.BoolProperty(
        name="Select Linked On Double Click",
        description="Double clicking on a face or a vertex (if not part of a loop selection) "
                    + "will select all components for that contiguous mesh piece",
        default=True)

    allow_non_quads_at_ends: bpy.props.BoolProperty(
        name="Allow Non-Quads At Start/End Of Face Loops",
        description="If a loop of faces terminates at a triangle or n-gon, "
                    + "allow that non-quad face to be added to the final loop selection, "
                    + "and allow using that non-quad face to begin a loop selection. "
                    + "NOTE: For bounded face selection the starting OR ending face must be a quad",
        default=True)

    terminate_self_intersects: bpy.props.BoolProperty(
        name="Terminate Self-Intersects At Intersection",
        description="If a loop or ring of vertices, edges, or faces circles around and crosses over itself, "
                    + "stop the selection at that location",
        default=False)

    ignore_boundary_wires: bpy.props.BoolProperty(
        name="Ignore Wire Edges On Boundaries",
        description="If wire edges are attached to a boundary vertex the selection will ignore it, "
                    + "pass through, and continue selecting the boundary loop",
        default=False)

    leave_edge_active: bpy.props.BoolProperty(
        name="Leave Edge Active After Selections",
        description="When selecting edge loops or edge rings, the active edge will remain active. "
                    + "NOTE: This changes the behavior of chained neighbour selections",
        default=False)

    ignore_hidden_geometry: bpy.props.BoolProperty(
        name="Ignore Hidden Geometry",
        description="Loop selections will ignore hidden components and continue through to the other side",
        default=False)

    return_single_loop: bpy.props.BoolProperty(
        name="Select Single Bounded Loop",
        description="For bounded selections, if there are multiple equal-length paths between the start and "
                    + "end component, select only one loop instead of all possible loops",
        default=False)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "add_keys_to_keymap")
        layout.label(text="General Selection:")
        layout.prop(self, "select_linked_on_double_click")
        layout.prop(self, "terminate_self_intersects")
        layout.prop(self, "ignore_hidden_geometry")
        layout.prop(self, "return_single_loop")
        layout.label(text="Vertex Selection:")
        layout.prop(self, "ignore_boundary_wires")
        layout.label(text="Edge Selection:")
        layout.prop(self, "leave_edge_active")
        layout.prop(self, "ignore_boundary_wires")
        layout.label(text="Face Selection:")
        layout.prop(self, "allow_non_quads_at_ends")
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


class ReportErr(bpy.types.Operator):
    bl_idname = 'wm.report_err'
    bl_label = 'Custom Error Reporter'
    bl_description = 'Mini Operator for using self.report outside of an operator'

    err_type: bpy.props.StringProperty(name="Error Type")
    err_message: bpy.props.StringProperty(name="Error Message")

    def execute(self, context):
        self.report({self.err_type}, self.err_message)
        return {'CANCELLED'}
classes.append(ReportErr)


class OBJECT_OT_context_select(bpy.types.Operator):
    bl_idname = "object.context_select"
    bl_label = "Context Select"
    bl_description = ('Contextually select vertex loops, edge loops, face loops, partial vertex loops, '
                     + 'partial edge loops, partial face loops, edge rings, partial edge rings, '
                     + 'vertex boundaries, edge boundaries, partial vertex boundaries, and partial edge boundaries')
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    select_modes = [
    ("SET", "Set", "Set a new selection (deselects any existing selection)", 1),
    ("ADD", "Extend", "Extend selection instead of deselecting everything first", 2),
    ]
#    ("SUB", "Subtract", "Subtract from the existing selection", 3),

    mode: bpy.props.EnumProperty(items=select_modes, name="Selection Mode",
    description="Choose whether to set or extend selection", default="SET")

    def execute(self, context):
        if context.object.mode == ObjectMode.EDIT:
            # Checks if we are in vertex selection mode.
            if context.tool_settings.mesh_select_mode[0]:
                return context_vert_select(context, self.mode)

            # Checks if we are in edge selection mode.
            if context.tool_settings.mesh_select_mode[1]:
                return context_edge_select(context, self.mode)

            # Checks if we are in face selection mode.
            if context.tool_settings.mesh_select_mode[2]:
                if context.area.type == 'VIEW_3D':
                    return context_face_select(context, self.mode)
                elif context.area.type == 'IMAGE_EDITOR':
                    bpy.ops.uv.select_linked_pick(extend=False)
        return {'FINISHED'}
classes.append(OBJECT_OT_context_select)


def context_vert_select(context, mode):
    prefs = context.preferences.addons[__name__].preferences
    me = context.object.data
    bm = bmesh.from_edit_mesh(me)

    if len(bm.select_history) == 0:
        return {'CANCELLED'}

    new_sel = None
    active_vert = bm.select_history.active
    previous_active_vert = bm.select_history[len(bm.select_history) - 2]
    # Sanity check.  Make sure we're actually working with vertices.
    if type(active_vert) is not bmesh.types.BMVert or type(previous_active_vert) is not bmesh.types.BMVert:
        return {'CANCELLED'}

    adjacent = previous_active_vert in get_neighbour_verts(active_vert)

    # If the two components are not the same it would correspond to a mode of 'ADD'
    if not previous_active_vert.index == active_vert.index:
        if adjacent:
            active_edge = [e for e in active_vert.link_edges if e in previous_active_vert.link_edges][0]
            if active_edge.hide and not prefs.ignore_hidden_geometry:
                return {'CANCELLED'}
            if active_edge.is_manifold:
                new_sel = full_loop_vert_manifold(prefs, active_vert, active_edge)
            elif active_edge.is_boundary:
                if active_vert.is_manifold:
                    new_sel = full_loop_vert_boundary(prefs, active_vert)
                elif previous_active_vert.is_manifold:
                    new_sel = full_loop_vert_boundary(prefs, previous_active_vert)
                else:
                    new_sel = full_loop_vert_boundary(prefs, active_vert)
            elif active_edge.is_wire:
                if active_vert.is_wire:
                    new_sel = full_loop_vert_wire(prefs, active_vert)
                elif previous_active_vert.is_wire:
                    new_sel = full_loop_vert_wire(prefs, previous_active_vert)
        elif not adjacent:
            new_sel = get_bounded_selection(active_vert, previous_active_vert, mode='VERT')

    if new_sel:
        for v in new_sel:
            v.select = True
    elif not new_sel and prefs.select_linked_on_double_click:
        if mode in ('SET', 'ADD'):
            bpy.ops.mesh.select_linked_pick('INVOKE_DEFAULT', delimit=set())
        else:
            bpy.ops.mesh.select_linked_pick('INVOKE_DEFAULT', delimit=set(), deselect=True)

    bm.select_history.add(active_vert)  # Re-add active_vert to history to keep it active.
    bm.select_flush_mode()
    bmesh.update_edit_mesh(me)
    return {'FINISHED'}


def context_face_select(context, mode):
    prefs = context.preferences.addons[__name__].preferences
    me = context.object.data
    bm = bmesh.from_edit_mesh(me)

    if len(bm.select_history) == 0:
        return {'CANCELLED'}

    new_sel = None
    active_face = bm.select_history.active
    previous_active_face = bm.select_history[len(bm.select_history) - 2]
    # Sanity check.  Make sure we're actually working with faces.
    if type(active_face) is not bmesh.types.BMFace or type(previous_active_face) is not bmesh.types.BMFace:
        return {'CANCELLED'}

    if len(active_face.verts) != 4 and len(previous_active_face.verts) != 4:
        quads = (0, 0)
    elif len(active_face.verts) == 4 and len(previous_active_face.verts) == 4:
        quads = (1, 1)
    elif len(active_face.verts) == 4 and len(previous_active_face.verts) != 4:
        quads = (1, 0)
    elif len(active_face.verts) != 4 and len(previous_active_face.verts) == 4:
        quads = (0, 1)

    adjacent = previous_active_face in get_neighbour_faces(active_face)

    # If the two components are not the same it would correspond to a mode of 'ADD'
    if not previous_active_face.index == active_face.index and not quads == (0, 0):
        if adjacent and (quads == (1, 1) or prefs.allow_non_quads_at_ends):
            ring_edge = [e for e in active_face.edges if e in previous_active_face.edges][0]
            new_sel = full_loop_face(ring_edge, active_face)
        elif not adjacent and (quads == (1, 1) or prefs.allow_non_quads_at_ends):
            new_sel = get_bounded_selection(active_face, previous_active_face, mode='FACE')

    if new_sel:
        for f in new_sel:
            f.select = True
    elif not new_sel and prefs.select_linked_on_double_click:
        if mode in ('SET', 'ADD'):
            bpy.ops.mesh.select_linked_pick('INVOKE_DEFAULT', delimit=set())
        else:
            bpy.ops.mesh.select_linked_pick('INVOKE_DEFAULT', delimit=set(), deselect=True)

    bm.select_history.add(active_face)
    bm.select_flush_mode()
    bmesh.update_edit_mesh(me)
    return {'FINISHED'}


def context_edge_select(context, mode):
    prefs = context.preferences.addons[__name__].preferences
    me = context.object.data
    bm = bmesh.from_edit_mesh(me)

    if len(bm.select_history) == 0:
        return {'CANCELLED'}

    new_sel = None
    active_edge = bm.select_history.active
    previous_active_edge = bm.select_history[len(bm.select_history) - 2]
    # Sanity check.  Make sure we're actually working with edges.
    if type(active_edge) is not bmesh.types.BMEdge or type(previous_active_edge) is not bmesh.types.BMEdge:
        return {'CANCELLED'}

    adjacent = previous_active_edge in get_neighbour_edges(active_edge)

    # If the previous edge and current edge are different we are doing a Shift+Double Click selection.
    # This corresponds to a mode of 'ADD'
    # This could be a complete edge ring/loop, or partial ring/loop.
    if not previous_active_edge.index == active_edge.index:
        if adjacent:
            # If a vertex is shared then the active_edge and previous_active_edge are physically connected.
            # We want to select a full edge loop.
            if any([v for v in active_edge.verts if v in previous_active_edge.verts]):
                if active_edge.is_manifold:
                    new_sel = full_loop_edge_manifold(active_edge)
                elif active_edge.is_boundary:
                    new_sel = full_loop_edge_boundary(prefs, active_edge)
                elif active_edge.is_wire:
                    new_sel = full_loop_edge_wire(prefs, active_edge)
                    if len(new_sel) == 1:  # Not sure if this condition is ever true due to filters elsewhere
                        new_sel = None
                        bpy.ops.mesh.loop_select('INVOKE_DEFAULT', extend=True)
            # If they're not connected but still adjacent then we want a full edge ring.
            else:
                if active_edge.is_manifold:
                    new_sel = full_ring_edge_manifold(prefs, active_edge)
                else:
                    new_sel = full_ring_edge_manifold(prefs, previous_active_edge)
        # If we're not adjacent we have to test for bounded selections.
        elif not adjacent:
            new_sel = get_bounded_selection(active_edge, previous_active_edge, mode='EDGE')
            if not new_sel:
                if active_edge.is_manifold:
                    new_sel = full_loop_edge_manifold(active_edge)
                elif active_edge.is_boundary:
                    new_sel = full_loop_edge_boundary(prefs, active_edge)
                elif active_edge.is_wire:
                    new_sel = full_loop_edge_wire(prefs, active_edge)
                    if len(new_sel) == 1:
                        new_sel = None
                        bpy.ops.mesh.loop_select('INVOKE_DEFAULT', extend=True)

    # This corresponds to a mode of 'SET'
    else:
        if active_edge.is_manifold:
            new_sel = full_loop_edge_manifold(active_edge)
        elif active_edge.is_boundary:
            new_sel = full_loop_edge_boundary(prefs, active_edge)
        elif active_edge.is_wire:
            new_sel = full_loop_edge_wire(prefs, active_edge)
            if len(new_sel) == 1:
                new_sel = None
                if mode == 'SET':
                    bpy.ops.mesh.loop_select('INVOKE_DEFAULT')
                else:
                    bpy.ops.mesh.loop_select('INVOKE_DEFAULT', extend=True)

    if new_sel:
        for e in new_sel:
            e.select = True

    # No idea why clearing history matters for edges and not for verts/faces, but it seems that it does.
    bm.select_history.clear()
    # Re-adding the active_edge to keep it active alters the way chained selections work so it's a user preference.
    # We'd have to replace view3d.select and some Blender functionality to retain active edge AND desired behavior.
    if prefs.leave_edge_active:
        bm.select_history.add(active_edge)
    bm.select_flush_mode()
    bmesh.update_edit_mesh(me)
    return {'FINISHED'}


# Takes a vertex and returns a set of adjacent vertices.
def get_neighbour_verts(vertex):
    edges = vertex.link_edges  # There's no nonmanifold check but that hasn't been a problem so far.
    relevant_neighbour_verts = {v for e in edges for v in e.verts if v != vertex}
    return relevant_neighbour_verts


# Takes a face and returns a set of connected faces.
def get_neighbour_faces(face):
    face_edges = face.edges  # There's no nonmanifold check but that hasn't been a problem so far.
    relevant_neighbour_faces = {f for e in face_edges for f in e.link_faces if f != face}
    return relevant_neighbour_faces


# Takes an edge and returns a set of nearby edges.
# Optionally takes a mode and will return only components for that mode, otherwise returns all.
def get_neighbour_edges(edge, mode=''):
    prefs = bpy.context.preferences.addons[__name__].preferences
    if mode not in ['', 'LOOP', 'RING']:
        bpy.ops.wm.report_err(err_type = 'ERROR_INVALID_INPUT',
                              err_message = "ERROR: get_neighbour_edges mode must be one of: "
                              + "'', 'LOOP', or 'RING'")
        return {'CANCELLED'}

    edge_faces = edge.link_faces
    face_edges = {e for f in edge_faces for e in f.edges}

    ring_edges = []
    if len(edge_faces) > 0:
        for f in edge_faces:
            if len(f.verts) == 4:
                # Get the only 2 verts that are not in the edge we start with.
                target_verts = [v for v in f.verts if v not in edge.verts]
                # Add the only edge that corresponds to those two verts.
                ring_edges.extend([e for e in f.edges if target_verts[0] in e.verts and target_verts[1] in e.verts])

    if edge.is_manifold:
        # Vertices connected to more or less than 4 edges are disqualified.
        loop_edges = [e for v in edge.verts for e in v.link_edges
                     if len(v.link_edges) == 4 and e.is_manifold and e not in face_edges]
    elif edge.is_boundary:
        edge_verts = edge.verts
        if not prefs.ignore_boundary_wires:
            loop_edges = []
            for v in edge_verts:
                linked_edges = v.link_edges
                for e in linked_edges:
                    if not any([e for e in linked_edges if e.is_wire]):
                        if e.is_boundary and e is not edge:
                            loop_edges.append(e)
        elif prefs.ignore_boundary_wires:
            loop_edges = [e for v in edge_verts for e in v.link_edges
                         if e.is_boundary and e is not edge]
    # There may be more that we can do with wires but for now this will have to do.
    elif edge.is_wire:
        loop_edges = []
        for vert in edge.verts:
            linked_edges = vert.link_edges
            if len(linked_edges) == 2:
                loop_edges.extend([e for e in linked_edges if e.is_wire and e is not edge])
    # Nonmanifold
    elif len(edge_faces) > 2:
        loop_edges = [e for v in edge.verts for e in v.link_edges
                     if not e.is_manifold and not e.is_wire and e not in face_edges]

    relevant_neighbour_edges = set(ring_edges + loop_edges)
    if mode == '':
        return relevant_neighbour_edges  # Returns a set.
    elif mode == 'LOOP':
        return loop_edges  # Returns a list, not a set. This is intentional.
    elif mode == 'RING':
        return ring_edges  # Returns a list, not a set. This is intentional.


# Deselect everything and select only the given component. 
# Replaces select_edge, select_vert, and select_face (NOT ACTUALLY BEING USED ANYWHERE AT THE MOMENT)
def select_component(component):
    bpy.ops.mesh.select_all(action='DESELECT')
    component.select = True


# Takes two components of the same type and returns a set of components that are bounded between them.
def get_bounded_selection(component0, component1, mode):
    prefs = bpy.context.preferences.addons[__name__].preferences

    if not component0 or not component1 or component0.index == component1.index:
        bpy.ops.wm.report_err(err_type = 'ERROR_INVALID_INPUT',
                              err_message = "ERROR: You must supply two components of the same type and a mode.")
        return {'CANCELLED'}
    if mode not in ['VERT', 'EDGE', 'FACE']:
        bpy.ops.wm.report_err(err_type = 'ERROR_INVALID_INPUT',
                              err_message = "ERROR: get_bounded_selection mode must be one of "
                              + "'VERT', 'EDGE', or 'FACE'")
        return {'CANCELLED'}
    if type(component0) != type(component1):
        bpy.ops.wm.report_err(err_type = 'ERROR_INVALID_INPUT',
                              err_message = "ERROR: Both components must be the same type and "
                              + "must match the supplied mode.")
        return {'CANCELLED'}

    ends = [component0, component1]
    c0 = component0
    c1 = component1

    if mode == 'VERT':
        c0_edges = c0.link_edges
        c0_boundary = [e for e in c0_edges if e.is_boundary]
        c0_wire = [e for e in c0_edges if e.is_wire]

        c1_edges = c1.link_edges
        c1_boundary = [e for e in c1_edges if e.is_boundary]
        c1_wire = [e for e in c1_edges if e.is_wire]

        if len(c0_edges) == 0 or len(c1_edges) == 0:  # Floating vertex not connected to anything
            return None

        # At least one internal manifold vertex
        if (c0.is_manifold and not c0.is_boundary) or (c1.is_manifold and not c1.is_boundary):
            if c0.is_manifold and c1.is_manifold and not c0.is_boundary and not c1.is_boundary:  # Both are manifold
                if len(c0_edges) == 4:
                    starting_vert = c0
                elif len(c0_edges) != 4 and len(c1_edges) == 4:
                    starting_vert = c1
                elif len(c0_edges) != 4 and len(c1_edges) != 4:
                    return None
            elif c0.is_manifold and not c0.is_boundary:  # One internal manifold and one of any other vertex type
                starting_vert = c0
            elif c1.is_manifold and not c1.is_boundary:  # One internal manifold and one of any other vertex type
                starting_vert = c1
            connected_loops = bounded_loop_vert_manifold(prefs, starting_vert, ends)

        # Two of any boundary vertex type
        elif c0.is_boundary and c1.is_boundary:
            if c0.is_manifold:  # Normal or "clean" boundary vert
                starting_vert = c0
            elif c1.is_manifold:  # Normal or "clean" boundary vert
                starting_vert = c1
            elif len(c0_wire) > 0 and len(c0_boundary) == 2:  # Boundary vert has wire edge but not self-intersect
                starting_vert = c0
            elif len(c1_wire) > 0 and len(c1_boundary) == 2:  # Boundary vert has wire edge but not self-intersect
                starting_vert = c1
            else:  # Only remaining possibility is both are intersect, in which case, good luck
                starting_vert = c0
            connected_loops = bounded_loop_vert_boundary(prefs, starting_vert, ends)

        # At least one wire vertex
        elif c0.is_wire or c1.is_wire:
            if c0.is_wire and c1.is_wire:  # Two wire verts
                if 0 < len(c0_wire) < 3:  # Can attempt if 1 or 2 connected wire edges
                    starting_vert = c0
                elif 0 < len(c1_wire) < 3:  # Can attempt if 1 or 2 connected wire edges
                    starting_vert = c1
                elif len(c0_wire) > 2 and len(c1_wire) > 2:
                    return None
            elif (c0.is_wire or c1.is_wire) and (not c0.is_wire or not c1.is_wire):  # One wire and one not wire
                return None
            connected_loops = bounded_loop_vert_wire(prefs, starting_vert, ends)

        # Two non-manifold vertices (extrusion from a manifold topology edge)
        elif not c0.is_manifold and not c1.is_manifold and not c0.is_boundary and not c1.is_boundary\
             and len(c0_wire) == 0 and len(c1_wire) == 0:
            return None  # For now, return none because we haven't written non-manifold selector.

        # At least one internal with a wire extrusion
        elif (not c0.is_boundary and len(c0_wire) > 0) or (not c1.is_boundary and len(c1_wire) > 0):
            # Two internal with a wire extrusion
            if not c0.is_boundary and len(c0_wire) > 0 and not c1.is_boundary and len(c1_wire) > 0:
                starting_vert = c0
            elif c0.is_boundary:  # One internal wire extrusion and one boundary of any type
                starting_vert = c1
            elif c1.is_boundary:  # One internal wire extrusion and one boundary of any type
                starting_vert = c0
            # One internal non-manifold edge extrusion and one internal wire extrusion
            elif not c0.is_manifold and len(c0_wire) == 0 and not c1.is_boundary and len(c1_wire) > 0:
                starting_vert = c1
            # One internal non-manifold edge extrusion and one internal wire extrusion
            elif not c1.is_manifold and len(c1_wire) == 0 and not c0.is_boundary and len(c0_wire) > 0:
                starting_vert = c0
            connected_loops = bounded_loop_vert_manifold(prefs, starting_vert, ends)

        else:  # Any other condition that's been missed
            return None

    if mode == 'EDGE':
        c0_faces = c0.link_faces
        c0_loop_dirs = get_neighbour_edges(c0, mode='LOOP')  # edges
        c0_ring_dirs = get_neighbour_edges(c0, mode='RING')  # edges

        c1_faces = c1.link_faces
        c1_loop_dirs = get_neighbour_edges(c1, mode='LOOP')  # edges
        c1_ring_dirs = get_neighbour_edges(c1, mode='RING')  # edges

        connected_loops = []
        if c0.is_manifold and c1.is_manifold:  # Manifold
            starting_edge = c0

            if len(c0_loop_dirs):
                connected_loops = bounded_loop_edge_manifold(prefs, starting_edge, ends)
            if len(connected_loops) > 0:
                # Priority behavior is that if there is a positive match for a bounded loop selection then
                # return the loop selection. It doesn't care if there's an equal-length ring selection too.
                pass
            elif len(c0_ring_dirs):
                if any(map(lambda x: len(x.verts) != 4, c0_faces)):
                    starting_edge = c1

                connected_loops = bounded_ring_edge_manifold(prefs, starting_edge, ends)

        elif c0.is_boundary and c1.is_boundary:  # Boundary
            connected_loops = bounded_loop_edge_boundary(prefs, c0, ends)

        elif c0.is_wire and c1.is_wire:  # Wire
            connected_loops = bounded_loop_edge_wire(prefs, c0, ends)

        elif len(c0_faces) > 2 and len(c1_faces) > 2:  # Non-manifold edge extrusion/intersection
            return None  # For now, return none because we haven't written non-manifold selector.

        elif c0.is_manifold and (c1.is_boundary or len(c1_faces) > 2):  # Only possible bounded selection is a ring.
            starting_edge = c0
            connected_loops = bounded_ring_edge_manifold(prefs, starting_edge, ends)

        elif c1.is_manifold and (c0.is_boundary or len(c0_faces) > 2):  # Only possible bounded selection is a ring.
            starting_edge = c1
            connected_loops = bounded_ring_edge_manifold(prefs, starting_edge, ends)

        # There is no conceivable condition where a wire edge can be part of any other type of loop or ring.
        elif (c0.is_wire and not c1.is_wire) or (c1.is_wire and not c0.is_wire):
            return None

    if mode == 'FACE':
        # Not implemented yet but if one of the faces is a triangle and the other is a quad we could use the triangle
        # as our starting_face if the pref allows cause n=3 instead of n=4 to find out if the other face is connected
        if not prefs.allow_non_quads_at_ends and (len(c0.verts) != 4 or len(c1.verts) != 4):
            return None
        if len(c0.verts) == 4:
            starting_face = c0
        elif len(c0.verts) != 4 and len(c1.verts) == 4:
            starting_face = c1
        else:
            return None

        connected_loops = bounded_loop_face(prefs, starting_face, ends)

    connected_loops.sort(key = lambda x: len(x))
    if len(connected_loops) == 0:
        return None
    elif len(connected_loops) == 1:
        return {i for i in connected_loops[0]}
    # If multiple bounded loop candidates of identical length exist, this pref returns only the first loop.
    elif prefs.return_single_loop and len(connected_loops) > 1:
        return {i for i in connected_loops[0]}
    else:
        return {i for loop in connected_loops if len(loop) == len(connected_loops[0]) for i in loop}


# ##################### Bounded Selections ##################### #

# Takes 2 separated verts, and which vert to start with, and returns a list of loop lists of vertices.
def bounded_loop_vert_manifold(prefs, starting_vert, ends):
    edges = [e for e in starting_vert.link_edges if not e.is_wire and not e.is_boundary]
    if len(edges) > 4:
        return []
    candidate_dirs = []
    for e in edges:
        loops = [loop for loop in e.link_loops]
        candidate_dirs.append(loops[0])
    connected_loops = []
    reference_list = set()

    for loop in candidate_dirs:
        if loop != "skip":
            if not prefs.ignore_hidden_geometry and loop.edge.hide:
                continue
            loop_edge = loop.edge
            reference_list.clear()  # Don't want *previous* partial loop data in here.
            partial_list = partial_loop_vert_manifold(prefs, loop, loop_edge, starting_vert, reference_list, ends)
            if "infinite" in partial_list:
                partial_list.discard("infinite")
                opposite_edge = get_opposite_edge(loop_edge, starting_vert)
                if opposite_edge is not None:
                    for l in opposite_edge.link_loops:
                        if l in candidate_dirs:
                            candidate_dirs[candidate_dirs.index(l)] = "skip"
            if ends[0] in partial_list and ends[1] in partial_list:
                connected_loops.append(partial_list)
    return connected_loops


# Takes 2 separated boundary vertices, and which vertex to start with, and returns a list of loop lists of vertices.
# NOTE: Must determine externally which vert to start with, whether the active or previous active
# e.g. it is desirable to start on a boundary vert with only 2 boundary edges and no wire edges
def bounded_loop_vert_boundary(prefs, starting_vert, ends):
    connected_loops = []
    if prefs.ignore_hidden_geometry:
        edges = [e for e in starting_vert.link_edges if e.is_boundary]
    else:
        edges = [e for e in starting_vert.link_edges if e.is_boundary and not e.hide]

    for e in edges:
        partial_list = partial_loop_vert_boundary(prefs, starting_vert, e, ends)
        if "infinite" not in partial_list:
            if ends[0] in partial_list and ends[1] in partial_list:
                connected_loops.append([c for c in partial_list])
        else:
            break  # If we're infinite then there is no bounded selection to get
    return connected_loops


# Takes a wire vertex and a start/end vert and returns a list of wire vertices if they are part of a stand-alone loop
# Only works on wire loops with 1-2 edges per vertex
def bounded_loop_vert_wire(prefs, starting_vert, ends):
    connected_loops = []
    if prefs.ignore_hidden_geometry:
        edges = [e for e in starting_vert.link_edges if e.is_wire]
    else:
        edges = [e for e in starting_vert.link_edges if e.is_wire and not e.hide]

    if len(edges) == 1 or len(edges) == 2:
        for e in edges:
            partial_list = partial_loop_vert_wire(prefs, starting_vert, e, ends)
            if "infinite" not in partial_list:
                if ends[0] in partial_list and ends[1] in partial_list:
                    connected_loops.append([c for c in partial_list])
            else:
                break  # If we're infinite then there is no bounded selection to get
    else:
        return None
    return connected_loops


# Takes 2 separated faces, and which face to start with, and returns a list of loop lists of faces.
def bounded_loop_face(prefs, starting_face, ends):
    # Must use the face's loops instead of its edges because edge's loop[0] could point to a different face.
    candidate_dirs = [loop for loop in starting_face.loops]
    connected_loops = []
    reference_list = set()

    for loop in candidate_dirs:
        if loop != "skip":
            reference_list.clear()  # Don't want *previous* partial loop data in here.
            partial_list = partial_loop_face(prefs, loop, starting_face, reference_list, ends)
            if "infinite" in partial_list:
                partial_list.discard("infinite")
                if len(starting_face.verts) == 4 and loop.link_loop_next.link_loop_next in candidate_dirs:
                    candidate_dirs[candidate_dirs.index(loop.link_loop_next.link_loop_next)] = "skip"
            if ends[0] in partial_list and ends[1] in partial_list:
                connected_loops.append([c for c in partial_list])
    return connected_loops


# Takes 2 separated edges, and which edge to start with, and returns a list of loop lists of edges.
def bounded_loop_edge_manifold(prefs, starting_edge, ends):
    loop = starting_edge.link_loops[0]
    connected_loops = []
    reference_list = set()

    for v in starting_edge.verts:
        if len(v.link_loops) != 4:
            continue
        reference_list.clear()  # Don't want *previous* partial loop data in here.
        o_vert = starting_edge.other_vert(v)
        partial_list = partial_loop_edge_manifold(prefs, loop, starting_edge, o_vert, reference_list, ends)
        if "infinite" not in partial_list:
            if ends[0] in partial_list and ends[1] in partial_list:
                connected_loops.append([c for c in partial_list])
        else:
            break  # If we're infinite then there is no bounded selection to get
    return connected_loops


# Takes 2 separated edges, and which edge to start with, and returns a list of ring lists of edges.
def bounded_ring_edge_manifold(prefs, starting_edge, ends):
    starting_loop = starting_edge.link_loops[0]
    loops = [starting_loop, starting_loop.link_loop_radial_next]
    connected_loops = []
    reference_list = set()

    for loop in loops:
        reference_list.clear()  # Don't want *previous* partial loop data in here.
        partial_list = partial_ring_edge(prefs, loop, starting_edge, reference_list, ends)
        if "infinite" not in partial_list:
            if ends[0] in partial_list and ends[1] in partial_list:
                connected_loops.append([c for c in partial_list])
        else:
            break  # If we're infinite then there is no bounded selection to get
    return connected_loops


# Takes 2 separated boundary edges, and which edge to start with, and returns a list of loop lists of edges.
def bounded_loop_edge_boundary(prefs, starting_edge, ends):
    connected_loops = []
    verts = starting_edge.verts

    for v in verts:
        partial_list = partial_loop_edge_boundary(prefs, starting_edge, v, ends)
        if "infinite" not in partial_list:
            if ends[0] in partial_list and ends[1] in partial_list:
                connected_loops.append([c for c in partial_list])
        else:
            break  # If we're infinite then there is no bounded selection to get
    return connected_loops


# Takes a wire edge and a start/end edge and returns a list of wire vertices if they are part of a stand-alone loop
# Only works on wire loops with 1-2 edges per vertex
def bounded_loop_edge_wire(prefs, starting_edge, ends):
    connected_loops = []
    verts = starting_edge.verts

    for v in verts:
        partial_list = partial_loop_edge_wire(prefs, starting_edge, v, ends)
        if "infinite" not in partial_list:
            if ends[0] in partial_list and ends[1] in partial_list:
                connected_loops.append([c for c in partial_list])
        else:
            break  # If we're infinite then there is no bounded selection to get
    return connected_loops


# ##################### Full Loop Selections ##################### #

# Takes a starting vertex and a connected reference edge and returns a full loop of vertex indices.
def full_loop_vert_manifold(prefs, starting_vert, starting_edge):
    if not prefs.ignore_hidden_geometry and starting_edge.hide:
        return None
    if len(starting_vert.link_loops) != 4:  # This should really be handled outside of this function.
        starting_vert = starting_edge.other_vert(starting_vert)
        if len(starting_vert.link_loops) != 4:  # Checking if both verts are unusable.
            return None
    opposite_edge = get_opposite_edge(starting_edge, starting_vert)
    if opposite_edge is not None:
        loops = [starting_edge.link_loops[0], opposite_edge.link_loops[0]]
    else:
        loops = [starting_edge.link_loops[0]]
    vert_list = set()
    reference_list = set()

    for loop in loops:
        loop_edge = loop.edge
        if not prefs.ignore_hidden_geometry and loop_edge.hide:
            continue
        partial_list = partial_loop_vert_manifold(prefs, loop, loop_edge, starting_vert, reference_list)
        if "infinite" not in partial_list:
            vert_list.update(partial_list)
        else:
            partial_list.discard("infinite")
            vert_list.update(partial_list)
            break  # Early out so we don't get the same loop twice.
    return vert_list


# Takes a boundary vertex and returns a list of boundary vertices.
# NOTE: Must determine externally which vert to start with, whether the active or previous active
# e.g. it is desirable to start on a boundary vert with only 2 boundary edges and no wire edges
def full_loop_vert_boundary(prefs, starting_vert):
    if prefs.ignore_hidden_geometry:
        edges = [e for e in starting_vert.link_edges if e.is_boundary]
    else:
        edges = [e for e in starting_vert.link_edges if e.is_boundary and not e.hide]
    vert_list = set()

    for e in edges:
        partial_list = partial_loop_vert_boundary(prefs, starting_vert, e)
        if "infinite" not in partial_list:
            vert_list.update(partial_list)
        else:
            partial_list.discard("infinite")
            vert_list.update(partial_list)
            break  # Early out so we don't get the same loop twice.
    return vert_list


# Takes a wire vertex and returns a list of wire vertices if they are part of a stand-alone loop
# Only works on wire loops with 1-2 edges per vertex
def full_loop_vert_wire(prefs, starting_vert):
    if prefs.ignore_hidden_geometry:
        edges = [e for e in starting_vert.link_edges if e.is_wire]
    else:
        edges = [e for e in starting_vert.link_edges if e.is_wire and not e.hide]
    vert_list = set()

    if len(edges) == 1 or len(edges) == 2:
        for e in edges:
            partial_list = partial_loop_vert_wire(prefs, starting_vert, e)
            if "infinite" not in partial_list:
                vert_list.update(partial_list)
            else:
                partial_list.discard("infinite")
                vert_list.update(partial_list)
                break  # Early out so we don't get the same loop twice.
    else:
        return None
    return vert_list


# Takes an edge and face and returns a loop of face indices (as a set) for the ring direction of that edge.
def full_loop_face(edge, face):
    if len(edge.link_loops) > 2:
        return None

    prefs = bpy.context.preferences.addons[__name__].preferences
    starting_loop = [loop for loop in edge.link_loops if loop in face.loops][0]
    loops = [starting_loop, starting_loop.link_loop_radial_next]
    face_list = set()
    reference_list = set()

    for loop in loops:
        starting_face = loop.face
        partial_list = partial_loop_face(prefs, loop, starting_face, reference_list)
        if "infinite" not in partial_list:
            face_list.update(partial_list)
        else:
            partial_list.discard("infinite")
            face_list.update(partial_list)
            break  # Early out so we don't get the same loop twice.
    return face_list


# Takes an edge and returns a full loop of edge indices.
def full_loop_edge_manifold(edge):
    starting_loop = edge.link_loops[0]
    if len(edge.verts[0].link_loops) == 4:
        starting_vert = edge.verts[0]
    elif len(edge.verts[1].link_loops) == 4:
        starting_vert = edge.verts[1]
    else:
        return []
    opposite_edge = get_opposite_edge(edge, starting_vert)
    if opposite_edge is not None:
        loops = [edge.link_loops[0], opposite_edge.link_loops[0]]
    else:
        loops = [edge.link_loops[0]]

    prefs = bpy.context.preferences.addons[__name__].preferences
    edge_list = set()
    reference_list = set()

    for loop in loops:
        new_edges = partial_loop_edge_manifold(prefs, loop, loop.edge, starting_vert, reference_list)
        if "infinite" not in new_edges:
            edge_list.update(new_edges)
        else:
            new_edges.discard("infinite")
            edge_list.update(new_edges)
            break  # Early out so we don't get the same loop twice.
    return edge_list


# Takes an edge and returns a ring of edge indices (as a set) for that edge.
def full_ring_edge_manifold(prefs, starting_edge):
    starting_loop = starting_edge.link_loops[0]
    loops = [starting_loop, starting_loop.link_loop_radial_next]
    edge_list = set()
    reference_list = set()

    for loop in loops:
        partial_list = partial_ring_edge(prefs, loop, starting_edge, reference_list)
        if "infinite" not in partial_list:
            edge_list.update(partial_list)
        else:
            partial_list.discard("infinite")
            edge_list.update(partial_list)
            break  # Early out so we don't get the same loop twice.
    return edge_list


# Takes a boundary edge and returns a list of boundary edge indices.
def full_loop_edge_boundary(prefs, edge):
    verts = edge.verts
    edge_list = set()

    for v in verts:
        new_edges = partial_loop_edge_boundary(prefs, edge, v)
        if "infinite" not in new_edges:
            edge_list.update(new_edges)
        else:
            new_edges.discard("infinite")
            edge_list.update(new_edges)
            break  # Early out so we don't get the same loop twice.
    return edge_list


# Takes a wire edge and returns a list of connected wire edges in a loop.
# Only works on wire loops with 1-2 edges per vertex
def full_loop_edge_wire(prefs, edge):
    verts = edge.verts
    edge_list = set()

    for v in verts:
        new_edges = partial_loop_edge_wire(prefs, edge, v)
        if "infinite" not in new_edges:
            edge_list.update(new_edges)
        else:
            new_edges.discard("infinite")
            edge_list.update(new_edges)
            break  # Early out so we don't get the same loop twice.
    return edge_list

# ##################### Partial Loop (Fragment) Selections ##################### #

# Takes a loop, reference edge and vertex, and returns a set of verts starting at the vert until reaching a dead end.
# For a bounded selection between two vertices it also requires the two end vertices for dead end validation.
def partial_loop_vert_manifold(prefs, loop, starting_edge, starting_vert, reference_list, ends=''):
    e_step = starting_edge
    pv = starting_vert  # Previous Vert
    cv = starting_edge.other_vert(starting_vert)  # Current Vert
    partial_list = {pv}

    while True:
        if cv in loop.link_loop_prev.edge.verts:
            loop = loop.link_loop_prev
        elif cv in loop.link_loop_next.edge.verts:
            loop = loop.link_loop_next

        pv = cv
        next_loop = fan_loop_extension(e_step, loop, cv)

        if next_loop:
            e_step = next_loop.edge
            cv = e_step.other_vert(cv)
            loop = next_loop

            # Check to see if next component matches dead end conditions
            if not ends:
                dead_end = dead_end_vert_manifold(prefs, pv, e_step, starting_vert, partial_list, reference_list)
            else:
                dead_end = dead_end_vert_manifold(prefs, pv, e_step, starting_vert, partial_list, reference_list, ends)

            reference_list.add(pv)
            # Add component to list.
            partial_list.add(pv)  # It would be better if the dead_end test could break before here
            if dead_end:
                break
        else:  # finite and we've reached an end
            partial_list.add(pv)
            break
    return partial_list  # Return the completed loop


# Takes a vertex and connected edge and returns a set of boundary verts starting at the vert until reaching a dead end.
# For a bounded selection between two vertices it also requires the two end vertices for dead end validation.
def partial_loop_vert_boundary(prefs, starting_vert, starting_edge, ends=''):
    cur_edges = [starting_edge]
    visited_edges = {starting_edge}
    visited_verts = {starting_vert}

    loop = 0
    while True:
        edge_verts = [v for e in cur_edges for v in e.verts if v not in visited_verts]
        new_edges = []
        for v in edge_verts:
            linked_edges = {e for e in v.link_edges if e.is_boundary or e.is_wire}
            for e in linked_edges:
                if not ends:
                    dead_end = dead_end_vert_boundary(prefs, v, e, starting_vert, linked_edges, visited_verts)
                else:
                    dead_end = dead_end_vert_boundary(prefs, v, e, starting_vert, linked_edges, visited_verts, ends)
                if dead_end:  # This might be wrong logic but we need a way to NOT add the edge if it is hidden.
                    visited_verts.add(v)  # but this might leave 1 edge not selected.
                else:
                    visited_verts.add(v)
                    if e not in visited_edges and not e.is_wire:
                        new_edges.append(e)

        if len(new_edges) == 0:
            break
        else:
            cur_edges = new_edges
            if not ends:
                if loop == 1:  # This is a stupid hack but we need to be able to iterate the first vert again
                    visited_verts.discard(starting_vert)
                loop +=1
    return visited_verts


# Takes a vertex and connected wire edge and returns a set of wire verts starting at the vert until reaching a dead end
# Only works on wire loops with 1-2 edges per vertex
# For a bounded selection between two vertices it also requires the two end vertices for dead end validation
def partial_loop_vert_wire(prefs, starting_vert, starting_edge, ends=''):
    cur_vert = starting_vert
    cur_edge = starting_edge
    next_vert = cur_edge.other_vert(cur_vert)
    partial_list = {cur_vert}

    while True:
        partial_list.add(next_vert)
        linked_edges = next_vert.link_edges
        if len(linked_edges) < 2:
            break
        next_edge = [e for e in next_vert.link_edges if e is not cur_edge][0]

        if not ends:
            dead_end = dead_end_vert_wire(prefs, next_vert, next_edge, starting_vert, linked_edges, partial_list)
        else:
            dead_end = dead_end_vert_wire(prefs, next_vert, next_edge, starting_vert, linked_edges, partial_list, ends)

        if dead_end:
            break

        cur_vert = next_vert
        next_vert = next_edge.other_vert(cur_vert)
        cur_edge = next_edge
    return partial_list

# Takes a BMesh loop and its connected starting face and returns a loop of faces until hitting a dead end.
# For a bounded selection between two faces it also requires the two end faces for dead end validation.
def partial_loop_face(prefs, cur_loop, starting_face, reference_list, ends=''):
    partial_list = {starting_face}
    while True:
        # Jump to next loop on the same edge and walk two loops forward (opposite edge)
        next_loop = cur_loop.link_loop_radial_next.link_loop_next.link_loop_next
        next_face = next_loop.face

        # Check to see if next component matches dead end conditions
        if not ends:
            dead_end = dead_end_face(prefs, cur_loop, next_loop, next_face, starting_face, partial_list, reference_list)
        else:
            dead_end = dead_end_face(prefs, cur_loop, next_loop, next_face, starting_face, partial_list, reference_list, ends)

        # Add component to list.
        if next_face not in partial_list:
            if len(next_face.verts) == 4:
                partial_list.add(next_face)
            elif prefs.allow_non_quads_at_ends:
                partial_list.add(next_face)
        reference_list.add(next_face)
        if dead_end:
            break
        # Run this part always
        cur_loop = next_loop
    return partial_list


# Takes a loop and reference edge and returns a set of edges starting at the edge until reaching a dead end.
# For a bounded selection between two edges it also requires the two end edges for dead end validation.
def partial_loop_edge_manifold(prefs, loop, starting_edge, starting_vert, reference_list, ends=''):
    e_step = starting_edge
    pv = starting_vert  # Previous Vert
    cv = starting_edge.other_vert(starting_vert)  # Current Vert
    partial_list = {e_step}

    while True:
        if cv in loop.link_loop_prev.edge.verts:
            loop = loop.link_loop_prev
        elif cv in loop.link_loop_next.edge.verts:
            loop = loop.link_loop_next

        pv = cv
        next_loop = fan_loop_extension(e_step, loop, cv)

        if next_loop:
            e_step = next_loop.edge
            cv = e_step.other_vert(cv)
            loop = next_loop

            # Check to see if next component matches dead end conditions
            if not ends:
                dead_end = dead_end_loop(prefs, e_step, cv, starting_edge, partial_list, reference_list)
            else:
                dead_end = dead_end_loop(prefs, e_step, cv, starting_edge, partial_list, reference_list, ends)

            reference_list.add(pv)
            # Add component to list.
            partial_list.add(e_step)  # It would be better if the dead_end test could break before here
            if dead_end:
                break
        else:  # finite and we've reached an end
            partial_list.add(e_step)
            break
    return partial_list  # Return the completed loop


# Takes a loop and starting edge and returns a set of edges starting at the edge until reaching a dead end.
# For a bounded selection between two edges it also requires the two end edges for dead end validation.
def partial_ring_edge(prefs, starting_loop, starting_edge, reference_list, ends=''):
    cur_loop = starting_loop
    partial_list = {starting_edge}
    while True:
        # Get next components
        next_loop = cur_loop.link_loop_radial_next.link_loop_next.link_loop_next
        if next_loop:
            next_edge = next_loop.edge
            next_face = next_loop.face

            # Check to see if next component matches dead end conditions
            if not ends:
                dead_end = dead_end_ring(prefs, next_edge, next_face, starting_edge, partial_list, reference_list)
            else:
                dead_end = dead_end_ring(prefs, next_edge, next_face, starting_edge, partial_list, reference_list, ends)

            # Add component to list.
            if next_edge not in partial_list:  # Hold up, do we even need to test this? It's a set, so why bother?
                if len(next_face.verts) == 4:
                    if not prefs.ignore_hidden_geometry and not next_face.hide:  # Very un-ideal way to do this
                        partial_list.add(next_edge)  # It would be better if the dead_end test could break before here
                    elif prefs.ignore_hidden_geometry:
                        partial_list.add(next_edge)
                reference_list.add(next_face)
            if dead_end:  # Can't place this BEFORE adding components to lists because it will break bounded selections
                break
        else:  # finite and we've reached an end
            break
        cur_loop = next_loop
    return partial_list  # Return the completed loop


# Takes an edge and connected vertex and returns a set of boundary edges starting at the edge until reaching a dead end
# For a bounded selection between two edges it also requires the two end edges for dead end validation.
def partial_loop_edge_boundary(prefs, starting_edge, starting_vert, ends=''):
    cur_edges = [starting_edge]
    final_selection = set()
    visited_verts = {starting_vert}

    loop = 0
    while True:
        edge_verts = [v for e in cur_edges for v in e.verts if v not in visited_verts]
        new_edges = []
        for v in edge_verts:
            linked_edges = {e for e in v.link_edges if e.is_boundary or e.is_wire}
            for e in linked_edges:
                if not ends:
                    dead_end = dead_end_edge_boundary(prefs, e, v, starting_edge, linked_edges, final_selection)
                else:
                    dead_end = dead_end_edge_boundary(prefs, e, v, starting_edge, linked_edges, final_selection, ends)
                if dead_end:  # This might be wrong logic but I need a way to NOT add the edge if it is hidden.
                    visited_verts.add(v)  # But it prevents the edge from being used in cur_edges
                else:
                    visited_verts.add(v)
                    if e not in final_selection and not e.is_wire:
                        new_edges.append(e)
        final_selection.update(new_edges)

        if len(new_edges) == 0:
            break
        else:
            cur_edges = new_edges
            if loop == 1:  # This is a stupid hack but we need to be able to iterate the first edge again
                visited_verts.discard(starting_vert)
            loop +=1  # Thanks, I hate it.
    return final_selection


# Takes a wire edge and connected vert and returns a set of wire edges starting at the edge until reaching a dead end
# Only works on wire loops with 1-2 edges per vertex
# For a bounded selection between two vertices it also requires the two end vertices for dead end validation
def partial_loop_edge_wire(prefs, starting_edge, starting_vert, ends=''):
    cur_vert = starting_vert
    cur_edge = starting_edge
    next_vert = cur_edge.other_vert(cur_vert)
    partial_list = {cur_edge}

    while True:
        linked_edges = next_vert.link_edges
        if len(linked_edges) < 2:
            break
        next_edge = [e for e in next_vert.link_edges if e is not cur_edge][0]
        if not len(linked_edges) > 2:
            partial_list.add(next_edge)
        if not ends:
            dead_end = dead_end_edge_wire(prefs, next_vert, next_edge, starting_edge, linked_edges, partial_list)
        else:
            dead_end = dead_end_edge_wire(prefs, next_vert, next_edge, starting_edge, linked_edges, partial_list, ends)

        if dead_end:
            break

        cur_vert = next_vert
        next_vert = next_edge.other_vert(cur_vert)
        cur_edge = next_edge
    return partial_list


# ##################### Dead End conditions ##################### #

def dead_end_vert_manifold(prefs, vert, edge, starting_vert, partial_list, reference_list, ends=''):
    if not ends:  # For non-bounded selections.
        # Loop is infinite and we're done
        reached_end = vert == starting_vert
        if reached_end:
            partial_list.add("infinite")  # NOTE: This must be detected and handled/discarded externally.
    else:  # For bounded selections between 2 verts.
        # Looped back on self, or reached other component in a bounded selection
        reached_end = vert == ends[0] or vert == ends[1]
        if reached_end:
            if vert == starting_vert:
                partial_list.add("infinite")  # NOTE: This must be detected and handled/discarded externally.
    # Self-intersecting loop and pref doesn't allow it
    is_intersect = prefs.terminate_self_intersects and vert in reference_list
    # Vertex/edge is hidden and pref to ignore hidden geometry isn't enabled
    is_hidden = not prefs.ignore_hidden_geometry and (vert.hide or edge.hide)
    return reached_end or is_intersect or is_hidden


def dead_end_vert_boundary(prefs, vert, edge, starting_vert, linked_edges, partial_list, ends=''):
    if not ends:  # For non-bounded selections.
        # Loop is infinite and we're done
        reached_end = starting_vert in partial_list and vert == starting_vert
        if reached_end:
            partial_list.add("infinite")  # NOTE: This must be detected and handled/discarded externally.

        # Self-intersecting loop and pref doesn't allow it
        is_intersect = prefs.terminate_self_intersects and len([e for e in linked_edges if e.is_boundary]) > 2
    else:  # For bounded selections between 2 edges.
        # Looped back on self, or reached other component in a bounded selection
        reached_end = starting_vert in partial_list and vert == ends[0] or vert == ends[1]
        if reached_end:
            partial_list.add(vert)  # This is a dumb hack but the upstream function won't work otherwise.
            if starting_vert in partial_list and vert == starting_vert:
                partial_list.add("infinite")  # NOTE: This must be detected and handled/discarded externally.

        # For bounded selections, we always terminate here because it's too complicated to grok otherwise
        is_intersect = len([e for e in linked_edges if e.is_boundary]) > 2

    # Vertex/edge is hidden and pref to ignore hidden geometry isn't enabled
    is_hidden = not prefs.ignore_hidden_geometry and (vert.hide or edge.hide)
    # Vertex on the mesh boundary is connected to a wire edge and pref to ignore wires isn't enabled
    is_wire = not prefs.ignore_boundary_wires and any([e for e in linked_edges if e.is_wire])
    return reached_end or is_intersect or is_hidden or is_wire


def dead_end_vert_wire(prefs, vert, edge, starting_vert, linked_edges, partial_list, ends=''):
    if not ends:  # For non-bounded selections.
        # Loop is infinite and we're done
        reached_end = vert == starting_vert
        if reached_end:
            partial_list.add("infinite")  # NOTE: This must be detected and handled/discarded externally.
    else:  # For bounded selections between 2 edges.
        # Looped back on self, or reached other component in a bounded selection
        reached_end = vert == ends[0] or vert == ends[1]
        if reached_end:
            if vert == starting_vert:
                partial_list.add("infinite")  # NOTE: This must be detected and handled/discarded externally.

    # For wire loops we can't continue if a vertex has more or less than 2 connected edges
    cant_continue = len(linked_edges) != 2
    # Vertex/edge is hidden and pref to ignore hidden geometry isn't enabled
    is_hidden = not prefs.ignore_hidden_geometry and (vert.hide or edge.hide)
    return reached_end or cant_continue or is_hidden


def dead_end_face(prefs, cur_loop, next_loop, next_face, starting_face, partial_list, reference_list, ends=''):
    if not ends:  # For non-bounded selections.
        # Loop is infinite and we're done
        reached_end = next_face == starting_face
        if reached_end:
            partial_list.add("infinite")  # NOTE: This must be detected and handled/discarded externally.
    else:  # For bounded selections between 2 faces.
        # Looped back on self, or reached other component in a bounded selection
        reached_end = next_face == ends[0] or next_face == ends[1]
        if reached_end and next_face == starting_face:
            partial_list.add("infinite")  # NOTE: This must be detected and handled/discarded externally.

    # Self-intersecting loop and pref doesn't allow it
    is_intersect = prefs.terminate_self_intersects and next_face in reference_list
    # Face is hidden and pref to ignore hidden geometry isn't enabled
    is_hidden = not prefs.ignore_hidden_geometry and next_face.hide
    # Triangle or n-gon
    is_non_quad = len(next_face.verts) != 4
    # Non-manifold OR mesh boundary (neither case is manifold)
    is_non_manifold = not cur_loop.edge.is_manifold or not next_loop.edge.is_manifold
    return reached_end or is_intersect or is_hidden or is_non_quad or is_non_manifold


def dead_end_loop(prefs, edge, vert, starting_edge, partial_list, reference_list, ends=''):
    if not ends:  # For non-bounded selections.
        # Loop is infinite and we're done
        reached_end = edge == starting_edge
        if reached_end:
            partial_list.add("infinite")  # NOTE: This must be detected and handled/discarded externally.
    else:  # For bounded selections between 2 edges.
        # Looped back on self, or reached other component in a bounded selection
        reached_end = edge == ends[0] or edge == ends[1]
        if reached_end:
            if edge == starting_edge:
                partial_list.add("infinite")  # NOTE: This must be detected and handled/discarded externally.

    # Self-intersecting loop and pref doesn't allow it
    is_intersect = prefs.terminate_self_intersects and vert in reference_list
    # Vertex/edge is hidden and pref to ignore hidden geometry isn't enabled
    is_hidden = not prefs.ignore_hidden_geometry and (vert.hide or edge.hide)
    return reached_end or is_intersect or is_hidden


def dead_end_ring(prefs, edge, face, starting_edge, partial_list, reference_list, ends=''):
    if not ends:  # For non-bounded selections.
        # Loop is infinite and we're done
        reached_end = edge == starting_edge
        if reached_end:
            partial_list.add("infinite")  # NOTE: This must be detected and handled/discarded externally.
    else:  # For bounded selections between 2 edges.
        # Looped back on self, or reached other component in a bounded selection
        reached_end = edge == ends[0] or edge == ends[1]
        if reached_end:
            if edge == starting_edge:
                partial_list.add("infinite")  # NOTE: This must be detected and handled/discarded externally.

    # Self-intersecting loop and pref doesn't allow it
    is_intersect = prefs.terminate_self_intersects and face in reference_list
    # Face/edge is hidden and pref to ignore hidden geometry isn't enabled
    is_hidden = not prefs.ignore_hidden_geometry and (face.hide or edge.hide)
    # Triangle or n-gon
    is_non_quad = len(face.verts) != 4  # Seems to work fine without this test, actually.
    # Non-manifold OR mesh boundary (neither case is manifold)
    is_non_manifold = not edge.is_manifold

    return reached_end or is_intersect or is_hidden or is_non_quad or is_non_manifold


def dead_end_edge_boundary(prefs, edge, vert, starting_edge, linked_edges, partial_list, ends=''):
    if not ends:  # For non-bounded selections.
        # Loop is infinite and we're done
        reached_end = starting_edge in partial_list and edge == starting_edge
        if reached_end:
            partial_list.add("infinite")  # NOTE: This must be detected and handled/discarded externally.

        # Self-intersecting loop and pref doesn't allow it
        is_intersect = prefs.terminate_self_intersects and len([e for e in linked_edges if e.is_boundary]) > 2
    else:  # For bounded selections between 2 edges.
        # Looped back on self, or reached other component in a bounded selection
        reached_end = starting_edge in partial_list and edge == ends[0] or edge == ends[1]
        if reached_end:
            partial_list.add(edge)  # This is a dumb hack but the upstream function won't work otherwise.
            if starting_edge in partial_list and edge == starting_edge:
                partial_list.add("infinite")  # NOTE: This must be detected and handled/discarded externally.

        # For bounded selections, we always terminate here because it's too complicated to grok otherwise
        is_intersect = len([e for e in linked_edges if e.is_boundary]) > 2

    # Vertex/edge is hidden and pref to ignore hidden geometry isn't enabled
    is_hidden = not prefs.ignore_hidden_geometry and (vert.hide or edge.hide)
    # Vertex on the mesh boundary is connected to a wire edge and pref to ignore wires isn't enabled
    is_wire = not prefs.ignore_boundary_wires and any([e for e in linked_edges if e.is_wire])
    return reached_end or is_intersect or is_hidden or is_wire


def dead_end_edge_wire(prefs, vert, edge, starting_edge, linked_edges, partial_list, ends=''):
    if not ends:  # For non-bounded selections.
        # Loop is infinite and we're done
        reached_end = edge == starting_edge
        if reached_end:
            partial_list.add("infinite")  # NOTE: This must be detected and handled/discarded externally.
    else:  # For bounded selections between 2 edges.
        # Looped back on self, or reached other component in a bounded selection
        reached_end = edge == ends[0] or edge == ends[1]
        if reached_end:
            if edge == starting_edge:
                partial_list.add("infinite")  # NOTE: This must be detected and handled/discarded externally.

    # For wire loops we can't continue if a vertex has more or less than 2 connected edges
    cant_continue = len(linked_edges) != 2
    # Vertex/edge is hidden and pref to ignore hidden geometry isn't enabled
    is_hidden = not prefs.ignore_hidden_geometry and (vert.hide or edge.hide)
    return reached_end or cant_continue or is_hidden


# ##################### Walker Functions ##################### #

def face_extension(loop):  # (THIS ISN'T ACTUALLY BEING USED ANYWHERE.. it's a one-liner)
    # Jump to next loop on the same edge and walk two loops forward (opposite edge)
    next_loop = loop.link_loop_radial_next.link_loop_next.link_loop_next
    return next_loop


# Loop extension converted from Blender's internal functions.
# https://developer.blender.org/diffusion/B/browse/master/source/blender/bmesh/intern/bmesh_query.c$613
# Takes a loop and a reference edge and returns a loop that is opposite of the starting loop, through a vertex.
# The reference edge can be perpendicular to the loop's edge (prev or next loop)
# Or in most cases it should also work if the reference edge is the same as the loop.edge
def BM_vert_step_fan_loop(edge, loop, vert):
    if len(vert.link_loops) != 4:
        return None
    e_prev = edge
    if loop.edge == e_prev:
        e_next = loop.link_loop_prev.edge
    elif loop.link_loop_prev.edge == e_prev:
        e_next = loop.edge
    elif loop.link_loop_next.edge == e_prev:
        e_next = loop.edge
    else:
        print("Context Select BM_vert_step_fan_loop: Unable to find a match.")
        return None

    if e_next.is_manifold:
        return BM_edge_other_loop(e_prev, e_next, loop)
    else:
        print("Context Select BM_vert_step_fan_loop: Nonmanifold edge.")
        return None


# https://developer.blender.org/diffusion/B/browse/master/source/blender/bmesh/intern/bmesh_query.c$572
def BM_edge_other_loop(e_prev, edge, loop):
    if loop.edge == edge:
        l_other = loop
    else:
        l_other = loop.link_loop_prev
    l_other = l_other.link_loop_radial_next

    if l_other.vert == loop.vert:
        if edge.other_vert(l_other.vert) == edge.other_vert(loop.vert):
            l_other = l_other.link_loop_next
            if l_other.vert not in e_prev.verts:
                l_other = l_other.link_loop_prev.link_loop_prev
        else:
            l_other = l_other.link_loop_prev
    elif l_other.link_loop_next.vert == loop.vert:
        if l_other.vert in e_prev.verts:
            l_other = l_other.link_loop_prev
        else:
            l_other = l_other.link_loop_next
    else:
        print("Context Select BM_edge_other_loop: No match, got stuck!")
        return None
    return l_other


def fan_loop_extension(edge, loop, vert):
    next_loop = BM_vert_step_fan_loop(edge, loop, vert)
    if not next_loop:
        loop = loop.link_loop_radial_next
        next_loop = BM_vert_step_fan_loop(edge, loop, vert)
    else:
        return next_loop
    # Can only return None if there's no next loop.
    return None


# Takes an edge + vert and returns the edge in the loop direction through the vert (assumes vert has 4 manifold edges)
def get_opposite_edge(edge, vert):
    edges = [e for e in vert.link_edges]
    faces = [f for f in vert.link_faces]
    a_face = [f for f in faces if edge in f.edges][0]
    step_loop = [l for l in a_face.loops if l.edge in edges and l.edge != edge][0]
    opposite_loop = fan_loop_extension(edge, step_loop, vert)
    if opposite_loop is not None:
        opposite_edge = opposite_loop.edge
        return opposite_edge
    else:
        return None


def register():
    for every_class in classes:
        bpy.utils.register_class(every_class)
    cs_register_keymap_keys()


def unregister():
    for every_class in classes:
        bpy.utils.unregister_class(every_class)
    cs_unregister_keymap_keys()


if __name__ == "__main__":
    register()
