"""Die Zusammenfassung als Seite im Browser: dieselben Inhalte wie das PDF, das Canvas in einem Rahmen zum Verschieben."""

from __future__ import annotations

from datetime import date

from spaces.learning.huelle.zusammenfassung import AufgabeZeile, Gelernt, Kursrueckmeldung, Zusammenfassung
from spaces.learning.huelle.zusammenfassung_html import als_html


def _z() -> Zusammenfassung:
    return Zusammenfassung(
        "KI-Anwendungsfälle <finden>", date(2026, 11, 21),
        (
            AufgabeZeile(1, "Bringen Sie die Phasen in die Reihenfolge.", "C → B → A", "Richtig. Gut gemacht.", b"png",
                         ("solve",), True, urteil="richtig", versuche=2, erstes_urteil="incorrect"),
            AufgabeZeile(2, "Welcher Fall ist ein <b>Quick Win</b>?", "offen", "–", None, begonnen=True,
                         erklaerungen=(("Warum?", "Weil der Nutzen hoch ist."),)),
            AufgabeZeile(3, "Schreiben Sie einen Onepager.", "offen", "–", None),
        ),
        (("Beratungsphasen", "71 %"), ("Quick Win", "noch offen")),
        Kursrueckmeldung("Stark.", "Lücke.", "Üben.", "ki_flaeche"),
        (("Quick Win", "Hoher Nutzen, wenig Aufwand."),),
        Gelernt(("Erst verstehen, dann bewerten.",), ("Die Phasen.",), (), ("Onepager",)),
    )


def _seite() -> str:
    return als_html(_z(), pdf_adresse="zusammenfassung.pdf", bilder={1: ("flaeche/1", 2400)})


def test_seite_traegt_alle_teile_der_zusammenfassung() -> None:
    html = _seite()
    assert html.startswith("<!doctype html>") and '<html lang="de">' in html
    for teil in ("Zusammenfassung vom 21.11.2026", "1 von 3 Aufgaben bearbeitet, 1 davon richtig, 1 weitere begonnen.",
                 "Das haben Sie gelernt", "Erst verstehen, dann bewerten.", "Das sitzt", "Noch vor Ihnen", "Onepager",
                 "Kursrückmeldung", "Stark.", "Alle Aufgaben", "Ihre bearbeiteten Aufgaben", "Aufgabe 1", "C → B → A",
                 "Richtig. Gut gemacht.", "Ihre Fragen an den Tutor", "Weil der Nutzen hoch ist.", "Ihre Notizen",
                 "Hoher Nutzen, wenig Aufwand.", "Begriffe", "71 %", "In Arbeit", "KI genutzt: Lösen"):
        assert teil in html, teil
    assert html.count("<article") == 2  # nur bearbeitete Aufgaben stehen ausfuehrlich da
    assert 'href="zusammenfassung.pdf"' in html and "Als PDF speichern" in html


def test_canvas_steht_im_rahmen_zum_verschieben() -> None:
    html = _seite()
    assert '<div class="flaeche" tabindex="0"' in html
    assert '<img src="flaeche/1" width="2400" alt="Ihre Fläche zu Aufgabe 1" loading="lazy">' in html
    assert html.count("<img") == 1  # Aufgabe 2 hat kein Bild
    assert "overflow: auto" in html and "max-width: none" in html


def test_fremder_text_wird_maskiert_und_die_seite_braucht_kein_skript() -> None:
    html = _seite()
    assert "&lt;finden&gt;" in html and "<finden>" not in html
    assert "&lt;b&gt;Quick Win&lt;/b&gt;" in html and "<b>Quick Win</b>" not in html
    assert "<script" not in html and "javascript:" not in html
    boese = als_html(_z(), pdf_adresse='x"><script>', bilder={1: ('y" onerror="z', 10)})
    assert "<script" not in boese and 'onerror="z' not in boese


def test_ohne_gelernt_rueckmeldung_und_notizen_fehlen_die_abschnitte() -> None:
    z = Zusammenfassung("Kurs", date(2026, 11, 21), (AufgabeZeile(1, "Frage.", "offen", "–", None),), ())
    html = als_html(z, pdf_adresse="p", bilder={})
    for teil in ("Das haben Sie gelernt", "Kursrückmeldung", "Ihre Notizen", "Ihre bearbeiteten Aufgaben", "<article"):
        assert teil not in html, teil
    assert "0 von 1 Aufgaben bearbeitet" in html and "Noch keine Begriffe." in html
