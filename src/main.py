# %%
from build123d import *
from global_params import *
from scipy import optimize

# Parameters
height = wall_min * 4
decor = height / 2
hole_diameter = 2
hole_corner_to_center = 2 * hole_diameter
decor_offset = 4 * wall
decor_width = decor_offset / 2
decor_hole = 3 * decor_offset

# Extract the two wires from the source drawing
part = import_svg('drawing.svg')
wire_small = part.wires().sort_by(SortBy.LENGTH)[0]
wire_big = part.wires().sort_by(SortBy.LENGTH)[-1]

# Align the wires and move them to the origin
# - Move to shared vertex
shared_vertex = wire_small.vertices().sort_by(Axis.Y)[0]
shared_vertex_2 = wire_big.vertices().sort_by(Axis.Y)[0]
print(shared_vertex, shared_vertex_2)
assert (shared_vertex.center() - shared_vertex_2.center()).length < 10 * tol
wire_big.move(Location(shared_vertex.center() - shared_vertex_2.center()))
shared_vertex_2 = wire_big.vertices().sort_by(Axis.Y)[0]
assert (shared_vertex.center() - shared_vertex_2.center()).length < eps
del shared_vertex_2
# - Rotate along shared vertex to align vertical center
left_small = wire_small.vertices().sort_by(Axis.X)[0]
left_big = wire_big.vertices().sort_by(Axis.X)[0]
print(left_small.center(), left_big.center())
assert abs((left_small.center() - left_big.center()).X) < 10 * tol
rotate_around = Axis(shared_vertex.center(), (0, 0, 1))


def to_optimize(x: float) -> float:
    wire_big_2 = wire_big.rotate(rotate_around, x)
    left_big = wire_big_2.vertices().sort_by(Axis.X)[0]
    return abs((left_small.center() - left_big.center()).X)


opt_angle = optimize.newton(to_optimize, 0)
print(opt_angle)
wire_big = wire_big.rotate(rotate_around, opt_angle)
left_big = wire_big.vertices().sort_by(Axis.X)[0]
assert abs((left_small.center() - left_big.center()).X) < tol
del left_big
# - Finally, move them to the origin for mirroring
move_both_by = Location((-left_small.center().X, -shared_vertex.center().Y, 0))
wire_small.move(move_both_by)
wire_big.move(move_both_by)
del left_small, shared_vertex, move_both_by

# Now the easy part, mirror the wires to build faces as needed
with BuildSketch() as sketch_part1:
    second_half = wire_big.mirror(Plane.YZ)
    closing_wire = Wire.make_wire([
        Edge.make_line(wire_big.vertices().sort_by(Axis.Y)[0],
                       second_half.vertices().sort_by(Axis.Y)[0])])
    face = Face.make_from_wires(Wire.make_wire(
        sum([wire_big.edges(), second_half.edges(), closing_wire.edges()], ShapeList())))
    add(face.mirror(Plane.XZ))

with BuildSketch() as sketch_part3:
    add(sketch_part1)
    add(sketch_part1.sketch.mirror(Plane.XZ))

with BuildSketch() as sketch_part2:
    second_half = wire_small.mirror(Plane.YZ)
    closing_wire = Wire.make_wire([
        Edge.make_line(wire_small.vertices().sort_by(Axis.Y)[0],
                       second_half.vertices().sort_by(Axis.Y)[0])])
    add(Face.make_from_wires(Wire.make_wire(
        sum([wire_small.edges(), second_half.edges(), closing_wire.edges()], ShapeList()))))
    add(sketch_part1.sketch)

# Finally, extrude into 3D objects, mark the top face and add center holes
ref1 = sketch_part1.vertices().sort_by(Axis.Y)[0].vertex().center()
ref2 = sketch_part2.vertices().sort_by(Axis.Y)[-1].vertex().center()
ref3 = extrude(sketch_part3.faces(), amount=2).find_intersection(Axis(ref2 + (0, 0, 1), (1, 0, 0)))[0][0]
print(ref3)
holes_pos = [
    (0, ref1.Y + hole_corner_to_center),
    (0, -ref1.Y - hole_corner_to_center),
    (ref3.X + hole_corner_to_center, ref2.Y),
    (-ref3.X - hole_corner_to_center, ref2.Y),
]
sketches = [sketch_part1.sketch, sketch_part2.sketch, sketch_part3.sketch]
parts = []
for i, sketch in enumerate(sketches):
    with BuildPart() as tmp_part:
        # - Basic extrusion
        add(sketch.face())
        extrude(amount=height)
        face = tmp_part.part.faces().sort_by(Axis.Z)[-1]
        # - Holes
        with BuildSketch(Plane.XY.offset(face.center().Z)) as sketch:
            for hole_pos in holes_pos:
                with Locations(Location(hole_pos)):
                    Circle(hole_diameter / 2, height)
        extrude(amount=-height, mode=Mode.SUBTRACT)
        chamfer(edges(Select.LAST), length=height/4, length2=height/2 - eps)
        # - Text
        with BuildSketch(Plane(face.center_location).rotated((0, 0, 180))) as sketch:
            Text("{}".format(i + 1), 32, font_path="/usr/share/fonts/TTF/OpenSans-Regular.ttf")
        extrude(amount=-decor, mode=Mode.SUBTRACT)
        # - Hex grid decoration / material saving
        face_outer_filter = offset(face, amount=-decor_offset, mode=Mode.PRIVATE)
        face_cut = face - faces().sort_by(Axis.Z)[-1]
        face_inner_filter_sub = offset(face_cut, amount=decor_offset, mode=Mode.PRIVATE)
        face_filter = face_outer_filter.face()
        for tmp_face in face_inner_filter_sub.faces():
            face_filter -= tmp_face.face()
            face_filter = face_filter.face()
        with BuildSketch() as sketch:
            with HexLocations((decor_hole + decor_width) / 2, 6, 9):
                RegularPolygon(decor_hole / 2, 6, major_radius=False)
            add(face_filter.move(Location((0, 0, -face_filter.center().Z))), mode=Mode.INTERSECT)
        extrude(amount=height, mode=Mode.SUBTRACT)

    parts.append(tmp_part.part)

# Assemble the parts into a single compound with nice offsets
sizes_x = [part.bounding_box().size.X + 5 for part in parts]
offset_x = - sum(sizes_x) / 2
for part in parts:
    part.move(Location((offset_x, 0, 0)))
    offset_x += part.bounding_box().size.X + 5
obj = Compound.make_compound(parts)

if __name__ == "__main__":
    if 'show_object' in globals():  # Needed for CI / cq-editor
        show_object(obj)  # type: ignore
    else:
        show_or_export(obj)
        # show_all()()
