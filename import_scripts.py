# -*- coding: utf-8 -*-

import csv
import json
import logging
import os

from database import (
    DeclarativeGroup, default_engine, default_session,
    IntegrityError, NoResultFound
)
import database.writing as db_writing
from database.encoding import CodePoint

dirpath = "scripts"
script_filepath = os.path.join(dirpath, "scripts.json")
script_type_filepath = os.path.join(dirpath,"script_types.csv")
character_form_type_filepath = os.path.join(dirpath,"character_form_types.csv")
characters_dir = os.path.join(dirpath, "characters")

def load_scripts_from_json(session, filepath):
    with open(filepath, "r") as json_file:
        script_families = json.load(json_file)
    
    for family_name, script_list in script_families.items():
        family_obj = db_writing.ScriptFamily(
            name = family_name
        )
        family_obj = db_writing.ScriptFamily.prompt_merge(family_obj, session)
        session.commit()
        for script_dict in script_list:
            script_obj = db_writing.Script(
                name = script_dict["name"],
                family_id = family_obj.id,
                adjective = script_dict.get("adjective",None),
                iso_15924 = script_dict.get("iso_15924",None),
                direction = script_dict.get("direction",None),
                noto_fontname = script_dict.get("noto_fontname",None),
                comment = script_dict.get("comment",None),
            )
            script_obj = db_writing.Script.prompt_merge(script_obj, session)
            session.commit()
            script_types = script_dict.get("types",[])
            for script_type_name in script_types:
                script_type = session.query(
                        db_writing.ScriptType,
                    ).filter(
                        db_writing.ScriptType.name == script_type_name,
                    ).one()
                mapping_obj = session.query(
                        db_writing.ScriptTypeMapping,
                    ).filter(
                        db_writing.ScriptTypeMapping.script_id == script_obj.id,
                        db_writing.ScriptTypeMapping.type_id == script_type.id,
                    ).one_or_none()
                if mapping_obj is None: 
                    mapping_obj = db_writing.ScriptTypeMapping(
                        script_id = script_obj.id,
                        type_id = script_type.id,
                    )
                    session.add(mapping_obj)
    session.commit()

def load_characters_from_json(session, dir_path, script_family):
    filename = f"{script_family.name.lower().replace(' ', '_')}.json"
    filepath = os.path.join(dir_path, filename)
    if os.path.isfile(filepath):
        logging.info(f"Loading graphemes from {filepath}.")
        with open(filepath, "r") as json_file:
            graphemes = json.load(json_file)
            for grapheme_name, grapheme_data in graphemes.items():
                load_grapheme(session, script_family, grapheme_name, grapheme_data)
    else:
        logging.debug(f"No grapheme file was found at {filepath}.")

def load_grapheme(session, script_family, grapheme_name, grapheme_data):
    grapheme_obj = db_writing.Grapheme(
        script_family_id = script_family.id,
        name = grapheme_name,
        name_meaning = None,
    )
    grapheme_obj = db_writing.Grapheme.prompt_merge(grapheme_obj, session)
    session.commit()
    for character_data in grapheme_data.get("characters", []):
        load_character(session, grapheme_obj, character_data)
    
def load_character(session, grapheme_obj, character_data):
    script_name = character_data["script"]
    script_query = session.query(
            db_writing.Script,
        ).filter(
            db_writing.Script.name == script_name
        )
    try:
        script_obj = script_query.one()
    except NoResultFound:
        logging.warning(f"Trying to load characters for the script {script_name!r}, but no such script exists in the database. Skipping this character data.")
        return None
    character_obj = db_writing.Character(
        grapheme_id = grapheme_obj.id,
        script_id = script_obj.id,
        name = None,
        name_meaning = None,
    )
    character_obj = db_writing.Character.prompt_merge(character_obj, session)
    session.commit()
    
    for form_data in character_data.get("forms", []):
        load_character_form(session, character_obj, form_data)
        
def load_character_form(session, character_obj, form_data):
    if form_data.get("unicode", None):
        code_point_index = ord(form_data["unicode"])
        code_point = session.query(CodePoint).get(code_point_index)
        if code_point is None:
            logging.warning(f"{code_point_index}/{CodePoint._hex_point(code_point_index)} is not in the database. No codepoint will be associated with the character form.")
            code_point_index = None
            
    else:
        code_point_index = None
    form_type_obj = session.query(
            db_writing.CharacterFormType
        ).filter(
            db_writing.CharacterFormType.name == form_data["form_type"],
        ).one()
    form_obj = db_writing.CharacterForm(
        character_id = character_obj.id,
        character_form_type_id = form_type_obj.id,
        code_point_id = code_point_index,
    )
    form_obj = db_writing.CharacterForm.prompt_merge(form_obj, session)
    session.commit()

if __name__ == "__main__":
    import argparse
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s [%(name)s] [%(threadName)s] %(message)s",
    )
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-i', '--initialize',
        action = 'store_true',
        help = 'Erases existing database and starts from scratch.'
    )
    parser.add_argument(
        '-r', '--read',
        action = 'store_true',
        help = 'Read from files.'
    )
    parser.add_argument(
        '-w', '--write',
        action = 'store_true',
        help = 'Write to files. (Only CSVs. Writing JSON NYI)'
    )
    args = parser.parse_args()
    engine = default_engine()
    engine.initialize_tables(DeclarativeGroup.metadata, re_initialize=args.initialize)
    session = default_session()
    
    if args.read:
        logging.info(f"Loading script type data from {script_type_filepath}.")
        db_writing.ScriptType.load_from_csv(session, script_type_filepath, prompt_merge=True)
        
        logging.info("Loading scripts from json.")
        load_scripts_from_json(session, script_filepath)
        
        logging.info(f"Loading character form type data from {character_form_type_filepath}.")
        db_writing.CharacterFormType.load_from_csv(session, character_form_type_filepath, prompt_merge=True)
        
        script_families = session.query(db_writing.ScriptFamily).all()
        for script_family in script_families:
            load_characters_from_json(session, characters_dir, script_family)
        
    if args.write:
        logging.info(f"Writing script type data from {script_type_filepath}.")
        db_writing.ScriptType.write_to_csv(session, script_type_filepath)
        
        logging.info(f"Writing script type data from {character_form_type_filepath}.")
        db_writing.CharacterFormType.write_to_csv(session, character_form_type_filepath)
        
    
    session.commit()
    session.close()
