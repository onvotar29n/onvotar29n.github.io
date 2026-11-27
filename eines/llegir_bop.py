#!/usr/bin/env python3
"""Converteix el text del PDF del BOP (locals i meses) en una llista de files."""
import re, sys, json

PAT = re.compile(r'^08 (\d{3}) (.+?) (\d{1,2}) (\d{1,3})(?: (\d{1,2}))? ([A-Z]) ([A-ZÑ]) ([A-ZÑ]) (8\d{7}) (.*)$')

TIPUS = ["C/", "C", "CARRE", "AV", "AVGDA", "CRA", "PSAJE", "JDINS", "URBAT", "TRVA", "PG", "PL", "PZ", "CTRA", "TRRNT", "RIERA", "RBLA", "RONDA", "PTGE", "TRAV", "G.V.", "VIA",
         "CAMI", "CAMÍ", "BDA", "URB", "PLCET", "PSTGE", "CR", "RAMBLA", "PARC", "VEINAT", "VEÏNAT",
         "AVDA", "TRV", "ESC", "COSTA", "PJE", "PUJADA", "CTRA.", "CRTA", "RDA", "PTGE.", "JARD", "TORRENT",
         "CARRER", "TRAVESSIA", "TRS", "RAVAL", "BAIXADA", "PASSEIG", "PLAÇA", "AVINGUDA", "CAMÍ", "POLIG", "PG.", "CMI"]
SECUNDARIS = ["LLOC", "MASIA", "GRUP", "JDIN", "MAS", "LG", "LUGAR", "POL", "SECTOR", "DS", "DISEM", "NUCLI", "ZONA", "ACCES", "ACCÉS", "BLOC", "VEÏNAT", "VEINAT", "BARRI"]
TRE = "|".join(re.escape(t) for t in sorted(TIPUS, key=len, reverse=True))
# nom + ' ' + TIPUS + ' ' + via + ' ' + (num|S/N) + ', resta'
SPLIT = re.compile(r'^(?P<nom>.+?) (?P<adr>(?:' + TRE + r') .+?(?: \d+(?: ?[A-Z]{1,3})?| S/N| SN| KM[ .\d,]*)?)(?P<resta>, .*)$')


def parse(path):
    files = []
    for l in open(path, encoding="utf-8"):
        l = l.rstrip()
        m = PAT.match(l)
        if not m:
            continue
        mun, nom_mun, dist, sec, sub, mesa, li, lf, codi, resta = m.groups()
        files.append(dict(mun=mun, municipi=nom_mun, dist=int(dist), sec=int(sec), sub=int(sub) if sub else 0,
                          mesa=mesa, ini=li, fi=lf, codi=codi, local_brut=resta))
    return files


def separar(brut):
    """'ESCOLA X C MAJOR 3, BARRI, 08630 ABRERA, BARCELONA' -> ('ESCOLA X', 'C MAJOR 3', 'BARRI', '08630', 'ABRERA')"""
    t = re.sub(r",\s*BARCELONA\s*$", "", brut.strip())
    m = re.search(r",\s*(\d{5})\s+(.+)$", t)
    cp, pob = (m.group(1), m.group(2)) if m else ("", "")
    if m:
        t = t[:m.start()]
    parts = t.split(", ")
    cap = parts[0]
    extra = ", ".join(parts[1:])
    # nom i adreça: tria la primera paraula-tipus que deixi un nom no buit
    best = None
    # prova els tipus per ordre de freqüència (C, AV, PG...) i, per a cada un, la primera aparició vàlida
    for t in TIPUS + SECUNDARIS:
        for mt in re.finditer(r"(?<= )" + re.escape(t) + r" ", cap):
            i = mt.start()
            nom, adr = cap[:i].strip(), cap[i:].strip()
            if nom and re.search(r"(\d+\s?[A-Z]{0,3}|S/N|SN|KM[\s\d.,]*)$", adr):
                best = (nom, adr)
                break
        if best:
            break
    if not best:
        # adreça sense tipus reconegut: nom = tot fins al darrer bloc amb número
        mm = re.match(r"^(.*?)\s+(\S.*\s(?:\d+\s?[A-Z]?|S/N))$", cap)
        best = (cap, "") if not mm else (mm.group(1), mm.group(2))
    return best[0], best[1], extra, cp, pob


if __name__ == "__main__":
    files = parse(sys.argv[1])
    for f in files:
        f["local"], f["adreca"], f["zona"], f["cp"], f["poblacio"] = separar(f["local_brut"])
    json.dump(files, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
    print(len(files), "files")
