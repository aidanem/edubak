import argparse
import logging

import database as db

alphabet_origins = [
    "F1:Egyptian hieroglyphs:Normal", #Alep
    "O1:Egyptian hieroglyphs:Normal", #Bayt
    "T14:Egyptian hieroglyphs:Normal", #Gaml
    "O31:Egyptian hieroglyphs:Normal", #Dalet
    "A28:Egyptian hieroglyphs:Normal", #Haw
    "G43:Egyptian hieroglyphs:Normal", #Waw
    "N34:Egyptian hieroglyphs:Normal", #Zayn
    "O6:Egyptian hieroglyphs:Normal", # Hasr
    "V28:Egyptian hieroglyphs:Normal", # Hayt
    "F35:Egyptian hieroglyphs:Normal", # Tab
    "D36:Egyptian hieroglyphs:Normal", # Yad
    "D46:Egyptian hieroglyphs:Normal", # Kap
    "U20:Egyptian hieroglyphs:Normal", # Lamd
    "N35:Egyptian hieroglyphs:Normal", # Maym
    "I10:Egyptian hieroglyphs:Normal", # Nahash
    "R11:Egyptian hieroglyphs:Normal", # Samk
    "D4:Egyptian hieroglyphs:Normal", # Ayn
    "V28:Egyptian hieroglyphs:Normal", # Gabi
    "D21:Egyptian hieroglyphs:Normal", # Pit
    "M22:Egyptian hieroglyphs:Normal", # Saday
    "O34:Egyptian hieroglyphs:Normal", # Qoba
    "D1:Egyptian hieroglyphs:Normal", # Rash
    "N5:Egyptian hieroglyphs:Normal", #Shin
    "M39:Egyptian hieroglyphs:Normal", #Shadeh
    "Z9:Egyptian hieroglyphs:Normal", #Taw
]

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
        default=alphabet_origins,
        help='One or more grapheme names to detail.'
    )
    args = parser.parse_args()
    session = db.default_session()
    
    for grapheme in args.graphemes:
        grapheme_name, script_name, character_form = grapheme.split(":")
        kar = session.query(
                db.writing.CharacterForm,
            ).join(
                db.writing.CharacterForm.character,
                db.writing.Character.grapheme,
                db.writing.Character.script,
                db.writing.CharacterForm.form_type,
            ).filter(
                db.writing.Grapheme.name == grapheme_name,
                db.writing.Script.name == script_name,
                db.writing.CharacterFormType.name == character_form,
            ).one()
        kar.print_children()

