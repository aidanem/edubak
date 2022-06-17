# -*- coding: utf-8 -*-

import logging
import re

import sqlalchemy as sqla
import sqlalchemy.orm

import hermes

from .declaration import DeclarativeGroup, default_engine, default_session
from .writing import Script



class Language(DeclarativeGroup, hermes.DynamicReprMixin, hermes.MergeMixin):
    __tablename__ = 'languages'
    
    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String, unique=True)
    bcp47 = sqla.Column(sqla.String)
    
    _unique_keys = [
        "name",
    ]
    
    def safe_name(self):
        return re.sub(r'\W', '', self.name)
    
    @classmethod
    def get_by_name(cls, name, session):
        try:
            language = session.query(
                    cls
                ).filter(
                    cls.name == name,
                ).one()
        except sqlalchemy.orm.exc.NoResultFound:
            try:
                language = LanguageAutoCorrection.get_language_by_input(name, session)
            except:
                raise ValueError(f"No language found for input: {name!r}")
        return language
    
    def script_from_bcp47(self, session):
        if self.bcp47 is not None:
            for tag_part in self.bcp47.split("-")[1:]:
                try:
                    return Script.get_by_iso_15924(tag_part, session)
                except ValueError:
                    continue
            else:
                return None
    
    children = sqlalchemy.orm.relationship(
        "Language",
        secondary = "language_descent_mapping",
        back_populates = "parents",
        primaryjoin = "Language.id == LanguageDescentMapping.parent_id",
        secondaryjoin = "LanguageDescentMapping.child_id == Language.id",
    )
    
    parents = sqlalchemy.orm.relationship(
        "Language",
        secondary = "language_descent_mapping",
        back_populates = "children",
        primaryjoin = "Language.id == LanguageDescentMapping.child_id",
        secondaryjoin = "LanguageDescentMapping.parent_id == Language.id",
    )
    
    @classmethod
    def write_json(session):
        import json
        from collections import defaultdict
        language_autocorrects = session.query(LanguageAutoCorrection).all()
        autocorrects_map = defaultdict(list)
    
        for autocorrection in language_autocorrects:
            autocorrects_map[autocorrection.language_id].append(autocorrection.input)
    
        languages = session.query(Language).all()
        language_data = []
        for language in languages:
            lang_dict = {
                "name": language.name,
                "subtag": language.subtag,
                "style_classes": list(language.style_classes),
                "direct_parents": [parent.name for parent in language.parents],
                "autocorrects": autocorrects_map[id],
            }
            language_data.append(lang_dict)
    
    
        with open("languages.json", "w") as json_file:
            json.dump(language_data, json_file, indent=2)
    
    @classmethod
    def read_json(session, initialize=False):
        import json
        with open("languages.json", "r") as json_file:
            language_data = json.load(json_file)
        if initialize:
            default_engine().initialize_tables(
                DeclarativeGroup.metadata,
                re_initialize = True,
            )
        if initialize:
            session.add_all([
                DerivationType(name = "synchronic_derivation"),
                DerivationType(name = "diachronic_derivation"),
                DerivationType(name = "borrowing"),
            ])
        for lang_dict in language_data:
            language_obj = Language(
                name = lang_dict["name"],
                bcp47 = lang_dict["subtag"],
                style_classes = []
            )
            hermes.prompt_merge(Language, language_obj, session, "name")
        session.commit()
        for lang_dict in language_data:
            language = Language.get_by_name(lang_dict["name"], session)
            style_classes = set(language.style_classes).union(lang_dict["style_classes"])
            if lang_dict["direct_parents"]:
                for parent_language_name in lang_dict["direct_parents"]:
                    parent = Language.get_by_name(parent_language_name, session)
                    language_descent_obj = LanguageDescentMapping(
                        parent_id = parent.id,
                        child_id = language.id,
                    )
                    hermes.prompt_merge(Language, language_obj, session, "name")
                    style_classes = style_classes.union(parent.style_classes)
                    language.style_classes = list(style_classes)
                    session.merge(language_descent_obj)
            if lang_dict["autocorrects"]:
                for input in lang_dict["autocorrects"]:
                    autocorrect_obj = LanguageAutoCorrection(
                        language.id,
                        input,
                    )
                    session.merge(autocorrect_obj)
        session.commit()


class LanguageDescentMapping(
        DeclarativeGroup,
        hermes.DynamicReprMixin,
        hermes.MergeMixin
    ):
    __tablename__ = 'language_descent_mapping'
    __table_args__ = (
        sqla.PrimaryKeyConstraint(
            'parent_id',
            'child_id',
        ),
    )
    
    parent_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("languages.id"),
    )
    child_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("languages.id"),
    )
    
    _unique_keys = [
        "parent_id",
        "child_id",
    ]

class LanguageAutoCorrection(
        DeclarativeGroup,
        hermes.DynamicReprMixin,
        hermes.MergeMixin
    ):
    __tablename__ = 'language_autocorrections'
    
    input = sqla.Column(sqla.String, primary_key=True)
    language_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("languages.id")
    )
    
    _unique_keys = ["input"]
    
    @classmethod
    def get_language_by_input(cls, input, session):
        language = session.query(
                cls
            ).filter(
                cls.input == input,
            ).one().language
        return language
    
    language = sqlalchemy.orm.relationship("Language")

class Word(DeclarativeGroup, hermes.DynamicReprMixin, hermes.MergeMixin):
    __tablename__ = 'words'
    
    id = sqla.Column(sqla.Integer, primary_key=True)
    language_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("languages.id")
    )
    orthography = sqla.Column(sqla.String)
    latin_transliteration = sqla.Column(sqla.String)
    meaning = sqla.Column(sqla.String)
    inline_note = sqla.Column(sqla.String)
    
    _unique_keys = [
        "language_id",
        "orthography",
        "latin_transliteration",
    ]
    
    language = sqlalchemy.orm.relationship("Language")
    
    children = sqlalchemy.orm.relationship(
        "Word",
        secondary = "word_derivations",
        back_populates = "parents",
        primaryjoin = "Word.id == Derivation.parent_id",
        secondaryjoin = "Derivation.child_id == Word.id",
    )
    
    parents = sqlalchemy.orm.relationship(
        "Word",
        secondary = "word_derivations",
        back_populates = "children",
        primaryjoin = "Word.id == Derivation.child_id",
        secondaryjoin = "Derivation.parent_id == Word.id",
    )

class DerivationType(DeclarativeGroup, hermes.DynamicReprMixin):
    __tablename__ = 'word_derivation_types'
    
    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String, unique=True)


class Derivation(DeclarativeGroup, hermes.DynamicReprMixin):
    __tablename__ = 'word_derivations'
    
    __table_args__ = (
        sqla.PrimaryKeyConstraint(
            'parent_id',
            'child_id',
        ),
    )
    parent_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("words.id")
    )
    child_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("words.id")
    )
    confident = sqla.Column(sqla.Boolean, default=True)
    derivation_type_id = sqla.Column(
        sqla.Integer,
        sqla.ForeignKey("word_derivation_types.id")
    )
    
    derivation_type = sqlalchemy.orm.relationship("DerivationType")
