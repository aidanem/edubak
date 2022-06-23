
import database as db
session = db.default_session()

for grapheme in session.query(db.writing.Grapheme).all():
    for character in grapheme.characters:
        for form in character.forms:
            if hasattr(form, "unicode") and form.unicode:
                print(f"{grapheme.name} ({form.form_type.name}) in {character.script.name}: {form.unicode.glyph} ({form.unicode.hex_point})")
            else:
                print(f"{grapheme.name} ({form.form_type.name}) in {character.script.name} (No Unicode)")