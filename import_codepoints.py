# -*- coding: utf-8 -*-

import logging
import unicodedata

from database import DeclarativeGroup, encoding, default_engine, default_session

encoding_classes = {
    encoding.Plane: "codepoints/planes.csv",
    encoding.Block: "codepoints/blocks.csv",
    encoding.GeneralCategory: "codepoints/categories.csv",
    encoding.CodePoint: "codepoints/codepoints.csv",
}


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
        help = 'Read from csv files.'
    )
    parser.add_argument(
        '-w', '--write',
        action = 'store_true',
        help = 'Write to csv files.'
    )
    parser.add_argument(
        '-g', '--generate-codepoints',
        action = 'store_true',
        help = 'Generate codepoint objects from blocks.'
    )
    args = parser.parse_args()
    engine = default_engine()
    engine.initialize_tables(DeclarativeGroup.metadata, re_initialize=args.initialize)
    session = default_session()
    
    
    if args.read:
        for encoding_class, filepath in encoding_classes.items():
            try:
                logging.info(f"Loading {encoding_class.__name__!s} data from {filepath}.")
                encoding_class.load_from_csv(session, filepath, prompt_merge=True)
            except FileNotFoundError:
                logging.warning(f"No file was found at {filepath}. Skipping loading {encoding_class.__name__}")
            session.commit()
    if args.generate_codepoints:
        blocks = session.query(encoding.Block).all()
        for block in blocks:
            if block.include_points:
                logging.info(f"Generating codepoints in {block.name} block.")
                for point_value in block.points_gen():
                    character = chr(point_value)
                    category_abbr = unicodedata.category(character)
                    category = encoding.GeneralCategory.get_by_abbreviation(
                        session,
                        category_abbr,
                    )
                    if category.include_points:
                        code_point_obj = encoding.CodePoint(
                            id = point_value,
                            block_id = block.id,
                        )
                        encoding.CodePoint.prompt_merge(code_point_obj, session)
        session.commit()
            
    if args.write:
        for encoding_class, filepath in encoding_classes.items():
            logging.info(f"Writing {encoding_class.__name__!s} data to {filepath}.")
            encoding_class.write_to_csv(session, filepath)
    
    session.commit()
    session.close()
    
    
