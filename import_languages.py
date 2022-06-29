# -*- coding: utf-8 -*-

import json
import logging
import os

from database import DeclarativeGroup, default_engine, default_session
from database.linguistic import Language, LanguageDescentMapping

dirpath = "languages"

def load_json_file(session, filepath):
    logging.info(f"Reading language data from {filepath}.")
    languages_list = []
    parents_dict = {}
    
    with open(filepath, "r") as json_file:
        language_data = json.load(json_file)
        
        for language_dict in language_data:
            bcp47 = language_dict.get("bcp47")
            if bcp47:
                iso639 = bcp47[:3]
            else:
                iso639 = language_dict.get("iso639")
            language_obj = Language(
                name = language_dict["name"],
                iso639 = iso639,
            )
            Language.prompt_merge(language_obj, session)
            languages_list.append(language_dict["name"])
            parents_dict[language_dict["name"]] = language_dict.get(
                "direct_parents",
                []
            )
        session.commit()
        return languages_list, parents_dict

def load_languages(session, dirpath):
    languages_list = []
    parents_dict = {}
    
    for filename in sorted(os.listdir(dirpath)):
        if os.path.splitext(filename)[1] == ".json":
            json_filepath = os.path.join(dirpath,filename)
            file_languages, file_parents = load_json_file(session, json_filepath)
            session.commit()
            languages_list.extend(file_languages)
            parents_dict.update(file_parents)
            
    for language_name in languages_list:
        language = session.query(
            Language,
        ).filter(
            Language.name == language_name,
        ).one()
        for parent_name in parents_dict[language_name]:
            try:
                parent = session.query(
                    Language,
                ).filter(
                    Language.name == parent_name,
                ).one()
            except:
                logging.error(f"Parent language: {parent_name!r} could not be found (for {language_name})")
            descent_obj = LanguageDescentMapping(
                parent_id = parent.id,
                child_id = language.id,
            )
            LanguageDescentMapping.prompt_merge(descent_obj, session)
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
        help = 'Read from json files.'
    )
    parser.add_argument(
        '-w', '--write',
        action = 'store_true',
        help = 'Write to json files. (NYI)'
    )
    args = parser.parse_args()
    engine = default_engine()
    engine.initialize_tables(DeclarativeGroup.metadata, re_initialize=args.initialize)
    session = default_session()
    
    if args.read:
        load_languages(session, dirpath)
    if args.write:
        pass
    
    session.commit()
    session.close()
