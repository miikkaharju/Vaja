#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import pdb
import traceback

from enum import Enum, auto

def debug():
    tyoe, value, tb = sys.exc_info()
    traceback.print_exc()
    pdb.post_mortem(tb)

class Dimension(Enum):
    X = auto()
    Y = auto()
    Z = auto()

class FaceSign(Enum):
    minus = 0
    plus = 1

class Equality(Enum):
    LT = auto()
    GT = auto()
    EQ = auto()

class DistanceNotConstrainedException(Exception):
    pass

class DistanceConstraint:
    def __init__(self, operand, value):
        self.value = value
        if operand == ">" or operand == Equality.GT:
            self.equality = Equality.GT
        elif operand == "=" or operand == Equality.EQ:
            self.equality = Equality.EQ
        elif operand == "<" or operand == Equality.LT:
            self.equality = Equality.LT
        else:
            raise RuntimeError("Operation not recognized.")

    def __gt__(self, other):
        if self.equality == Equality.GT:
            return self.value >= other
        if self.equality == Equality.EQ:
            return self.value == other
        if self.equality == Equality.LT:
            if self.value > other:
                raise ValueError("Result undefined.")
            return False

    def __neg__(self):
        if self.equality == Equality.LT:
            new_op = Equality.GT
        elif self.equality == Equality.GT:
            new_op = Equality.LT
        return DistanceConstraint(new_op, -self.value)

    def __add__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            return DistanceConstraint(self.equality, self.value + other)
        if isinstance(other, DistanceConstraint):
            if (self.equality == Equality.GT or other.equality == Equality.GT):
                if not (self.equality == Equality.LT
                        or other.equality == Equality.LT):
                    return DistanceConstraint(
                            Equality.GT, self.value + other.value)
                else:
                    raise ValueError
            if (self.equality == Equality.LT or other.equality == Equality.LT):
                if not (self.equality == Equality.GT
                        or other.equality == Equality.GT):
                    return DistanceConstraint(
                            Equality.LT, self.value + other.value)
                else:
                    raise ValueError
            elif self.equality == Equality.EQ and other.equality == Equality.EQ:
                return DistanceConstraint(
                        Equality.EQ, self.value + other.value)

        else:
            pdb.set_trace()
            raise NotImplementedError

    def __radd__(self, other):
        return DistanceConstraint.__add__(self, other)

class ConstraintSystem:
    def __init__(self):
        self.blocks = []

        self.origo = ConstrainedBlock(self)
        for face in (f for f_pair in self.origo.faces.values() for f in f_pair):
            face.s = 0

    def add(self, block):
        self.blocks.append(block)

    def make_hole(self, hole_block, target_blocks=[]):
        if not target_blocks:
            target_blocks = self.blocks
        for t_block in target_blocks:
            if hole_block.intersects(t_block):
                t_block.make_hole(hole_block)

    def solve(self):
        for dimension in Dimension:
            self.solve_dimension(dimension)

    def solve_dimension(self, dimension: Dimension):
        leave_faces = [
                self.origo.faces[dimension][0],
                self.origo.faces[dimension][1]]
        while leave_faces:
            new_leave_faces = []
            for old_face in leave_faces:
                for neighbor_face, offset in old_face.neighbors:
                    if isinstance(offset, DistanceConstraint):
                        continue
                    neighbor_face.s = old_face.s + offset
                    neighbor_face.neighbors[:]\
                            = [p for p in neighbor_face.neighbors
                                    if not p[0] == old_face]
                    new_leave_faces.append(neighbor_face)
            leave_faces = new_leave_faces

class ConstrainedBlock:
    def __init__(self, system: ConstraintSystem):
        #system.add(self)
        self.system = system
        self.faces = {
                Dimension.X: (Face(Dimension.X), Face(Dimension.X)),
                Dimension.Y: (Face(Dimension.Y), Face(Dimension.Y)),
                Dimension.Z: (Face(Dimension.Z), Face(Dimension.Z)),
                }
        #for face_l, face_h in self.faces.values():
        #    face_l.bind(face_h, offset=DistanceConstraint(">", 0))
        self.tb = traceback.format_stack()

    @staticmethod
    def from_faces(system, x0, x1, y0, y1, z0, z1):
        new_block = ConstrainedBlock(system)
        new_block.faces = {
                Dimension.X: (x0, x1),
                Dimension.Y: (y0, y1),
                Dimension.Z: (z0, z1),
                }
        return new_block

    @staticmethod
    def from_normals(system, *normals):
        new_block = ConstrainedBlock(system)
        for a_normal in normals:
            faces_tuple_as_list = list(new_block.faces[a_normal.dimension])
            faces_tuple_as_list[1 if a_normal.is_positive else 0]\
                    = a_normal.face
            new_block.faces[a_normal.dimension] = tuple(faces_tuple_as_list)
        return new_block

    def bind(
            self, other, dimension: Dimension,
            sign_self = FaceSign.plus, sign_other = FaceSign.minus,
            offset = 0):
        face_self = self.faces[dimension][sign_self.value]
        face_other = other.faces[dimension][sign_other.value]
        Face.bind_faces(face_self, face_other, offset)

    def lazy_bind_centered(self, other, dimension):
        def bind_closure():
            length_self = self.get_length(dimension)
            length_other = other.get_length(dimension)
            difference = float(length_self - length_other)/2
            self.get_low_face(dimension).bind(
                    other.get_low_face(dimension),
                    difference)

        try:
            bind_closure()
            return None
        except:
            return bind_closure

    def bind_internally(self, dimension: Dimension, offset):
        faces = self.faces[dimension]
        Face.bind_faces(faces[0], faces[1], offset)

    def unbind_internally(self, dimension: Dimension):
        faces = self.faces[dimension]
        Face.unbind_faces(faces[0], faces[1])

    def get_face(self, dimension: Dimension, sign: FaceSign):
        return self.faces[dimension][sign]

    def get_low_normal(self, dimension: Dimension):
        return Normal(self.faces[dimension][0], False)

    def get_high_normal(self, dimension: Dimension):
        return Normal(self.faces[dimension][1], True)

    def get_low_face(self, dimension: Dimension):
        return self.faces[dimension][0]

    def get_high_face(self, dimension: Dimension):
        return self.faces[dimension][1]

    def get_inner(self, normal):
        if normal.is_positive:
            return Normal(self.faces[normal.dimension][0], True)
        else:
            return Normal(self.faces[normal.dimension][1], False)

    def get_outer(self, normal):
        if normal.is_positive:
            return Normal(self.faces[normal.dimension][1], True)
        else:
            return Normal(self.faces[normal.dimension][0], False)

    def get_length(self, dimension: Dimension):
        return self.faces[dimension][0].get_distance(self.faces[dimension][1])

    def get_computed_length(self, dimension: Dimension):
        try:
            return self.faces[dimension][1].s - self.faces[dimension][0].s
        except AttributeError:
            pdb.set_trace()
            sys.exit("Something is underdefined.")

    def get_internal_length(self, dimension: Dimension):
        try:
            return next((abs(n[1]) for n in self.faces[dimension][0].neighbors
                if n[0] == self.faces[dimension][1]
                and not isinstance(n[1], DistanceConstraint)))
        except IndexError:
            pdb.set_trace()
            sys.exit("No internal bind.")

    def get_position(self, dimension: Dimension):
        try:
            return self.faces[dimension][0].s
        except AttributeError:
            pdb.set_trace()
            sys.exit("Something is underdefined")

    def intersects(self, other):
        for dimension in Dimension:
            face_self_0 = self.faces[dimension][0]
            face_self_1 = self.faces[dimension][1]
            face_other_0 = other.faces[dimension][0]
            face_other_1 = other.faces[dimension][1]
            try:
                distance_0_1 = face_self_0.get_distance(face_other_1)
                distance_1_0 = face_self_1.get_distance(face_other_0)
            except:
                return False
            if distance_0_1 < 0 or distance_1_0 > 0:
                return False
        return True

    def make_hole(self, hole_block):
        raise NotImplementedError

    def union(self, other):
        the_union = ConstrainedBlock(self.system)
        try:
            for dimension in Dimension:
                the_union.faces[dimension] = (
                        self.faces[dimension][0]
                        if self.faces[dimension][0].get_distance(
                            other.faces[dimension][0]) > 0
                        else other.faces[dimension][0],
                        other.faces[dimension][1]
                        if self.faces[dimension][1].get_distance(
                            other.faces[dimension][1]) > 0
                        else self.faces[dimension][1]
                        )
        except:
            pdb.set_trace()
            debug()
        return the_union

    def __add__(self, other):
        return self.union(other)

    
class Face:
    def __init__(self, normal_dimension: Dimension):
        # list of neighbor tuples: (neighbor, offset)
        self.neighbors = []
        self.normal_dimension = normal_dimension

    @staticmethod
    def bind_faces(face_0, face_1, offset = 0):
        face_0.remove_neighbor(face_1)
        face_1.remove_neighbor(face_0)
        face_0.add_neighbor(face_1, offset)
        face_1.add_neighbor(face_0, -offset)

    def unbind_faces(face_0, face_1):
        face_0.remove_neighbor(face_1)
        face_1.remove_neighbor(face_0)

    def bind(self, other, offset = 0):
        Face.bind_faces(self, other, offset)

    def add_neighbor(self, neighbor, offset):
        self.neighbors.append((neighbor, offset))

    def remove_neighbor(self, neighbor):
        self.neighbors[:] = [n for n in self.neighbors if not n[0] == neighbor]

    def remove_neighbor(self, neighbor):
        self.neighbors[:] = [n for n in self.neighbors if not n[0] == neighbor]

    def get_distance(self, other):
        if self == other:
            return 0

        candidates = []
        def distance_recursion(seen_faces, current_face, distance):
            if current_face == other:
                candidates.append(distance)
            for neighbor_face, neighbor_distance in current_face.neighbors:
                if neighbor_face in seen_faces:
                    continue

                try:
                    new_distance = distance + neighbor_distance
                except ValueError:
                    continue

                distance_recursion(
                        seen_faces | set([neighbor_face]),
                        neighbor_face,
                        new_distance)

        distance_recursion(set([self]), self, 0)

        if len(candidates) > 2:
            pdb.set_trace()
            raise NotImplementedError
        elif len(candidates) == 1:
            #if isinstance(candidates[0], DistanceConstraint):
            #    pdb.set_trace()
            return candidates[0]
        elif len(candidates) == 2:
            for candidate in candidates:
                if isinstance(candidate, int) or isinstance(candidate, float):
                    return candidate
            return candidates[0] # TODO: actually choose which imprecise
        else:
            raise DistanceNotConstrainedException


class Normal:
    def __init__(self, face, is_positive):
        self.face = face
        self.is_positive = is_positive

    def copy(self):
        return Normal(Face(self.dimension), self.is_positive)

    def offset_copy(self, offset):
        new_normal = self.copy()
        if self.is_positive:
            self.bind(new_normal, offset)
        else:
            self.bind(new_normal, -offset)
        return new_normal

    @property
    def dimension(self):
        return self.face.normal_dimension

    def flipped(self):
        return Normal(self.face, not self.is_positive)

    def bind(self, other, offset=0):
        if isinstance(other, ConstrainedBlock):
            other_face = other.get_inner(self).face
            Face.bind_faces(self.face, other_face, offset)
        elif isinstance(other, Normal):
            Face.bind_faces(self.face, other.face, offset)
        else:
            raise NotImplementedError
