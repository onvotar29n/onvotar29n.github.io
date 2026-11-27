#!/usr/bin/env python3
"""Genera web/dades.json per al cercador "On voto?".

Entrades:
  - Fitxers TRAM i VIAS del Callejero del Censo Electoral de l'INE (província 08)
  - Excel(s) de meses per districte (columnes: Districte, Secció, Subsecció, Mesa,
    Lletra inici, Lletra final, Codi local, Local electoral, Adreça)
  - locals.json: nom i adreça nets de cada local (codi -> [nom, adreça, CP])

Ús:
  python3 construir_dades.py TRAM.P08... VIAS.P08... meses1.xlsx [meses2.xlsx ...]
"""
import json, sys, os, re
import openpyxl

AQUI = os.path.dirname(os.path.abspath(__file__))
MUN = "08019"  # Barcelona

DISTRICTES = {1: "Ciutat Vella", 2: "Eixample", 3: "Sants-Montjuïc", 4: "Les Corts",
              5: "Sarrià-Sant Gervasi", 6: "Gràcia", 7: "Horta-Guinardó", 8: "Nou Barris",
              9: "Sant Andreu", 10: "Sant Martí"}

TIPUS = {"C": "Carrer", "AV": "Avinguda", "PG": "Passeig", "PL": "Plaça", "PTGE": "Passatge",
         "PTG": "Passatge", "TRAV": "Travessera", "RBLA": "Rambla", "RBL": "Rambla",
         "RDA": "Ronda", "RON": "Ronda", "VIA": "Via", "CTRA": "Carretera", "CTR": "Carretera",
         "CAMI": "Camí", "CAM": "Camí", "BDA": "Baixada", "BAIX": "Baixada", "JARD": "Jardins",
         "JAR": "Jardins", "PLA": "Pla", "PLTA": "Placeta", "PLC": "Placeta", "RIER": "Riera",
         "RIE": "Riera", "TRAS": "Travessia", "TRS": "Travessia", "ESC": "Escales", "COST": "Costa",
         "COS": "Costa", "TORR": "Torrent", "TRR": "Torrent", "MOLL": "Moll", "MOL": "Moll",
         "G.V.": "Gran Via", "G.V": "Gran Via", "GV": "Gran Via", "PARC": "Parc", "PAR": "Parc",
         "PUJ": "Pujada", "ARC": "Arc", "AUTO": "Autopista", "BARRI": "Barri", "BAR": "Barri",
         "CRO": "Cruïlla", "PAS": "Passeig", "PTJ": "Passatge", "PDI": "Pas", "DRE": "Drecera",
         "GRU": "Grup", "JDI": "Jardí", "MUE": "Moll", "POR": "Portal", "VCT": "Viaducte", "TRRNT": "Torrent", "PLCET": "Placeta", "ESCA": "Escales",
         "TRSSI": "Travessia", "PDIS": "Pas", "MUELL": "Moll", "VCTO": "Viaducte", "DRERA": "Drecera",
         "GRUP": "Grup", "GRAN": "Gran Via", "PORT": "Port", "ESCU": "Escullera"}

PETITES = {"i", "de", "del", "dels", "la", "les", "el", "els", "a", "y", "d", "l", "en", "na", "sa"}


def bonic(nom):
    """MUNTANER -> Muntaner ; ELISA MORAGAS I BADIA (D') -> Elisa Moragas i Badia"""
    nom = re.sub(r"\s*\([^)]*\)\s*$", "", nom.strip())
    paraules = nom.lower().split()
    out = []
    for i, w in enumerate(paraules):
        if i > 0 and w in PETITES:
            out.append(w)
        else:
            out.append("-".join(p[:1].upper() + p[1:] for p in w.split("-")))
    s = " ".join(w.upper() if re.fullmatch(r"[ivxl]+", w.lower()) and w not in PETITES else w for w in out)
    s = re.sub(r"\b([DdLl])'(\w)", lambda m: m.group(1).lower() + "'" + m.group(2).upper(), s)
    return s[:1].upper() + s[1:]


ACRONIMS = {"OAC", "CEIP", "IES", "CAP", "EMAV", "UB", "CESIRE", "EBM", "CC", "SES", "IMEB", "UPC",
            "CF", "CE", "CEM", "UPF", "CIRD", "ONCE", "SAD", "CSS", "FAD", "AV", "AAVV", "UIB", "CCOO", "UGT"}
TIPUS_ADR = {"C": "Carrer", "PL": "Plaça", "AV": "Avinguda", "PG": "Passeig", "RONDA": "Ronda",
             "PTGE": "Passatge", "RBLA": "Rambla", "RIERA": "Riera", "CTRA": "Carretera", "VIA": "Via",
             "TRAV": "Travessera", "G.V.": "Gran Via de les", "BDA": "Baixada", "CAMI": "Camí"}
PARTICULES = {"(L')": "de l'", "(D')": "d'", "(DE)": "de", "(DE LA)": "de la", "(DEL)": "del",
              "(DELS)": "dels", "(LA)": "de la", "(LES)": "de les", "(EL)": "del", "(ELS)": "dels",
              "(DE LES)": "de les"}


def titol(txt):
    out = []
    for i, w in enumerate(txt.split()):
        lw = w.lower()
        if w.strip(".,()") in ACRONIMS:
            out.append(w)
        elif i > 0 and lw in PETITES:
            out.append(lw)
        elif re.fullmatch(r"[ivxl]+", lw.strip(".,")):
            out.append(w.upper())
        else:
            pre = re.match(r"^[(\"«]*", lw).group(0)
            core = lw[len(pre):]
            core = "-".join(x[:1].upper() + x[1:] for x in core.split("-"))
            core = re.sub(r"^([DdLl])'(\w)", lambda m: (m.group(1).lower() if i > 0 else m.group(1).upper()) + "'" + m.group(2).upper(), core)
            core = re.sub(r"\b(\w)\.(\w)\.", lambda m: m.group(1).upper() + "." + m.group(2).upper() + ".", core)
            out.append(pre + core)
    s = " ".join(out).replace("l.l", "l·l").replace("L.l", "L·l")
    s = re.sub(r"\bla Salle\b", "La Salle", s).replace("Jaume i (", "Jaume I (")
    return s


def netejar_local(nom, adr):
    """('ESCOLA X TRAV GRACIA (DE) 55,', '08006 BARCELONA') -> ['Escola X', 'Travessera de Gracia, 55', '08006']"""
    nom, adr = nom.strip(), adr.strip()
    if re.fullmatch(r"\d{5} BARCELONA", adr):
        m = re.search(r"\s(" + "|".join(re.escape(t) for t in TIPUS_ADR) + r")\s(.+?),?$", nom)
        if m:
            adr = f"{m.group(1)} {m.group(2).rstrip(',')}, {adr}"
            nom = nom[:m.start()].strip()
    m = re.match(r"^(\S+)\s+(.*?)\s*(\([^)]*\))?\s+(\d+\s*[A-Z]?)\s*,\s*(\d{5})", adr)
    if not m:
        return [titol(nom), titol(adr), ""]
    tipus, carrer, part, num, cp = m.groups()
    t = TIPUS_ADR.get(tipus, tipus.title())
    part = PARTICULES.get(part or "", "")
    nomc = titol(carrer)
    if part.endswith("'"):
        via = f"{t} {part}{nomc}"
    elif part:
        via = f"{t} {part} {nomc}"
    else:
        via = f"{t} {nomc}"
    via = {"Travessera Dalt": "Travessera de Dalt", "Travessera Corts": "Travessera de les Corts"}.get(via, via)
    return [titol(nom), f"{via}, {num.strip()}", cp]


def llegir(path):
    with open(path, encoding="latin-1") as f:
        for linia in f:
            yield linia.rstrip("\r\n")


def main():
    tram, vias, *excels = sys.argv[1:]
    # Vies de Barcelona
    noms = {}
    for l in llegir(vias):
        if not l.startswith(MUN):
            continue
        cvia = l[5:10]
        tipus = l[52:57].strip()
        llarg = l[57:107].strip() or l[10:40].strip()
        t = TIPUS.get(tipus, tipus.title()).lower()
        part = re.search(r"\(([^)]*)\)\s*$", llarg)
        part = (" " + part.group(1).lower()) if part else ""
        part = part.replace("' ", "'")
        part = {" l'": " de l'", " la": " de la", " les": " de les", " el": " del", " els": " dels"}.get(part, part)
        T = t[:1].upper() + t[1:]
        sep = "" if part.endswith("'") else " "
        noms[cvia] = f"{T}{part}{sep}{bonic(llarg)}" if t else bonic(llarg)
        noms[cvia] = {"Gran via Corts Catalanes": "Gran Via de les Corts Catalanes",
                      "Gran via Carles III": "Gran Via de Carles III"}.get(noms[cvia], noms[cvia])

    # Trams: via -> [[ini, fi, paritat, "D-S"], ...]
    trams = {}
    for l in llegir(tram):
        if not l.startswith(MUN):
            continue
        dist, sec = int(l[5:7]), int(l[7:10])
        cvia = l[20:25]
        par = int(l[47])               # 1 senars, 2 parells
        ini, fi = int(l[48:52]), int(l[53:57])
        trams.setdefault(cvia, set()).add((ini, fi, par, f"{dist}-{sec}"))

    carrers = []
    for cvia, ts in trams.items():
        if cvia not in noms:
            continue
        carrers.append([noms[cvia], sorted(ts)])
    carrers.sort(key=lambda c: c[0])

    # Meses (accepta l'Excel d'un districte o el de tota la ciutat, pestanya "Barcelona ciutat")
    seccions, brut = {}, {}
    for x in excels:
        wb = openpyxl.load_workbook(x, data_only=True)
        ws = wb["Barcelona ciutat"] if "Barcelona ciutat" in wb.sheetnames else wb.active
        cap = [str(c or "").strip().lower() for c in next(ws.iter_rows(max_row=1, values_only=True))]
        ix = {n: cap.index(n) for n in ("districte", "secció", "mesa", "lletra inici", "lletra final",
                                          "codi local", "local electoral", "adreça")}
        for r in ws.iter_rows(min_row=2, values_only=True):
            if not r[ix["districte"]]:
                continue
            g = lambda n: str(r[ix[n]]).strip()
            k = f"{int(g('districte'))}-{int(g('secció'))}"
            fila = [g("mesa"), g("lletra inici"), g("lletra final"), g("codi local")]
            if fila not in seccions.setdefault(k, []):
                seccions[k].append(fila)
            brut[g("codi local")] = (g("local electoral"), g("adreça"))

    # Locals: neteja automàtica, i locals.json mana (correccions a mà)
    manuals = json.load(open(os.path.join(AQUI, "locals.json"), encoding="utf-8"))
    locals_ = {c: manuals.get(c) or netejar_local(*v) for c, v in brut.items()}
    data = re.search(r"D(\d{6})", os.path.basename(tram)).group(1)
    districtes_amb_meses = sorted({int(k.split("-")[0]) for k in seccions})
    dades = {
        "meta": {
            "font": "Eleccions 29N · Barcelona ciutat · Dades: INE, Cens Electoral (20%s/%s)" % (data[:2], data[2:4]),
            "districtes": {str(k): v for k, v in DISTRICTES.items()},
            "amb_meses": districtes_amb_meses,
        },
        "locals": locals_,
        "seccions": seccions,
        "carrers": [[n, [list(t) for t in ts]] for n, ts in carrers],
    }
    out = os.path.join(AQUI, "..", "dades.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(dades, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(carrers)} carrers, {sum(len(c[1]) for c in carrers)} trams, "
          f"{len(seccions)} seccions amb meses (districtes {districtes_amb_meses}) -> {out} "
          f"({os.path.getsize(out)//1024} KB)")


if __name__ == "__main__":
    main()
