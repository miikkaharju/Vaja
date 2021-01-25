#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from solid import *

from constraint_system import *

woods = {
        "100x100": {"width": 100, "thickness": 100, "max_length": 6000},
        "100x50": {"width": 100, "thickness": 50, "max_length": 6000},
        "50x50": {"width": 50, "thickness": 50, "max_length": 6000},
        "100x25": {"width": 100, "thickness": 25, "max_length": 6000},
        "100x20": {"width": 100, "thickness": 20, "max_length": 6000},
        "100x22": {"width": 100, "thickness": 22, "max_length": 6000},
        "148x48": {"width": 148, "thickness": 48, "max_length": 6000}
        }

class WoodBlock(ConstrainedBlock):
    def __init__(self, system):
        super().__init__(system)
        self.visible = True
        system.add(self)

    def get_openscad(self):
        length_x = self.get_computed_length(Dimension.X)
        length_y = self.get_computed_length(Dimension.Y)
        length_z = self.get_computed_length(Dimension.Z)
        translation_x = self.get_position(Dimension.X)
        translation_y = self.get_position(Dimension.Y)
        translation_z = self.get_position(Dimension.Z)

        new_cube = cube([length_x, length_y, length_z])
        new_cube = translate([translation_x, translation_y, translation_z])(new_cube)
        return new_cube

    def make_hole(self, hole_block):
        pass

    def set_length(self, length):
        self.bind_internally(self.length_dimension, length)

class WoodSystem(ConstraintSystem):
    def get_wood(self, name, length_dimension, width_dimension, visible=True):
        new_block = WoodBlock(self)
        new_block.visible = visible
        new_block.length_dimension = length_dimension
        thickness_dimension = next((d for d in Dimension
            if d is not length_dimension and d is not width_dimension))
        new_block.bind_internally(thickness_dimension, woods[name]["thickness"])
        new_block.bind_internally(width_dimension, woods[name]["width"])
        return new_block

    def get_material_width(self, name):
        return woods[name]["width"]

    def get_material_thickness(self, name):
        return woods[name]["thickness"]

    def create_openscad(self):
        openscad_object = union()()
        for block in self.blocks:
            if not block.visible:
                continue
            openscad_object += block.get_openscad()

        scad_render_to_file(openscad_object, 'verstas.scad')
