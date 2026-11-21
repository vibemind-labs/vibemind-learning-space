"""Die Zusammenfassung als Seite im Browser.

Dieselben Inhalte wie das PDF (`zusammenfassung_pdf.py`), aber zum Durchsehen: das Canvas jeder Aufgabe steht in
einem Rahmen in seiner Groesse und laesst sich darin verschieben. Ein PDF kann das nicht; dort ist das Bild auf
die Seitenbreite verkleinert.

Rein wie `zusammenfassung.py`: nimmt eine fertige `Zusammenfassung`, liest nichts. Die Seite braucht kein Skript
und laedt nichts Fremdes; aller Text aus Kurs, Antworten und KI wird maskiert.
"""

from __future__ import annotations

from collections.abc import Mapping
from html import escape

from .zusammenfassung import (
    AufgabeZeile, Zusammenfassung, _einzeilig, erster_satz, ki_genutzt, ohne_latex, rueckmeldung_teile, status_von,
)

# Status einer Aufgabe: Wort und CSS-Klasse (Farben wie im PDF und in huelle.css).
STATUS = {
    "richtig": ("Richtig", "gruen"), "teilweise": ("Teilweise richtig", "gelb"), "falsch": ("Noch nicht richtig", "rot"),
    "leer": ("Nicht bearbeitet", "grau"), "arbeit": ("In Arbeit", "blau"), "offen": ("Offen", "grau"),
}
MIT_KARTE = frozenset(STATUS) - {"offen"}

STIL = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; background: #fff; color: #17191c; font: 16px/1.5 system-ui, "Segoe UI", sans-serif; }
main { max-width: 62rem; margin: 0 auto; padding: 1.5rem 1.25rem 4rem; }
h1 { font-size: 1.9rem; line-height: 1.2; margin: 0 0 .25rem; }
h2 { font-size: 1.25rem; margin: 2.25rem 0 .75rem; }
h3 { font-size: 1.1rem; margin: 0; }
p { margin: 0 0 .5rem; }
.unter { color: #55524a; margin-bottom: 1rem; }
.kopf { display: flex; flex-wrap: wrap; gap: 1rem; align-items: flex-start; justify-content: space-between; }
.knopf { display: inline-flex; align-items: center; min-height: 2.5rem; padding: 0 .9rem; border: 1px solid #c9c6bc;
  border-radius: .5rem; background: #fff; color: inherit; font-weight: 600; text-decoration: none; }
.knopf:hover, .knopf:focus-visible { border-color: #17191c; }
.zahlen { display: grid; grid-template-columns: repeat(4, 1fr); gap: .75rem; margin: 1rem 0 .5rem; }
.zahl { border-radius: .5rem; padding: .6rem .5rem; text-align: center; }
.zahl b { display: block; font-size: 1.7rem; line-height: 1.2; }
.zahl span { font-size: .85rem; color: #55524a; }
.gruen { background: #e7f3eb; color: #1d7a3e; } .gelb { background: #fff6dc; color: #8a5a00; }
.rot { background: #fdecea; color: #8a1c13; } .grau { background: #f0eee8; color: #55524a; }
.blau { background: #eef3f8; color: #24507d; }
.pille { display: inline-block; border-radius: 1rem; padding: .1rem .65rem; font-size: .8rem; font-weight: 700; white-space: nowrap; }
.kasten, article { background: #f6f5f1; border-radius: .5rem; padding: 1rem 1.25rem; }
.kasten ul { margin: 0; padding-left: 1.2rem; } .kasten li { margin: .35rem 0; font-size: 1.05rem; }
article { margin: 0 0 1.25rem; }
article header { display: flex; gap: 1rem; align-items: center; justify-content: space-between; margin-bottom: .75rem; }
.marke { font-size: .72rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; color: #55524a; margin: .9rem 0 .15rem; }
ul.liste { margin: 0 0 .5rem; padding-left: 1.2rem; }
table { border-collapse: collapse; width: 100%; font-size: .92rem; }
th { text-align: left; font-size: .72rem; letter-spacing: .04em; text-transform: uppercase; color: #55524a; border-bottom: 2px solid #17191c; padding: .35rem .5rem .35rem 0; }
td { vertical-align: top; border-bottom: 1px solid #c9c6bc; padding: .4rem .5rem .4rem 0; }
.flaeche { overflow: auto; max-height: 80vh; background: #fff; border: 1px solid #c9c6bc; border-radius: .35rem; }
.flaeche:focus-visible { outline: 2px solid #24507d; outline-offset: 2px; }
.flaeche img { display: block; max-width: none; height: auto; }
.hinweis, .fuss { font-size: .85rem; color: #55524a; }
.frage { font-weight: 700; margin-top: .5rem; }
.balken { display: inline-block; width: 12rem; max-width: 40vw; height: .5rem; border-radius: .25rem; background: #e3e0d6; vertical-align: middle; }
.balken i { display: block; height: 100%; border-radius: .25rem; background: #1d7a3e; }
@media (max-width: 40rem) { .zahlen { grid-template-columns: repeat(2, 1fr); } }
@media print { .knopf { display: none; } .flaeche { max-height: none; overflow: visible; } .flaeche img { max-width: 100%; } }
"""


def _x(text: object) -> str:
    """Klartext fuer die Seite: Formeln umgeschrieben, einzeilig, HTML-Zeichen maskiert."""
    return escape(_einzeilig(ohne_latex(str(text))), quote=True)


def _pille(status: str) -> str:
    wort, klasse = STATUS[status]
    return f'<span class="pille {klasse}">{wort}</span>'


def _liste(saetze: tuple[str, ...] | list[str]) -> str:
    return '<ul class="liste">' + "".join(f"<li>{_x(s)}</li>" for s in saetze) + "</ul>"


def _kopf(z: Zusammenfassung, zaehler: dict[str, int], pdf_adresse: str) -> list[str]:
    gesamt = len(z.aufgaben)
    richtig, teilweise = zaehler["richtig"], zaehler["teilweise"]
    falsch, begonnen = zaehler["falsch"] + zaehler["leer"], zaehler["arbeit"]
    offen = zaehler["offen"] + begonnen
    satz = (f"{gesamt - offen} von {gesamt} Aufgaben bearbeitet, {richtig} davon richtig"
            + (f", {begonnen} weitere begonnen." if begonnen else "."))
    kacheln = "".join(f'<div class="zahl {klasse}"><b>{zahl}</b><span>{wort}</span></div>' for zahl, wort, klasse in (
        (richtig, "richtig", "gruen"), (teilweise, "teilweise richtig", "gelb"),
        (falsch, "noch nicht richtig", "rot"), (offen, "noch offen", "grau")))
    return [
        '<div class="kopf"><div>', f"<h1>{_x(z.kurs)}</h1>",
        f'<p class="unter">Zusammenfassung vom {z.datum:%d.%m.%Y}</p></div>',
        f'<a class="knopf" href="{escape(pdf_adresse, quote=True)}" download>Als PDF speichern</a></div>',
        f'<div class="zahlen">{kacheln}</div>', f'<p class="hinweis">{satz}</p>',
    ]


def _gelernt(z: Zusammenfassung) -> list[str]:
    g = z.gelernt
    if g is None or not g.kernpunkte:
        return []
    teile = ["<h2>Das haben Sie gelernt</h2>",
             '<div class="kasten"><ul>' + "".join(f"<li>{_x(p)}</li>" for p in g.kernpunkte) + "</ul></div>"]
    for titel, liste in g.abschnitte():
        teile += [f'<p class="marke">{escape(titel)}</p>', _liste(liste)]
    return teile


def _kursrueckmeldung(z: Zusammenfassung) -> list[str]:
    teile = ["<h2>Kursrückmeldung</h2>"] if z.rueckmeldung is not None else []
    for titel, text in z.abschnitte():
        teile += [f'<p class="marke">{escape(titel)}</p>', f"<p>{_x(text)}</p>"]
    return teile


def _tabelle(z: Zusammenfassung) -> list[str]:
    zeilen = []
    for a in z.aufgaben:
        s = status_von(a)
        ergebnis = "" if s in ("offen", "arbeit") else _x(a.ergebnis)
        zeilen.append(f"<tr><td>{int(a.nummer)}</td><td>{escape(erster_satz(a.text), quote=True)}</td>"
                      f"<td>{ergebnis}</td><td>{_pille(s)}</td></tr>")
    return ["<h2>Alle Aufgaben</h2>",
            "<table><thead><tr><th>Nr.</th><th>Aufgabe</th><th>Ihr Ergebnis</th><th>Stand</th></tr></thead><tbody>",
            *zeilen, "</tbody></table>"]


def _karte(a: AufgabeZeile, bild: tuple[str, int] | None) -> str:
    s = status_von(a)
    teile = [f'<article aria-labelledby="aufgabe-{int(a.nummer)}"><header><h3 id="aufgabe-{int(a.nummer)}">'
             f"Aufgabe {int(a.nummer)}</h3>{_pille(s)}</header>",
             '<p class="marke">Aufgabe</p>', f"<p>{_x(a.text)}</p>"]
    if s != "arbeit":  # begonnen, aber nichts abgegeben: es gibt noch kein Ergebnis
        teile += ['<p class="marke">Ihr Ergebnis</p>', f"<p>{_x(a.ergebnis)}</p>"]
    einleitung, punkte = rueckmeldung_teile(a.rueckmeldung or a.kernaussage)
    if einleitung:
        teile += ['<p class="marke">Rückmeldung</p>', f"<p>{escape(einleitung, quote=True)}</p>"]
        if punkte:
            teile.append('<ul class="liste">' + "".join(f"<li>{escape(p, quote=True)}</li>" for p in punkte) + "</ul>")
    if bild is not None:
        adresse, breite = bild
        teile += ['<p class="marke">Ihre Fläche</p>',
                  f'<div class="flaeche" tabindex="0" role="group" aria-label="Ihre Fläche zu Aufgabe {int(a.nummer)}, '
                  'zum Verschieben">'
                  f'<img src="{escape(adresse, quote=True)}" width="{int(breite)}" '
                  f'alt="Ihre Fläche zu Aufgabe {int(a.nummer)}" loading="lazy"></div>',
                  '<p class="hinweis">Im Rahmen können Sie die Fläche mit der Maus, dem Finger oder den Pfeiltasten '
                  "verschieben.</p>"]
    if a.erklaerungen:
        teile.append('<p class="marke">Ihre Fragen an den Tutor</p>')
        for frage, antwort in a.erklaerungen:
            teile += [f'<p class="frage">{_x(frage)}</p>', f"<p>{_x(antwort)}</p>"]
    fuss = " · ".join(t for t in (a.versuche_zeile, ki_genutzt(a.ki_schritte)) if t)
    teile.append(f'<p class="fuss">{escape(fuss, quote=True)}</p></article>')
    return "".join(teile)


def _karten(z: Zusammenfassung, bilder: Mapping[int, tuple[str, int]]) -> list[str]:
    bearbeitet = [a for a in z.aufgaben if status_von(a) in MIT_KARTE]
    if not bearbeitet:
        return []
    return ["<h2>Ihre bearbeiteten Aufgaben</h2>", *(_karte(a, bilder.get(a.nummer)) for a in bearbeitet)]


def _notizen(z: Zusammenfassung) -> list[str]:
    if not z.notizen:
        return []
    teile = ["<h2>Ihre Notizen</h2>"]
    for titel, text in z.notizen:
        teile.append(f'<p class="frage">{_x(titel) or "Notiz"}</p>')
        if text.strip():
            teile.append(f"<p>{_x(text)}</p>")
    return teile


def _begriffe(z: Zusammenfassung) -> list[str]:
    teile = ["<h2>Begriffe</h2>"]
    if not z.begriffe:
        return [*teile, '<p class="hinweis">Noch keine Begriffe.</p>']
    zeilen = []
    for titel, stand in z.begriffe:
        wert = str(stand).strip().removesuffix("%").strip()
        balken = (f'<span class="balken"><i style="width: {min(100, int(wert))}%"></i></span>'
                  if wert.isdigit() else "")
        zeilen.append(f"<tr><td>{_x(titel)}</td><td>{balken}</td><td>{_x(stand)}</td></tr>")
    return [*teile, "<table><tbody>", *zeilen, "</tbody></table>"]


def als_html(z: Zusammenfassung, *, pdf_adresse: str, bilder: Mapping[int, tuple[str, int]]) -> str:
    """Die ganze Seite. `bilder`: Aufgabennummer -> (Adresse des Bildes der Flaeche, Anzeigebreite in CSS-Pixeln);
    Aufgaben ohne Eintrag haben keinen Rahmen. `pdf_adresse`: Link „Als PDF speichern“."""
    zaehler = {name: 0 for name in STATUS}
    for a in z.aufgaben:
        zaehler[status_von(a)] += 1
    koerper = [*_kopf(z, zaehler, pdf_adresse), *_gelernt(z), *_tabelle(z), *_kursrueckmeldung(z), *_karten(z, bilder),
               *_notizen(z), *_begriffe(z)]
    return ("<!doctype html>\n"
            '<html lang="de"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{_x(z.kurs)} – Zusammenfassung</title><style>{STIL}</style></head>"
            f"<body><main>{''.join(koerper)}</main></body></html>\n")
