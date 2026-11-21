"""„Das haben Sie gelernt“ in der Zusammenfassung: Eingabe fuer die Flaechen-KI und ihre Antwort.

Rein: liest nichts bei Learning, PenEcho oder der Lernflaeche. Die Eingabe enthaelt nur, was die Person ohnehin
sieht (Aufgabentext, ihr Ergebnis, die Rueckmeldung, ihre Fragen an den Tutor samt Antwort, ihre Notizen, die
Begriffe), nie Musterloesung oder Rubrik. Die Lernflaeche prueft sie mit `exactKeys` (`lern-gelernt.js`); darum
entsteht hier genau dieses Schema, schon auf ihre Grenzen gekuerzt (UTF-16-Codeeinheiten, `kursrueckmeldung._kurz`).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from .kursrueckmeldung import GRADER, _abschneiden, _kurz
from .zusammenfassung import AufgabeZeile, Gelernt, status_von

KURS_ZEICHEN = 200
AUFGABE_ZEICHEN = 600
ERGEBNIS_ZEICHEN = 400
RUECKMELDUNG_ZEICHEN = 2000
FRAGE_ZEICHEN = 300
ANTWORT_ZEICHEN = 1200
FRAGEN_HOECHSTENS = 3
AUFGABEN_HOECHSTENS = 100
BEGRIFFE_HOECHSTENS = 100
NAME_ZEICHEN = 200
STAND_ZEICHEN = 40
NOTIZEN_HOECHSTENS = 30
NOTIZ_TITEL_ZEICHEN = 200
NOTIZ_TEXT_ZEICHEN = 600
# Status der Zusammenfassung -> Wort des Schemas. „leer“ (gebucht ohne Abgabe) ist nicht bearbeitet: „offen“.
STAND = {"richtig": "richtig", "teilweise": "teilweise", "falsch": "falsch", "arbeit": "in Arbeit",
         "leer": "offen", "offen": "offen"}
# Listen der Antwort: (hoechstens, Zeichen je Satz), wie `lern-gelernt.js`.
LISTEN = {"kernpunkte": (6, 300), "sitzt": (5, 200), "wiederholen": (5, 200), "offen": (6, 120)}


def gelerntdaten(kurs: str, zeilen: Sequence[AufgabeZeile], begriffe: Sequence[tuple[str, str]],
                 notizen: Sequence[tuple[str, str]]) -> dict[str, Any]:
    """Eingabe des Endpunkts `gelernt`: `{kurs, aufgaben: [{nummer, aufgabe, stand, ergebnis, rueckmeldung,
    fragen: [{frage, antwort}]}], begriffe: [{name, stand}], notizen: [{titel, text}]}`."""
    aufgaben = []
    for z in zeilen:
        if not isinstance(z.nummer, int) or isinstance(z.nummer, bool) or z.nummer < 1:
            continue
        stand = STAND[status_von(z)]
        bearbeitet = stand not in ("offen", "in Arbeit")
        aufgaben.append({
            "nummer": int(z.nummer),
            "aufgabe": _kurz(z.text, AUFGABE_ZEICHEN),
            "stand": stand,
            "ergebnis": _kurz(z.ergebnis, ERGEBNIS_ZEICHEN) if bearbeitet else "",
            "rueckmeldung": _kurz(z.rueckmeldung or z.kernaussage, RUECKMELDUNG_ZEICHEN) if bearbeitet else "",
            "fragen": [{"frage": _kurz(f, FRAGE_ZEICHEN), "antwort": _kurz(a, ANTWORT_ZEICHEN)}
                       for f, a in z.erklaerungen[-FRAGEN_HOECHSTENS:]],
        })
    return {
        "kurs": _kurz(kurs, KURS_ZEICHEN),
        "aufgaben": aufgaben[:AUFGABEN_HOECHSTENS],
        "begriffe": [{"name": _kurz(n, NAME_ZEICHEN), "stand": _kurz(s, STAND_ZEICHEN)}
                     for n, s in list(begriffe)[:BEGRIFFE_HOECHSTENS]],
        "notizen": [{"titel": _kurz(t, NOTIZ_TITEL_ZEICHEN), "text": _kurz(x, NOTIZ_TEXT_ZEICHEN)}
                    for t, x in list(notizen)[:NOTIZEN_HOECHSTENS]],
    }


def hat_stoff(daten: Mapping[str, Any]) -> bool:
    """Gibt es etwas Gelerntes? Mindestens eine Aufgabe, die nicht „offen“ ist; sonst wird nicht gefragt."""
    return any(a.get("stand") != "offen" for a in daten.get("aufgaben") or [])


def fingerabdruck(daten: Mapping[str, Any]) -> str:
    """Kennzeichen des Stands: dieselbe Eingabe ergibt dieselbe Antwort aus dem Speicher, eine neue Abgabe,
    Frage oder Notiz fragt die Flaechen-KI neu."""
    return hashlib.sha256(json.dumps(daten, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _liste(wert: object, hoechstens: int, zeichen: int) -> tuple[str, ...] | None:
    if not isinstance(wert, (list, tuple)):
        return None
    saetze = [" ".join(w.split()) for w in wert if isinstance(w, str) and w.strip()]
    return tuple(_abschneiden(s, zeichen) for s in saetze[:hoechstens])


def aus_antwort(wert: Mapping[str, Any] | None) -> Gelernt | None:
    """Antwort der Flaechen-KI (oder der gespeicherte Eintrag): nur mit `grader == "ki_flaeche"`, vier Listen und
    mindestens einem Kernpunkt, sonst None."""
    if not isinstance(wert, Mapping) or wert.get("grader") != GRADER:
        return None
    listen = {name: _liste(wert.get(name), *grenze) for name, grenze in LISTEN.items()}
    if any(liste is None for liste in listen.values()) or not listen["kernpunkte"]:
        return None
    return Gelernt(**listen)  # type: ignore[arg-type]


def als_eintrag(g: Gelernt, stand: str) -> dict[str, Any]:
    """Form in `gelernt.json`: die Antwort samt Kennzeichen des Stands; `aus_antwort` liest sie wieder."""
    return {"grader": GRADER, "stand": stand, "kernpunkte": list(g.kernpunkte), "sitzt": list(g.sitzt),
            "wiederholen": list(g.wiederholen), "offen": list(g.offen)}
