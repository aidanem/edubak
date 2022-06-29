import argparse
import logging

import database as db

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
        "graphemes",
        metavar='GRAPH',
        type=str,
        nargs="*",
        help='One or more grapheme names to detail.'
    )
    args = parser.parse_args()
    session = db.default_session()
    
    grapheme_query = session.query(db.writing.Grapheme)
    if args.graphemes:
        grapheme_query = grapheme_query.filter(
                db.writing.Grapheme.name.in_(args.graphemes)
            )
    
    graphemes = grapheme_query.all()

    for grapheme in graphemes:
        for character in grapheme.characters:
            for form in character.forms:
                if hasattr(form, "unicode") and form.unicode:
                    print(f"{grapheme.name} ({form.form_type.name}) in {character.script.name}: {form.unicode.glyph} ({form.unicode.hex_point})")
                else:
                    print(f"{grapheme.name} ({form.form_type.name}) in {character.script.name} (No Unicode)")