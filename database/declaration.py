# -*- coding: utf-8 -*-

import logging
import os

from sqlalchemy.ext.declarative import declarative_base

import hermes

module_path = os.path.abspath(os.path.dirname(__file__))

DeclarativeGroup = declarative_base()

class Base(DeclarativeGroup, hermes.DynamicReprMixin, hermes.CsvMixin):
    __abstract__ = True
    #csvmixin, jsonmixin?

class MergeBase(Base, hermes.MergeMixin):
    __abstract__ = True

def default_engine():
    return hermes.SQLiteEngine(
        path = os.path.join(module_path, "database.db"),
        foreign_keys = True,
    )

def default_session():
    return default_engine().Session()
