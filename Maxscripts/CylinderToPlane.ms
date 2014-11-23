rollout CTPlane "Cylinder To Plane"
(
--Define Interface
		checkbox _Del "Delete Source" triState:0
		checkbox _Half "Half Cylinder" triState:0
		button _Gen "Generate Plane"
	
		on _Gen pressed do
		(		
			if _Half.state == false then (
				"Info collected from selected cylinder"
				Height = $.height
				HeightSegs = $.heightsegs
				Sides = $.sides
				Radius = $.radius
				Radius = ((Radius * 3.14) * 2)
				selection[1].pivot = selection[1].center
				Pos = $.pos
				if _Del.state == True then (delete $)
				
				"Plane is created"
				Plane length:Radius width:Height lengthsegs:Sides Widthsegs:HeightSegs isSelected:on
				addmodifier $ (bend BendAngle:360 BendDir:-90 BendAxis:1)	
				selection[1].pivot = selection[1].center
				$.pos = Pos
				)
			if _Half.state == True then (
				"Info collected from selected cylinder"
				Height = $.height
				HeightSegs = $.heightsegs
				Sides = ($.sides / 2)
				Radius = $.radius
				Radius = (Radius * 3.14)
				selection[1].pivot = selection[1].center
				Pos = $.pos
				if _Del.state == True then (delete $)
				
				"Plane is created"
				Plane length:Radius width:Height lengthsegs:Sides Widthsegs:HeightSegs isSelected:on
				addmodifier $ (bend BendAngle:180 BendDir:-90 BendAxis:1)	
				selection[1].pivot = selection[1].center
				$.pos = Pos
				)
		)
)
createdialog CTPlane