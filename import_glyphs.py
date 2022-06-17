# -*- coding: utf-8 -*-

import csv
import json
import logging

from database import *

def process_list_dict(string):
    out = {}
    try:
        if string:
            items_ = string.split(";")
            for item in items_:
                key, value = item.split(":")
                key = key.strip('/" ')
                value = value.strip('/" ')
                try:
                    value = int(value)
                except ValueError:
                    pass
                out[key] = value
    except Exception as e:
        print(e)
        import pdb; pdb.set_trace()
    else:
        return out

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s [%(name)s] [%(threadName)s] %(message)s",
    )
    engine = default_engine()
    engine.initialize_tables(DeclarativeGroup.metadata, re_initialize=True)
    session = default_session()
    
    
    # load scripts
    logging.info("Loading scripts from json.")
    with open("scripts/scripts.json", "r") as json_file:
        script_data = json.load(json_file)
    
    for script_dict in script_data:
        alternate_names = script_dict.get("alternate_names",[])
        
        script_obj = Script(
            name = script_dict["name"],
            adjective = script_dict.get("adjective",None),
            iso_15924 = script_dict.get("iso_15924",None),
            direction = script_dict.get("direction",None),
            noto_fontname = script_dict.get("noto_fontname",None),
            comment = script_dict.get("comment",None),
        )
        session.add(script_obj)
        session.commit()
        for name_ in alternate_names:
            session.add(
                ScriptAlternateNames(
                    script_id = script_obj.id,
                    name = name_,
                )
            )
            
    session.commit()
    #Script.export_css_file(session)
    
    # load transliteration schemes
    
    with open("scripts/transliteration_schemes.csv", 'r', encoding = "utf-8",) as transliteration_file:
        scheme_reader = csv.DictReader(transliteration_file)
        for row in scheme_reader:
            try:
                source_script = session.query(
                    Script,
                ).filter(
                    Script.name == row["source_script"],
                ).one()
                target_script = session.query(
                    Script,
                ).filter(
                    Script.name == row["target_script"],
                ).one()
            except Exception as e:
                print(e)
                import pdb; pdb.set_trace()
            
            session.add(
                TransliterationScheme(
                    source_script_id = source_script.id,
                    target_script_id = target_script.id,
                    name = row["name"],
                    priority = int(row["priority"]),
                )
            )
    session.commit()
    
    # load ordering sequences
    logging.info("Loading ordering sequence priorities")
    with open("scripts/ordering_sequences.csv", 'r', encoding = "utf-8",) as ordering_file:
        scheme_reader = csv.DictReader(ordering_file)
        for row in scheme_reader:
            try:
                script = session.query(
                    Script,
                ).filter(
                    Script.name == row["script"],
                ).one()
            except sqlalchemy.orm.exc.NoResultFound:
                logging.error(f"No script named {row['script']} was found, so the ordering sequence {row['name']} could not be loaded into the database.")
            session.add(
                OrderingSequence(
                    script_id = script.id,
                    name = row["name"],
                    priority = int(row["priority"]),
                )
            )
    session.commit()
    
    # load glyphs
    logging.info("Loading glyphs")
    last_script_adjective = None
    with open("scripts/glyphs - input.csv", 'r', encoding = "utf-8",) as glyph_file:
        glyph_reader = csv.DictReader(glyph_file)
        # save origins and transliterations for after all glyphs are loaded
        deferred_origin_data = {}
        deferred_transliteration_data = {}
        for row in glyph_reader:
            glyph_unicode = row["unicode_"] or None
            glyph_name = row["name"] or None
            script_name = row["script"]
            try:
                script = session.query(Script).filter(Script.name == script_name).one()
            except sqlalchemy.orm.exc.NoResultFound:
                import pdb; pdb.set_trace()
            if script.adjective != last_script_adjective:
                logging.info(f"Loading {script.adjective} glyphs")
                last_script_adjective = script.adjective
            diacritic = bool(int(row["diacritic"]))
            name_meaning = row["name_meaning"] or None
            english_name = row["english_name"] or None
            glyph_obj = Glyph(
                script_id = script.id,
                diacritic = diacritic,
                unicode_ = glyph_unicode,
                name = glyph_name,
                name_meaning = name_meaning,
                english_name = english_name,
            )
            session.add(glyph_obj)
            session.commit()
            
            orderings = process_list_dict(row["ordering"])
            for sequence_name, sequence_order in orderings.items():
                try:
                    ordering_sequence = session.query(
                            OrderingSequence
                        ).filter(
                            OrderingSequence.name == sequence_name,
                            OrderingSequence.script_id == script.id,
                        ).one()
                except sqlalchemy.orm.exc.NoResultFound:
                    import pdb; pdb.set_trace()
                order_mapping_obj = OrderMapping(
                    sequence_id = ordering_sequence.id,
                    order = sequence_order,
                    glyph_id = glyph_obj.id,
                )
                session.add(order_mapping_obj)
            variants = process_list_dict(row["variants"])
            """for variant_label, unicode_ in variants.items():
                glyph_variant_obj = GlyphVariant(
                        primary_id = glyph_obj.id,
                        label = variant_label,
                        unicode_ = unicode_,
                    )
                session.add(glyph_variant_obj)"""
            session.commit()
            
            
            origin = process_list_dict(row["origin"])
            if origin:
                deferred_origin_data[glyph_obj] = []
                for parent_glyph_identifier, confidence in origin.items():
                    deferred_origin_data[glyph_obj].append(
                            (parent_glyph_identifier, confidence,)
                        )
            
            transliteration = process_list_dict(row["transliteration"])
            if transliteration:
                deferred_transliteration_data[glyph_obj] = []
                for scheme_name, target_glyph_identifier in transliteration.items():
                    deferred_transliteration_data[glyph_obj].append(
                            (scheme_name, target_glyph_identifier,)
                        )
    
    logging.info("Loading glyph origin relationships.")
    for glyph_obj, origin_tuples in deferred_origin_data.items():
        for origin_tuple in origin_tuples:
            parent_glyph_identifier, confidence = origin_tuple
            try:
                parent_glyph = Glyph.get_by_unicode_or_name(
                        parent_glyph_identifier, session
                    )
            except Exception as e:
                print(e)
                import pdb; pdb.set_trace()
            descent_mapping_obj = GlyphDescentMapping(
                parent_id = parent_glyph.id,
                child_id = glyph_obj.id,
                confidence = confidence,
            )
            session.add(descent_mapping_obj)
    session.commit()
    
    logging.info("Loading glyph transliteration relationships.")
    missing_transliteration_schemes = set()
    for glyph_obj, transliteration_tuples in deferred_transliteration_data.items():
        for transliteration_tuple in transliteration_tuples:
            scheme_name, target_unicode = transliteration_tuple
            try:
                transliteration_scheme_obj = session.query(
                    TransliterationScheme,
                ).filter(
                    TransliterationScheme.name == scheme_name,
                ).one()
            except sqla.orm.exc.NoResultFound:
                missing_transliteration_schemes.add(scheme_name)
                continue
            except sqla.orm.exc.MultipleResultsFound:
                print(e)
                import pdb; pdb.set_trace()
            # For now, not all transliteration characters are loaded into the db
            # e.g. "ʾ"
            """target_glyph = Glyph.get_by_unicode_or_name(
                    target_glyph_identifier, session
                )
            if target_glyph is None:
                import pdb; pdb.set_trace()"""
        
            transliteation_mapping_obj = TransliterationMapping(
                scheme_id = transliteration_scheme_obj.id,
                source_unicode = glyph_obj.unicode_,
                target_unicode = target_unicode,
            )
            #variants
            session.add(transliteation_mapping_obj)
    session.commit()
    
    for transliteration_scheme_name in missing_transliteration_schemes:
        print(transliteration_scheme_name)
