# -*- coding: utf-8 -*-

from collections import defaultdict
import csv
import logging
import re

import sqlalchemy as sqla
import sqlalchemy.orm
from sqlalchemy.exc import NoResultFound

import hermes

from .declaration import Base, MergeBase

iso_15924_pattern = re.compile("[A-Z][a-z]{3}")

class ScriptFamily(MergeBase):
    __tablename__ = 'script_families'
    _unique_keys = ["name",]

    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String)
    
    
    ordering_sequences = sqlalchemy.orm.relationship(
        "OrderingSequence",
        back_populates='script_family'
    )

class Script(MergeBase):
    __tablename__ = 'scripts'
    _unique_keys = ["name",]
    
    id = sqla.Column(sqla.Integer, primary_key=True)
    family_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("script_families.id")
    )
    name = sqla.Column(sqla.String)
    adjective = sqla.Column(sqla.String)
    iso_15924 = sqla.Column(sqla.String, unique=True)
    #type_ = sqla.Column(sqla.String) # switch to multiple types per Script
    direction = sqla.Column(sqla.String)
    noto_fontname = sqla.Column(sqla.String)
    comment = sqla.Column(sqla.String)
    
    
    characters = sqlalchemy.orm.relationship("Character", back_populates='script')

    transliteration_schemes = sqlalchemy.orm.relationship(
        "TransliterationScheme",
        back_populates='source_script',
        primaryjoin = "Script.id == TransliterationScheme.source_script_id",
    )
    
    types = sqlalchemy.orm.relationship("ScriptType", back_populates='scripts', secondary="script_type_mapping")

class ScriptType(MergeBase):
    __tablename__ = 'script_types'
    _unique_keys = ["name",]
    
    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String)
    
    scripts = sqlalchemy.orm.relationship("Script", back_populates='types', secondary="script_type_mapping")

class ScriptTypeMapping(Base):
    __tablename__ = 'script_type_mapping'
    __table_args__ = (
        sqla.PrimaryKeyConstraint(
            'script_id',
            'type_id',
        ),
    )
    
    script_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("scripts.id"),
    )
    type_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("script_types.id"),
    )


class OrderingSequence(Base):
    __tablename__ = 'ordering_sequences'
    __table_args__ = (
        sqla.UniqueConstraint(
            'script_family_id',
            'priority',
        ),
        sqla.UniqueConstraint(
            'script_family_id',
            'name',
        ),
    )
    
    id = sqla.Column(sqla.Integer, primary_key=True)
    script_family_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("script_families.id")
    )
    name = sqla.Column(sqla.String)
    priority = sqla.Column(sqla.Integer)
    
    script_family = sqlalchemy.orm.relationship("ScriptFamily", back_populates='ordering_sequences')
    
    mappings = sqlalchemy.orm.relationship("OrderMapping", back_populates='sequence')
    
    def order(self, characters):
        character_map = {character.id: character for character in characters}
        ordered_characters = {mapping.order: character_map[mapping.character_id] for mapping in self.mappings}
        unordered_characters = [character for character in characters if character not in ordered_characters.values()]
        return ordered_characters, unordered_characters
    


class TransliterationScheme(Base):
    __tablename__ = 'transliteration_schemes'
    __table_args__ = (
        sqla.UniqueConstraint(
            'source_script_id',
            'priority',
        ),
    )
    
    id = sqla.Column(sqla.Integer, primary_key=True)
    source_script_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("scripts.id")
    )
    target_script_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("scripts.id")
    )
    name = sqla.Column(sqla.String)
    priority = sqla.Column(sqla.Integer)
    
    source_script = sqlalchemy.orm.relationship(
        "Script",
        back_populates='transliteration_schemes',
        primaryjoin = "Script.id == TransliterationScheme.source_script_id",
    )
    
    target_script = sqlalchemy.orm.relationship(
        "Script",
        primaryjoin = "Script.id == TransliterationScheme.target_script_id",
    )
    
    mappings = sqlalchemy.orm.relationship("TransliterationMapping", back_populates='scheme')


class Grapheme(MergeBase):
    __tablename__ = 'graphemes'
    __table_args__ = (
        sqla.UniqueConstraint(
            'script_family_id',
            'name',
        ),
    )
    _unique_keys = ["script_family_id","name"]
    
    id = sqla.Column(sqla.Integer, primary_key=True)
    script_family_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("script_families.id")
    )
    name = sqla.Column(sqla.String)
    name_meaning = sqla.Column(sqla.String)
    
    characters = sqlalchemy.orm.relationship("Character", back_populates='grapheme')
    

class Character(MergeBase):
    __tablename__ = 'characters'
    __table_args__ = (
        sqla.UniqueConstraint(
            'grapheme_id',
            'script_id',
        ),
        sqla.UniqueConstraint(
            'script_id',
            'name',
        ),
    )
    _unique_keys = ["grapheme_id","script_id"]
    
    id = sqla.Column(sqla.Integer, primary_key=True)
    grapheme_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("graphemes.id")
    )
    script_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("scripts.id", ondelete='SET NULL')
    )
    
    name = sqla.Column(sqla.String)
    name_meaning = sqla.Column(sqla.String)
    
    script = sqlalchemy.orm.relationship(
        "Script",
        back_populates='characters',
    )
    grapheme = sqlalchemy.orm.relationship(
        "Grapheme",
        back_populates='characters',
    )
    forms = sqlalchemy.orm.relationship("CharacterForm", back_populates='character')
    orderings = sqlalchemy.orm.relationship(
        "OrderMapping",
        back_populates='character',
    )
    
    def transliterate(self, scheme, session):
        import transliteration
        return transliteration.transliterate(self.unicode_, scheme, session)
        
        
class CharacterForm(MergeBase):
    __tablename__ = 'character_forms'
    __table_args__ = (
        sqla.UniqueConstraint(
            'character_id',
            'character_form_type_id',
        ),
    )
    _unique_keys = ["character_id","character_form_type_id"]
    
    id = sqla.Column(sqla.Integer, primary_key=True)
    character_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("characters.id")
    )
    character_form_type_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("character_form_types.id")
    )
    code_point_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("code_points.id")
    )
    
    character = sqlalchemy.orm.relationship(
        "Character",
        back_populates='forms',
    )
    form_type = sqlalchemy.orm.relationship("CharacterFormType")
    unicode = sqlalchemy.orm.relationship("CodePoint")
    
    # make additional relations that get descent mapping,
    # instead of skipping directly to the related character (get confidence)
    children = sqlalchemy.orm.relationship(
        "CharacterForm",
        secondary = "character_descent_mapping",
        back_populates = "parents",
        primaryjoin = "CharacterForm.id == CharacterDescentMapping.parent_id",
        secondaryjoin = "CharacterDescentMapping.child_id == CharacterForm.id",
    )
    
    parents = sqlalchemy.orm.relationship(
        "CharacterForm",
        secondary = "character_descent_mapping",
        back_populates = "children",
        primaryjoin = "CharacterForm.id == CharacterDescentMapping.child_id",
        secondaryjoin = "CharacterDescentMapping.parent_id == CharacterForm.id",
    )
    

class CharacterFormType(MergeBase):
    __tablename__ = 'character_form_types'
    _unique_keys = ["name",]
    
    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String)

class OrderMapping(Base):
    __tablename__ = 'order_mappings'
    __table_args__ = (
        sqla.PrimaryKeyConstraint(
            'sequence_id',
            'order',
        ),
    )
    
    sequence_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("ordering_sequences.id")
    )
    order = sqla.Column(sqla.Integer)
    character_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("characters.id")
    )
    
    sequence = sqlalchemy.orm.relationship(
        "OrderingSequence",
        back_populates='mappings',
    )
    
    character = sqlalchemy.orm.relationship("Character", back_populates='orderings')


class TransliterationMapping(Base):
    __tablename__ = 'transliteration_mapping'
    
    scheme_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("transliteration_schemes.id"),
        primary_key=True
    )
    source_unicode = sqla.Column(sqla.String, primary_key=True)
    target_unicode = sqla.Column(sqla.String)
    
    scheme = sqlalchemy.orm.relationship(
        "TransliterationScheme",
        back_populates='mappings',
    )


class CharacterDescentMapping(MergeBase):
    __tablename__ = 'character_descent_mapping'
    __table_args__ = (
        sqla.PrimaryKeyConstraint(
            'parent_id',
            'child_id',
        ),
    )
    _unique_keys = ["parent_id","child_id"]
    
    parent_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("character_forms.id"),
    )
    child_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("character_forms.id"),
    )
    confidence = sqla.Column(sqla.Boolean, default=True)
    
    @classmethod
    def load_from_csv(cls, session, filepath, prompt_merge=False):
        with open(filepath, 'r') as csv_file:
            reader = csv.reader(csv_file)
            headers = next(reader)
            for row in reader:
                parent_grapheme, parent_script, parent_character_type, child_grapheme, child_script, child_character_type, confidence = row
                try:
                    parent = session.query(
                            CharacterForm,
                        ).join(
                            CharacterForm.character,
                            Character.grapheme,
                            Character.script,
                            CharacterForm.form_type
                        ).filter(
                            Grapheme.name == parent_grapheme,
                            Script.name == parent_script,
                            CharacterFormType.name == parent_character_type,
                        ).one()
                except NoResultFound:
                    logging.error(f"Found no result for parent glyph <{parent_grapheme}:{parent_script}:{parent_character_type}>. Skipping descent row.")
                    continue
                try:
                    child = session.query(
                            CharacterForm,
                        ).join(
                            CharacterForm.character,
                            Character.grapheme,
                            Character.script,
                            CharacterForm.form_type
                        ).filter(
                            Grapheme.name == child_grapheme,
                            Script.name == child_script,
                            CharacterFormType.name == child_character_type,
                        ).one()
                except NoResultFound:
                    logging.error(f"Found no result for parent glyph <{child_grapheme}:{child_script}:{child_character_type}>. Skipping descent row.")
                    continue
                cls_obj = cls(
                    parent_id = parent.id,
                    child_id = child.id,
                    confidence = bool(int(confidence)),
                )
                if prompt_merge:
                    cls.prompt_merge(cls_obj, session)
                else:
                    session.add(cls_obj)
    

"""sqla.Index(
    'child_parent_ix', #index primary keys in opposite order
    CharacterDescentMapping.child_id,
    CharacterDescentMapping.parent_id,
)"""


