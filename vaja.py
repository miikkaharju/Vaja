#!/usr/bin/python3
# -*- coding: utf-8 -*-

import math

from constraint_system import *
from woods import *

lazys = []

def repeating(
        system, start_normal, stop_normal, end_normal_0, end_normal_1,
        surface_normal, material_name, difference, laid_flat,
        start_offset=0, visible=True):
    material_width = system.get_material_width(material_name)\
            if laid_flat else system.get_material_thickness(material_name)
    material_thickness = system.get_material_thickness(material_name)\
            if laid_flat else system.get_material_width(material_name)

    def repeating_closure():
        signed_distance = start_normal.face.get_distance(stop_normal.face)
        if isinstance(signed_distance, DistanceConstraint):
            if signed_distance.equality == Equality.EQ:
                distance = abs(signed_distance.value)
            else:
                raise DistanceNotConstrainedException
        else:
            distance = abs(signed_distance)
        sign = 1 if start_normal.is_positive else -1

        offset = start_offset
        top_offset = 0
        while offset + material_width <= distance:
            if laid_flat:
                new_block = system.get_wood(
                        material_name,
                        end_normal_0.dimension,
                        start_normal.dimension,
                        visible)
            else:
                new_block = system.get_wood(
                        material_name,
                        end_normal_0.dimension,
                        surface_normal.dimension,
                        visible)
            start_normal.bind(new_block, sign*offset)
            surface_normal.bind(new_block)
            end_normal_0.bind(new_block)
            end_normal_1.bind(new_block)
            top_offset = offset + material_width
            offset += difference

        if laid_flat:
            new_block = system.get_wood(
                    material_name,
                    end_normal_0.dimension,
                    start_normal.dimension,
                    visible)
        else:
            new_block = system.get_wood(
                    material_name,
                    end_normal_0.dimension,
                    surface_normal.dimension,
                    visible)
        surface_normal.bind(new_block)
        end_normal_0.bind(new_block)
        end_normal_1.bind(new_block)
        if distance - top_offset < material_width:
            new_block.unbind_internally(start_normal.dimension)
            start_normal.bind(new_block, sign*top_offset)
            stop_normal.bind(new_block)
        else:
            stop_normal.bind(new_block)

    try:
        repeating_closure()
    except DistanceNotConstrainedException:
        lazys.append(repeating_closure)

    outer_surface_normal = surface_normal.offset_copy(material_thickness)
    the_union = ConstrainedBlock.from_normals(
            system,
            surface_normal.flipped(),
            outer_surface_normal,
            start_normal.flipped(),
            stop_normal.flipped(),
            end_normal_0.flipped(),
            end_normal_1.flipped())
    return the_union

def board_on_board(
        system, start_normal, stop_normal,
        end_normal_0, end_normal_1, surface_normal):
    offset_surface_normal = surface_normal.offset_copy(44)
    inner = repeating(
        system, start_normal, stop_normal, end_normal_0, end_normal_1,
        offset_surface_normal, "100x22", system.get_material_width("100x22")*1.5,
        True, visible=False)
    outer = repeating(
        system, start_normal, stop_normal, end_normal_0, end_normal_1,
        inner.get_outer(offset_surface_normal),
        "100x22", system.get_material_width("100x22")*1.5,
        True, system.get_material_width("100x22")*0.75, visible=False)
    return inner + outer, inner

def bottom_beams(system, x_width, y_width):
    beams = [system.get_wood("100x100", Dimension.X, Dimension.Z) for i in range(3)]
    for i, beam in enumerate(beams):
        beam.name = "beam " + str(i)

    beams[0].get_low_face(Dimension.X).bind(
            beams[1].get_low_face(Dimension.X))
    beams[0].get_low_face(Dimension.X).bind(
            beams[2].get_low_face(Dimension.X))
    beams[0].get_high_face(Dimension.X).bind(
            beams[1].get_high_face(Dimension.X))
    beams[0].get_high_face(Dimension.X).bind(
            beams[2].get_high_face(Dimension.X))

    beams[0].get_high_face(Dimension.Y).bind(
            beams[2].get_low_face(Dimension.Y), offset=DistanceConstraint(">", 0))
    #beams[1].get_high_face(Dimension.Y).bind(
    #        beams[2].get_low_face(Dimension.Y), offset=DistanceConstraint(">", 0))

    beams[0].get_low_face(Dimension.Z).bind(
            beams[1].get_low_face(Dimension.Z))
    beams[0].get_low_face(Dimension.Z).bind(
            beams[2].get_low_face(Dimension.Z))

    the_union = beams[0] + beams[2]

    lazy_closure = beams[1].lazy_bind_centered(the_union, Dimension.Y)
    if not lazy_closure is None:
        lazys.append(lazy_closure)

    return the_union, beams

def floor_support(system, bottom, x0, x1, y0, y1):
    return repeating(system, x0, x1, y0, y1, bottom, "100x50", 600, False)

def california_corner(
        system, bottom_normal, top_normal, connecting_normal, outside_normal):
    outer = system.get_wood(
            "100x50", Dimension.Z, connecting_normal.dimension)
    inner = system.get_wood(
            "100x50", Dimension.Z, outside_normal.dimension)
    bottom_normal.bind(outer)
    bottom_normal.bind(inner)
    top_normal.bind(outer)
    top_normal.bind(inner)
    if outside_normal.is_positive:
        outside_normal.bind(outer)
        outer.bind(inner, outside_normal.dimension)
    else:
        outside_normal.bind(outer)
        inner.bind(outer, outside_normal.dimension)
    if connecting_normal.is_positive:
        connecting_normal.bind(outer)
        connecting_normal.bind(inner)
    else:
        connecting_normal.bind(outer)
        connecting_normal.bind(inner)
    return outer + inner, outer, inner

def wall_frame_w_corners(
        system, height, bottom_normal, floor_normal,
        outside_normal, neg_end, pos_end):
    bottom = system.get_wood(
            "100x50", neg_end.dimension, outside_normal.dimension)
    top = system.get_wood(
            "100x50", neg_end.dimension, outside_normal.dimension)
    bottom_normal.bind(bottom)
    bottom_normal.bind(top, offset=DistanceConstraint(">", 0))
    floor_normal.bind(top, offset=height)
    outside_normal.bind(bottom)
    outside_normal.bind(top)
    neg_end.bind(bottom)
    neg_end.bind(top)
    pos_end.bind(bottom)
    pos_end.bind(top)
    neg_corner, neg_outer, neg_inner = california_corner(
            system,
            bottom.get_high_normal(Dimension.Z), top.get_low_normal(Dimension.Z),
            bottom.get_inner(outside_normal.flipped()), neg_end
            )
    pos_corner, pos_outer, pos_inner = california_corner(
            system,
            bottom.get_high_normal(Dimension.Z), top.get_low_normal(Dimension.Z),
            bottom.get_inner(outside_normal.flipped()), pos_end
            )

    repeating(
        system,
        neg_outer.get_low_normal(neg_end.dimension).flipped(),
        pos_outer.get_high_normal(pos_end.dimension).flipped(),
        bottom.get_high_normal(Dimension.Z),
        top.get_low_normal(Dimension.Z),
        outside_normal,
        "100x50",
        600,
        False)

    return bottom + top

def wall_frame(
        system, height, bottom_normal, floor_normal,
        outside_normal, neg_end, pos_end):
    top = system.get_wood(
            "100x50", neg_end.dimension, outside_normal.dimension)
    floor_normal.bind(top, offset=height)
    outside_normal.bind(top)
    neg_end.bind(top)
    pos_end.bind(top)

    ribs = repeating(
        system,
        neg_end,
        pos_end,
        bottom_normal,
        top.get_low_normal(Dimension.Z),
        outside_normal,
        "100x50",
        600,
        False)
    return ribs + top

def door(system, width_dimension):
    thickness_dimension = next((d for d in Dimension
        if d is not Dimension.Z and d is not width_dimension))

    the_door = WoodBlock(system)
    the_door.bind_internally(Dimension.Z, 2050)
    the_door.bind_internally(width_dimension, 830)
    the_door.bind_internally(thickness_dimension, 100)

    the_extension = WoodBlock(system)
    the_extension.bind_internally(Dimension.Z, 2050)
    the_extension.bind_internally(width_dimension, 300)
    the_extension.bind_internally(thickness_dimension, 100)

    left_frame = WoodBlock(system)
    left_frame.bind_internally(thickness_dimension, 120)
    left_frame.bind_internally(width_dimension, 30)

    right_frame = WoodBlock(system)
    right_frame.bind_internally(thickness_dimension, 120)
    right_frame.bind_internally(width_dimension, 30)

    top_frame = WoodBlock(system)
    top_frame.bind_internally(thickness_dimension, 120)
    top_frame.bind_internally(Dimension.Z, 30)

    bottom_frame = WoodBlock(system)
    bottom_frame.bind_internally(thickness_dimension, 120)
    bottom_frame.bind_internally(Dimension.Z, 30)

    left_frame.get_high_normal(Dimension.Z).flipped().bind(top_frame)
    right_frame.get_high_normal(Dimension.Z).flipped().bind(top_frame)
    left_frame.get_low_normal(Dimension.Z).flipped().bind(bottom_frame)
    right_frame.get_low_normal(Dimension.Z).flipped().bind(bottom_frame)

    bottom_frame.get_high_normal(width_dimension).flipped().bind(right_frame)
    top_frame.get_high_normal(width_dimension).flipped().bind(right_frame)
    bottom_frame.get_low_normal(width_dimension).flipped().bind(left_frame)
    top_frame.get_low_normal(width_dimension).flipped().bind(left_frame)

    the_door.get_low_normal(width_dimension).bind(the_extension)
    the_door.get_low_normal(thickness_dimension).flipped().bind(the_extension)
    the_door.get_low_normal(Dimension.Z).flipped().bind(the_extension)

    door_and_extension = the_door + the_extension

    door_and_extension.get_high_normal(Dimension.Z).bind(top_frame)
    door_and_extension.get_low_normal(Dimension.Z).bind(bottom_frame)
    door_and_extension.get_high_normal(width_dimension).bind(right_frame)
    door_and_extension.get_low_normal(width_dimension).bind(left_frame)

    frame_offset = -20
    door_and_extension.get_low_normal(thickness_dimension).flipped()\
            .bind(top_frame, offset=frame_offset)
    door_and_extension.get_low_normal(thickness_dimension).flipped()\
            .bind(bottom_frame, offset=frame_offset)
    door_and_extension.get_low_normal(thickness_dimension).flipped()\
            .bind(left_frame, offset=frame_offset)
    door_and_extension.get_low_normal(thickness_dimension).flipped()\
            .bind(right_frame, offset=frame_offset)

    frame = top_frame + bottom_frame + left_frame + right_frame

    return door_and_extension + frame


def pillars(system, beam):
    pillars = [WoodBlock(system) for i in range(3)]

    for pillar in pillars:
        pillar.bind_internally(Dimension.X, 240)
        pillar.bind_internally(Dimension.Y, 240)
        pillar.bind_internally(Dimension.Z, 190)

        lazy_closure = beam.lazy_bind_centered(pillar, Dimension.Y)
        if not lazy_closure is None:
            lazys.append(lazy_closure)
        beam.get_low_normal(Dimension.Z).bind(
                pillar.get_high_normal(Dimension.Z))

    lazy_closure = beam.lazy_bind_centered(pillars[1], Dimension.X)
    if not lazy_closure is None:
        lazys.append(lazy_closure)

    pillars[0].get_low_face(Dimension.X).bind(
            beam.get_low_face(Dimension.X))
    pillars[2].get_high_face(Dimension.X).bind(
            beam.get_high_face(Dimension.X))

    return pillars

def wall_frame_w_door(
        system, height, bottom_normal, floor_normal,
        outside_normal, neg_end, pos_end):
    top = system.get_wood(
            "100x50", neg_end.dimension, outside_normal.dimension)
    floor_normal.bind(top, offset=height)
    outside_normal.bind(top)
    neg_end.bind(top)
    pos_end.bind(top)

    first = system.get_wood(
            "100x50", bottom_normal.dimension, outside_normal.dimension)
    bottom_normal.bind(first)
    pos_end.bind(first)
    outside_normal.bind(first)
    top.get_low_normal(Dimension.Z).bind(first)

    second = system.get_wood(
            "100x50", bottom_normal.dimension, outside_normal.dimension)
    bottom_normal.bind(second)
    second.get_high_normal(Dimension.X)\
            .bind(first.get_high_normal(Dimension.X), offset=600)
    outside_normal.bind(second)
    top.get_low_normal(Dimension.Z).bind(second)

    the_door = door(system, neg_end.dimension)
    second.get_low_normal(pos_end.dimension).bind(the_door)
    floor_normal.bind(the_door)
    outside_normal.bind(the_door)

    ribs = repeating(
        system,
        the_door.get_low_normal(Dimension.X),
        neg_end,
        bottom_normal,
        top.get_low_normal(Dimension.Z),
        outside_normal,
        "100x50",
        600,
        False)
    return top + ribs

def main():
    verstas = WoodSystem()

    beams, beam_blocks = bottom_beams(verstas, 3000, 3000)

    origo = verstas.origo
    origo.bind(beams, Dimension.X)
    origo.bind(beams, Dimension.Y)
    origo.bind(beams, Dimension.Z)

    floor_normal = Normal(Face(Dimension.Z), True)

    wall_height = 2700

    wall_frame_left = wall_frame_w_corners(
            verstas,
            wall_height,
            beams.get_high_normal(Dimension.Z),
            floor_normal,
            beams.get_low_normal(Dimension.X).flipped(),
            beams.get_low_normal(Dimension.Y).flipped(),
            beams.get_high_normal(Dimension.Y).flipped())

    wall_frame_right = wall_frame_w_corners(
            verstas,
            wall_height,
            beams.get_high_normal(Dimension.Z),
            floor_normal,
            beams.get_high_normal(Dimension.X).flipped(),
            beams.get_low_normal(Dimension.Y).flipped(),
            beams.get_high_normal(Dimension.Y).flipped())

    wall_frame_front = wall_frame_w_door(
            verstas,
            wall_height,
            beams.get_high_normal(Dimension.Z),
            floor_normal,
            beams.get_low_normal(Dimension.Y).flipped(),
            wall_frame_left.get_high_normal(Dimension.X),
            wall_frame_right.get_low_normal(Dimension.X))

    wall_frame_back = wall_frame(
            verstas,
            wall_height,
            beams.get_high_normal(Dimension.Z),
            floor_normal,
            beams.get_high_normal(Dimension.Y).flipped(),
            wall_frame_right.get_low_normal(Dimension.X),
            wall_frame_left.get_high_normal(Dimension.X))

    b_frame = floor_support(
            verstas,
            beams.get_high_normal(Dimension.Z),
            wall_frame_left.get_high_normal(Dimension.X),
            wall_frame_right.get_low_normal(Dimension.X),
            beams.get_low_normal(Dimension.Y).flipped(),
            beams.get_high_normal(Dimension.Y).flipped())
    b_frame.get_high_normal(Dimension.Z).bind(floor_normal)

    #wall_frame_front.get_low_face(Dimension.Y).bind(
    #        wall_frame_back.get_high_face(Dimension.Y), offset=3000)
    wall_frame_left.get_low_face(Dimension.X).bind(
            wall_frame_right.get_high_face(Dimension.X), offset=3000)

    front_cladding_inner_normal = Normal(Face(Dimension.Y), True)
    back_cladding_inner_normal = Normal(Face(Dimension.Y), False)

    cladding_right, cladding_right_inner = board_on_board(
            verstas,
            front_cladding_inner_normal,
            back_cladding_inner_normal,
            wall_frame_right.get_low_normal(Dimension.Z).flipped(),
            wall_frame_right.get_high_normal(Dimension.Z).flipped(),
            wall_frame_right.get_high_normal(Dimension.X))

    cladding_left, cladding_left_inner = board_on_board(
            verstas,
            front_cladding_inner_normal,
            back_cladding_inner_normal,
            wall_frame_left.get_low_normal(Dimension.Z).flipped(),
            wall_frame_left.get_high_normal(Dimension.Z).flipped(),
            wall_frame_left.get_low_normal(Dimension.X))

    cladding_front, cladding_front_inner = board_on_board(
            verstas,
            cladding_left_inner.get_low_normal(Dimension.X).flipped(),
            cladding_right_inner.get_high_normal(Dimension.X).flipped(),
            wall_frame_front.get_low_normal(Dimension.Z).flipped(),
            wall_frame_front.get_high_normal(Dimension.Z).flipped(),
            wall_frame_front.get_low_normal(Dimension.Y))

    cladding_back, cladding_back_inner = board_on_board(
            verstas,
            cladding_left_inner.get_low_normal(Dimension.X).flipped(),
            cladding_right_inner.get_high_normal(Dimension.X).flipped(),
            wall_frame_back.get_low_normal(Dimension.Z).flipped(),
            wall_frame_back.get_high_normal(Dimension.Z).flipped(),
            wall_frame_back.get_high_normal(Dimension.Y))

    front_cladding_inner_normal.bind(cladding_front_inner.get_high_normal(Dimension.Y))
    back_cladding_inner_normal.bind(cladding_back_inner.get_low_normal(Dimension.Y))
    #front_cladding_inner_normal.bind(back_cladding_inner_normal, 3000)

    cladding_left.get_low_face(Dimension.X).bind(
            cladding_right.get_high_face(Dimension.X), math.sqrt(10000000))
    cladding_front.get_low_face(Dimension.Y).bind(
            cladding_back.get_high_face(Dimension.Y), math.sqrt(10000000))

    pillars(verstas, beam_blocks[0])
    pillars(verstas, beam_blocks[1])
    pillars(verstas, beam_blocks[2])

    for i, lazy in enumerate(lazys):
        try:
            lazy()
        except:
            debug()
    verstas.solve()
    verstas.create_openscad()

if __name__ == "__main__":
    main()
