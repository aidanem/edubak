# -*- coding: utf-8 -*-

import json
import logging
import os

from database import *

if __name__ == "__main__":
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s [%(name)s] [%(threadName)s] %(message)s")
    
    engine = default_engine()
    session = default_session()
    
    logging.info(f"Reading style file.")
    with open("styles.json") as json_file:
        style_data = json.load(json_file)
        for style_dict in style_data:
            style_obj = LanguageStyle(
                name = style_dict["name"],
                dot_styling = style_dict.get("dot_style"),
            )
            LanguageStyle.prompt_merge(style_obj, session)
    session.commit()
            
    
    languages_list = []
    parents_dict = {}
    autocorrects_dict = {}
    styles_dict = {}
    
    for filename in sorted(os.listdir("languages")):
        if os.path.splitext(filename)[1] == ".json":
            logging.info(f"Reading {filename}.")
            json_filepath = os.path.join("languages",filename)
            with open(json_filepath, "r") as json_file:
                language_data = json.load(json_file)
                
                for language_dict in language_data:
                    
                    language_obj = Language(
                        name = language_dict["name"],
                        bcp47 = language_dict.get("bcp47"),
                    )
                    Language.prompt_merge(language_obj, session)
                    languages_list.append(language_dict["name"])
                    parents_dict[language_dict["name"]] = language_dict.get(
                        "direct_parents",
                        []
                    )
                    autocorrects_dict[language_dict["name"]] = language_dict.get(
                        "autocorrects",
                        []
                    )
                    style_classes = set(language_dict.get(
                        "style_classes",
                        []
                    ))
                    styles_dict[language_dict["name"]] = style_classes
                session.commit()
    
            
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
            styles_dict[language_name].update(styles_dict[parent_name])
        
        for style_name in styles_dict[language_name]:
            try:
                style = session.query(
                    LanguageStyle,
                ).filter(
                    LanguageStyle.name == style_name,
                ).one()
                mapping_obj = LanguageStyleMapping(
                    language_id = language.id,
                    style_id = style.id,
                )
                LanguageStyleMapping.prompt_merge(mapping_obj, session)
            except Exception as ex:
                import pdb; pdb.set_trace()
        
        for input in autocorrects_dict[language_name]:
            autocorrect_obj = LanguageAutoCorrection(
                input = input,
                language_id = language.id,
            )
            LanguageAutoCorrection.prompt_merge(autocorrect_obj, session)
    
    session.commit()
    session.close()
    