"""Helper utilities."""
import bpy
import bmesh
from mathutils import Vector


def find_center(source):
    """Assumes that the input is an Edge or an ordered object holding vertices or Vectors"""
    coords = []
    if isinstance(source, bmesh.types.BMEdge):
        coords = [source.verts[0].co, source.verts[1].co]
    elif isinstance(source[0], bmesh.types.BMVert):
        coords = [v.co for v in source]
    elif isinstance(source[0], Vector):
        coords = [v for v in source]

    offset = Vector((0.0, 0.0, 0.0))
    for v in coords:
        offset = offset + v
    return offset / len(coords)


def set_component(self, mode):
    selected_comp = None
    selected_comp = self.bm.select_history.active

    if selected_comp:
        if mode == 'START':
            self.start_comp = selected_comp  # Set the start component
            if self.sel_mode == 'VERT':
                self.start_comp_transformed = self.world_matrix @ self.start_comp.co
            elif self.sel_mode == 'EDGE':
                self.start_comp_transformed = self.world_matrix @ find_center(self.start_comp)
        if mode == 'END':
            self.end_comp = selected_comp  # Set the end component
            if self.sel_mode == 'VERT':
                self.end_comp_transformed = self.world_matrix @ self.end_comp.co
            elif self.sel_mode == 'EDGE':
                self.end_comp_transformed = self.world_matrix @ find_center(self.end_comp)

def merge_uv_points(self, vertices, target):
    if bpy.app.version[0] >= 5 and bpy.app.version[1] >= 2:
    # Keyword was changed in Blender 5.2
        bmesh.ops.pointmerge_facedata(self.bm, verts=vertices, vert_target=target)
    else:
        bmesh.ops.pointmerge_facedata(self.bm, verts=vertices, vert_snap=target)
