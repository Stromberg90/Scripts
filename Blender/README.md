# Blender

### Maya Style Merge Tool
![](https://i.imgur.com/aTZDOdp.gif)

Usage: Search for Merge Tool in the spacebar menu or hotkey object.merge_tool

### Context Select (Emulates Maya's selections)
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

### Edges To Curve
![](https://i.imgur.com/u2tHwLL.gif)

Usage: Select edge(s) then search for Edges To Curve in the spacebar menu, or the Edges menu in the top of the viewport, or the Context menu, or hotkey object.edge_to_curve  
Left Mouse confirms, Right Mouse cancels, Mouse Wheel increases or decreases resolution.

### Duplicate Along Curve
![](https://i.imgur.com/8kERwFF.gif)

Usage: Select one curve and one object, then search for Duplicate Along Curve in the spacebar menu or hotkey object.duplicate_along_curve
