"""„Das haben Sie gelernt“: Eingabe fuer die Flaechen-KI, ihre Antwort, die Seite im PDF und der Abschnitt im Text."""

from __future__ import annotations

import io
from dataclasses import replace
from datetime import date

import pypdf

from spaces.learning.huelle.gelernt import aus_antwort, fingerabdruck, gelerntdaten, hat_stoff
from spaces.learning.huelle.zusammenfassung import (
    NICHT_BEARBEITET, AufgabeZeile, Gelernt, Zusammenfassung, als_markdown, als_pdf, status_von,
)

ANTWORT = {"grader": "ki_flaeche", "kernpunkte": ["Ein Quick Win hat hohen Nutzen bei geringem Aufwand."],
           "sitzt": ["Die Reihenfolge der fünf Phasen."], "wiederholen": ["Risikoklassen: die Begründung fehlte."],
           "offen": ["Onepager"]}


def _zeilen() -> tuple[AufgabeZeile, ...]:
    return (
        AufgabeZeile(1, "Bringen Sie die Phasen in die richtige Reihenfolge.", "C → B → A", "Richtig. Gut gemacht.", None,
                     richtig=True, urteil="richtig", rueckmeldung="Richtig. Gut gemacht. Erst verstehen."),
        AufgabeZeile(2, "Ordnen Sie die Risikoklassen zu.", "1 → B", "Noch nicht richtig.", None, urteil="falsch"),
        AufgabeZeile(3, "Welcher Fall ist ein Quick Win?", "offen", "–", None, begonnen=True,
                     erklaerungen=tuple((f"Frage {i}?", f"Antwort {i}.") for i in range(1, 6))),
        AufgabeZeile(4, "Schreiben Sie einen Onepager.", "offen", "–", None),
        AufgabeZeile(5, "Nicht abgegeben.", NICHT_BEARBEITET, "–", None),
    )


def test_status_von_liegt_bei_der_zusammenfassung() -> None:
    assert [status_von(a) for a in _zeilen()] == ["richtig", "falsch", "arbeit", "offen", "leer"]


def test_gelerntdaten_genau_das_schema_der_lernflaeche() -> None:
    d = gelerntdaten("Kurs " + "x" * 300, _zeilen(), (("Quick Win", "71 %"),), (("Quick Win", "Hoher Nutzen. " * 100),))
    assert set(d) == {"kurs", "aufgaben", "begriffe", "notizen"} and len(d["kurs"]) == 200
    assert [a["stand"] for a in d["aufgaben"]] == ["richtig", "falsch", "in Arbeit", "offen", "offen"]
    eins, _, drei, _, fuenf = d["aufgaben"]
    assert set(eins) == {"nummer", "aufgabe", "stand", "ergebnis", "rueckmeldung", "fragen"}
    assert eins["rueckmeldung"] == "Richtig. Gut gemacht. Erst verstehen."  # die ganze, nicht die gekuerzte
    # Hoechstens drei Fragen an den Tutor, die juengsten.
    assert drei["fragen"] == [{"frage": f"Frage {i}?", "antwort": f"Antwort {i}."} for i in (3, 4, 5)]
    assert fuenf["ergebnis"] == "" and fuenf["rueckmeldung"] == ""  # „–“ und der feste Text sind kein Inhalt
    assert d["begriffe"] == [{"name": "Quick Win", "stand": "71 %"}]
    assert d["notizen"][0]["titel"] == "Quick Win" and len(d["notizen"][0]["text"]) == 600
    viele = gelerntdaten("K", _zeilen(), (), tuple((f"n{i}", "t") for i in range(40)))
    assert len(viele["notizen"]) == 30


def test_hat_stoff_nur_mit_bearbeiteter_aufgabe() -> None:
    assert hat_stoff(gelerntdaten("K", _zeilen(), (), ())) is True
    assert hat_stoff(gelerntdaten("K", _zeilen()[3:], (), ())) is False
    assert hat_stoff(gelerntdaten("K", (), (), ())) is False


def test_fingerabdruck_folgt_dem_stand() -> None:
    a = gelerntdaten("K", _zeilen(), (), ())
    assert fingerabdruck(a) == fingerabdruck(gelerntdaten("K", _zeilen(), (), ()))
    b = gelerntdaten("K", (replace(_zeilen()[0], urteil="teilweise"), *_zeilen()[1:]), (), ())
    assert fingerabdruck(a) != fingerabdruck(b)


def test_aus_antwort() -> None:
    g = aus_antwort(ANTWORT)
    assert g == Gelernt(("Ein Quick Win hat hohen Nutzen bei geringem Aufwand.",), ("Die Reihenfolge der fünf Phasen.",),
                        ("Risikoklassen: die Begründung fehlte.",), ("Onepager",))
    assert aus_antwort({**ANTWORT, "grader": "anders"}) is None
    assert aus_antwort({**ANTWORT, "kernpunkte": []}) is None
    assert aus_antwort({**ANTWORT, "sitzt": "kein Feld"}) is None
    assert aus_antwort(None) is None
    lang = aus_antwort({**ANTWORT, "kernpunkte": ["a" * 900, " ", 7, *["b"] * 9]})
    assert lang is not None and len(lang.kernpunkte) == 6 and len(lang.kernpunkte[0]) == 300


def _z(gelernt: Gelernt | None) -> Zusammenfassung:
    return Zusammenfassung("KI-Anwendungsfälle", date(2026, 11, 21), _zeilen(), (("Quick Win", "71 %"),), gelernt=gelernt)


def _alles(pdf: bytes) -> str:
    return " ".join(" ".join((s.extract_text() or "").split()) for s in pypdf.PdfReader(io.BytesIO(pdf)).pages)


def test_pdf_zeigt_die_seite_das_haben_sie_gelernt() -> None:
    text = _alles(als_pdf(_z(aus_antwort(ANTWORT))))
    for teil in ("Das haben Sie gelernt", "Ein Quick Win hat hohen Nutzen bei geringem Aufwand.", "DAS SITZT",
                 "Die Reihenfolge der fünf Phasen.", "DAS LOHNT SICH NOCH EINMAL", "Risikoklassen: die Begründung fehlte.",
                 "NOCH VOR IHNEN", "Onepager"):
        assert teil in text, teil
    assert text.index("Alle Aufgaben") < text.index("Das haben Sie gelernt") < text.index("Ihre bearbeiteten Aufgaben")


def test_pdf_ohne_gelernt_hat_die_seite_nicht_und_leere_listen_fallen_weg() -> None:
    assert "Das haben Sie gelernt" not in _alles(als_pdf(_z(None)))
    text = _alles(als_pdf(_z(Gelernt(("Nur ein Kernpunkt.",), (), (), ()))))
    assert "Nur ein Kernpunkt." in text
    assert "DAS SITZT" not in text and "NOCH VOR IHNEN" not in text


def test_markdown_traegt_den_abschnitt() -> None:
    md = als_markdown(_z(aus_antwort(ANTWORT)))
    assert "## Das haben Sie gelernt\n- Ein Quick Win hat hohen Nutzen bei geringem Aufwand.\n" in md
    assert "### Das sitzt\n- Die Reihenfolge der fünf Phasen.\n" in md
    assert "### Noch vor Ihnen\n- Onepager\n" in md
    assert "Das haben Sie gelernt" not in als_markdown(_z(None))
