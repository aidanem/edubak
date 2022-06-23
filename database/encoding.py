# -*- coding: utf-8 -*-

import csv
import json
import logging
import re
import unicodedata

import sqlalchemy as sqla
import sqlalchemy.orm

import hermes


from .declaration import Base, MergeBase

class Plane(MergeBase):
    __tablename__ = 'planes'
    
    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String, unique=True)
    short_name = sqla.Column(sqla.String, unique=True)
    
    _unique_keys = [
        "id",
    ]
    
    blocks = sqlalchemy.orm.relationship(
        "Block",
        back_populates = 'plane',
    )
    
    _size = 65536
    
    @staticmethod
    def calculated_plane_id(code_point):
        return code_point // Plane._size


class Block(MergeBase):
    __tablename__ = 'blocks'
    _unique_keys = [
        "name",
        "start_point",
    ]
    
    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String, unique=True)
    start_point = sqla.Column(sqla.Integer, unique=True)
    size = sqla.Column(sqla.Integer)
    plane_id = sqla.Column(sqla.Integer, sqla.ForeignKey("planes.id"))
    include_points = sqla.Column(sqla.Integer)
    @property
    def end_point(self):
        return self.start_point + self.size - 1
    def points_gen(self):
        for point in range(self.start_point, self.start_point + self.size):
            yield point
    
    plane = sqlalchemy.orm.relationship(
        "Plane",
        back_populates = 'blocks',
    )
    code_points = sqlalchemy.orm.relationship(
        "CodePoint",
        back_populates = 'block',
    )
    

class GeneralCategory(MergeBase):
    __tablename__ = 'general_categories'
    __table_args__ = (
        sqla.UniqueConstraint(
            'group_name',
            'name',
        ),
        sqla.UniqueConstraint(
            'group_abbreviation',
            'abbreviation',
        ),
    )
    _unique_keys = [
        "group_name",
        "name",
    ]
    
    #unique: group_id+name and group_id+abbreviation
    
    id = sqla.Column(sqla.Integer, primary_key=True)
    group_name = sqla.Column(sqla.String)
    name = sqla.Column(sqla.String)
    group_abbreviation = sqla.Column(sqla.String)
    abbreviation = sqla.Column(sqla.String)
    include_points = sqla.Column(sqla.Integer)
    
    @classmethod
    def get_by_abbreviation(cls, session, abbreviation):
        assert len(abbreviation) == 2
        return session.query(
                cls
            ).filter(
                cls.group_abbreviation == abbreviation[0],
                cls.abbreviation == abbreviation[1],
            ).one()

class CodePoint(MergeBase):
    __tablename__ = 'code_points'
    
    id = sqla.Column(sqla.Integer, primary_key=True)
    block_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("blocks.id")
    )
    
    block = sqlalchemy.orm.relationship(
        "Block",
        back_populates='code_points',
    )
    
    _unique_keys = [
        "id",
    ]
    
    @property
    def glyph(self):
        return chr(self.id)
    
    @staticmethod
    def _hex_point(index):
        plane_id = Plane.calculated_plane_id(index)
        if plane_id == 0:
            width = 4
        elif plane_id < 16:
            width = 5
        else:
            width = 6
        return f'U+{index:0{width}x}'
    
    @property
    def hex_point(self):
        return self._hex_point(self.id)
    
    @property
    def name(self):
        return unicodedata.name(self.glyph)
    
    def general_category(self, session):
        category_abbr = unicodedata.category(self.glyph)
        return GeneralCategory.get_by_abbreviation(session, category_abbr)
        