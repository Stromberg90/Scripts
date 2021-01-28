# Blender

## Maya Style Merge Tool
![](https://i.imgur.com/EQ0rLzV.gif)

Usage: Install the mesh_merge_tool.zip and then in Edit mode use the new tool that appears in the left-side Toolbar.  You can right click on the tool icon to set a hotkey for switching to the tool.

![](https://i.imgur.com/EuHTXth.png)

You can also choose to hotkey mesh.merge_tool in the Blender Preferences > Keymap > 3D View > Mesh > Mesh (Global) if you wish to call the operator directly instead of using the tool (NOTE: It is recommended that if you choose to do this then you should enable the "Wait for Input" checkbox when setting up your hotkey.

Click and hold the left mouse button on a vertex or edge and then drag it onto a second vertex or edge and release the mouse button to merge them.  You can control whether to merge at the first or last vertex/edge, or the center between the two, via a dropdown in the Tool Settings bar at the top of the 3D Viewport, OR you can press the 1, 2, 3, A, C, F, or L key while dragging to change the merge location on the fly before you release the mouse button.
- 1, A, or F will merge at the First component.
- 2 or C will merge at the Center between the two.
- 3 or L will merge at the Last component.

In vertex mode, if there is a starting selection and the tool is invoked on one if those vertices, then all vertices in the selection will be merged at the desired location.

![](https://i.imgur.com/4SySLU5.gif)

Multi-merge, line and point size, and colors can be controlled from the add-on preferences.
![](https://i.imgur.com/hIgc9ly.png)

## Context Select (Emulates Maya's selections)
![](https://i.imgur.com/FwF4o0r.gif)

![](https://i.imgur.com/bpaMJWL.png)
Usage: object.context_select is automatically added to Blender's keymap when the add-on is installed (this can be disabled from the add-on's preferences after being installed).  
Key entries are located in Blender Preferences > Keymap > 3D View > Mesh > Mesh (Global)  
Default keys are double-click to set a new selection and shift + double-click to extend a selection.

- Selection works for all 3 component types (vertices, edges, faces).  
- The script selects full loops of vertices, edges, or faces, and also full rings of edges.  (With several preferences to modify selection behavior.)
- It can also create bounded selections between two components (e.g. similar to Blender's Select Shortest Path but constrained to a loop or ring only).  Single-click (or shift + single-click) the first component, then shift + double-click the second component within the same loop or ring to create the bounded selection.  
- All of the above functionality works on manifold quad topology for all 3 component types, it also works on the boundary of an open mesh for vertices and edges, and it also works on single wire loops (e.g. like the Circle primitive type) for vertices and edges.  

LIMITATIONS: 
- At this time the add-on can only create or add to a selection; it cannot subtract from a selection (full loop or bounded deselection).  
- The add-on has not been tested in the UV viewport, only in the 3D viewport, so it may not work there.

## Edges To Curve
![](https://i.imgur.com/u2tHwLL.gif)

Usage: Select edge(s) then search for Edges To Curve in the spacebar menu, or the Edges menu in the top of the viewport, or the Context menu, or hotkey object.edge_to_curve  
Left Mouse confirms, Right Mouse cancels, Mouse Wheel increases or decreases resolution.

## Duplicate Along Curve
![](https://i.imgur.com/8kERwFF.gif)

Usage: Select one curve and one object, then search for Duplicate Along Curve in the spacebar menu or hotkey object.duplicate_along_curve
