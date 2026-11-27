#!/usr/bin/env python3
"""Genera les dades del cercador per a tot Catalunya (províncies de Barcelona, Girona, Lleida i Tarragona).

Entrades:
  - TRAM i VIAS del Callejero del Censo Electoral de l'INE (província 08)
  - Text del PDF del BOP amb les seccions, meses i locals (llegit amb llegir_bop.py)
  - locals.json: correccions a mà de noms i adreces de locals (opcional)

Sortida (a l'arrel del web):
  dades/index.json        municipis i llista de carrers (per als suggeriments)
  dades/m/<codi>.json     trams, meses i locals de cada municipi

Ús:
  python3 eines/construir_provincia.py TRAM.P08... VIAS.P08... BOP.txt
"""
import json, os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from construir_dades import TIPUS, TIPUS_ADR, PARTICULES, DISTRICTES, bonic, titol, llegir
from llegir_bop import parse, separar

AQUI = os.path.dirname(os.path.abspath(__file__))
SORTIDA = os.path.join(AQUI, "..", "dades")

TIPUS_EXTRA = {"CARRE": "Carrer", "AVGDA": "Avinguda", "CRA": "Carretera", "PSAJE": "Passatge", "JDINS": "Jardins",
               "URBAT": "Urbanització", "TRVA": "Travessera", "LLOC": "", "MASIA": "Masia", "C/": "Carrer",
               "PLAÇA": "Plaça", "PZ": "Plaça", "URB": "Urbanització", "AVDA": "Avinguda", "CR": "Carretera",
               "CRTA": "Carretera", "RAMBLA": "Rambla", "GRUP": "Grup", "JDIN": "Jardí", "PRAGE": "Paratge", "VNAT": "Veïnat", "PDA": "Partida", "PTDA": "Partida", "GJA": "Granja", "PROL": "Prolongació", "CLLON": "Carreró", "APTES": "Apartaments", "COMPX": "Complex", "COL": "Colònia", "SECT": "Sector", "POLIG": "Polígon", "LUGAR": "Lloc", "JARD": "Jardins", "BARRI": "Barri", "TRRNT": "Torrent", "PARC": "Parc", "PLCET": "Placeta"}

PARTICULES.update({"(DE L')": "de l'"})

ARTICLES = {"(L')": "L'", "(EL)": "El ", "(LA)": "La ", "(ELS)": "Els ", "(LES)": "Les "}

# Locals que el separador automàtic no resol
LOCALS_A_MA = {
    "CASAL DE SANTS C VIOLANT D'HONGRIA, REINA D'ARAGO (DE) 135, 08028 BARCELONA":
        ["Casal de Sants", "Carrer de Violant d'Hongria, Reina d'Aragó, 135", "08028"],
    "APSA (AIGÜES DEL PRAT, S.A.) PL AIGUA (DE L') 1, 08820 PRAT DE LLOBREGAT (EL), BARCELONA":
        ["APSA (Aigües del Prat)", "Plaça de l'Aigua, 1", "08820"],
}


def norm_txt(x):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", x.lower()) if unicodedata.category(c) != "Mn")


def nom_municipi(n):
    m = re.match(r"^(.*?)\s*(\([^)]*\))$", n.strip())
    if m and m.group(2) in ARTICLES:
        return ARTICLES[m.group(2)] + titol(m.group(1))
    return re.sub(r" E ", " e ", titol(n))


def punt_volat(t):
    """'Gal.la' -> 'Gal·la' (el cens escriu la ela geminada amb un punt)"""
    return re.sub(r"([lL])\.([lL])", r"\1·\2", t)


def nom_via(tipus, llarg):
    t = (TIPUS_EXTRA.get(tipus) or TIPUS.get(tipus) or tipus.title()).lower()
    part = re.search(r"\(([^)]*)\)\s*$", llarg)
    part = (" " + part.group(1).lower()) if part else ""
    part = part.replace("' ", "'")
    part = {" l'": " de l'", " la": " de la", " les": " de les", " el": " del", " els": " dels"}.get(part, part)
    T = t[:1].upper() + t[1:]
    sep = "" if part.endswith("'") else " "
    llarg = re.sub(r"^C/\s*", "", llarg)
    # Lleida i altres: la partícula va davant del nom ('DEL CARME', "DE L'ESTACIO")
    mp = re.match(r"^(DE LA|DE LES|DE L'|DELS|DEL|DE|D')\s*(\S.*)$", llarg)
    if mp and not part and t:
        part, llarg = " " + mp.group(1).lower(), mp.group(2)
    nb = bonic(llarg)
    if t and norm_txt(nb) == norm_txt(T):
        return T
    # 'Rambla Rambla Nova' -> 'Rambla Nova'
    if t and norm_txt(nb).split(" ")[0] == norm_txt(T) and not part:
        return nb
    n = f"{T}{part}{sep}{nb}" if t else nb
    return {"Gran via Corts Catalanes": "Gran Via de les Corts Catalanes",
            "Gran via Carles III": "Gran Via de Carles III"}.get(n, n)


def adreca(adr):
    """'C SALVADOR ESPRIU 3' -> 'Carrer Salvador Espriu, 3' ; 'PL AIGUA (DE L') 1' -> "Plaça de l'Aigua, 1" """
    m = re.match(r"^(\S+)\s+(.*?)\s*(\([^)]*\))?\s+(\d+\s?[A-Z]{0,3}|S/N|SN|KM[\s\d.,]*)$", adr.strip())
    if not m:
        return titol(adr)
    tipus, carrer, part, num = m.groups()
    mp = re.match(r"^(DE LA|DE LES|DE L'|DELS|DEL|DE|D')\s*(\S.*)$", carrer)
    if mp and not part:
        part, carrer = "(" + mp.group(1) + ")", mp.group(2)
    t = TIPUS_EXTRA[tipus] if tipus in TIPUS_EXTRA else (TIPUS_ADR.get(tipus) or TIPUS.get(tipus) or tipus.title())
    part = PARTICULES.get(part or "", "")
    nomc = titol(carrer)
    via = f"{t} {part}{nomc}" if part.endswith("'") else (f"{t} {part} {nomc}" if part else f"{t} {nomc}")
    via = via.strip()
    via = {"Travessera Dalt": "Travessera de Dalt", "Travessera Corts": "Travessera de les Corts"}.get(via, via)
    num = "s/n" if num in ("S/N", "SN") else num.strip()
    return f"{via}, {num}"


def clau(mun, d, s, sub):
    # Barcelona sense municipi a la clau per mantenir els enllaços antics (?s=5-10)
    return f"{d}-{s}" + (f"-{sub}" if sub else "")


PROVINCIES = {"08": "Barcelona", "17": "Girona", "25": "Lleida", "43": "Tarragona"}


def clau_muni(prov, mun):
    # Els municipis de la província de Barcelona mantenen el codi de 3 xifres (enllaços antics)
    return mun if prov == "08" else prov + mun


def meses_barcelona(bop, correccions):
    """Files del BOP de Barcelona amb les correccions aplicades (on diu -> ha de dir)."""
    files = parse(bop)
    for f in files:
        f["original"] = f["local_brut"].strip()
    if not correccions:
        return files, 0
    cor = json.load(open(correccions, encoding="utf-8"))
    blocs, cur = [], None
    for r in cor:
        if r["estat"] == "dice" and (cur is None or cur["debe"]):
            cur = {"dice": [], "debe": []}
            blocs.append(cur)
        cur[r["estat"]].append(r)
    k = lambda r: (r["mun"], int(r["dist"]), int(r["sec"]), int(r["sub"]), r["mesa"])
    n = 0
    for b in blocs:
        treure = {k(r) for r in b["dice"]}
        abans = [f for f in files if (f["mun"], f["dist"], f["sec"], f["sub"], f["mesa"]) in treure]
        if len(abans) != len(treure):
            print("Correcció que no quadra amb el BOP:", sorted(treure), file=sys.stderr)
            continue
        pos = files.index(abans[0])
        files = [f for f in files if f not in abans]
        nous = [dict(mun=r["mun"], municipi=r["municipi"], dist=int(r["dist"]), sec=int(r["sec"]), sub=int(r["sub"]),
                     mesa=r["mesa"], ini=r["ini"], fi=r["fi"], codi=r["codi"],
                     local_brut=(r["local"] + " " + r["adreca"]).strip(), corregit=True) for r in b["debe"]]
        files[pos:pos] = nous
        n += 1
    return files, n


def meses_altres(path, prov):
    """Files llegides amb llegir_bops_cat.py (Girona, Lleida, Tarragona)."""
    files, codis = [], {}
    for r in json.load(open(path, encoding="utf-8")):
        lk = (r["mun"], r["local"], r["adreca"])
        if lk not in codis:
            codis[lk] = "%s%s%03d" % (prov, r["mun"], sum(1 for c in codis if c[0] == r["mun"]) + 1)
        files.append(dict(mun=r["mun"], municipi=r["municipi"], dist=r["dist"], sec=r["sec"], sub=r["sub"],
                          mesa=r["mesa"], ini=r["ini"], fi=r["fi"], codi=codis[lk],
                          local=[titol(r["local"].strip('"')), adreca(r["adreca"]), r.get("cp", "")]))
    return files


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--ine", required=True, help="carpeta amb els TRAM.Pxx i VIAS.Pxx de l'INE")
    ap.add_argument("--bop", required=True, help="text del BOP de Barcelona")
    ap.add_argument("--correccions", help="correccions del BOP de Barcelona (json de llegir_bops_cat.py)")
    ap.add_argument("--meses", nargs="*", default=[], help="prov=fitxer.json (p. ex. 17=meses_17.json)")
    a = ap.parse_args()
    import glob

    manuals = {}
    p = os.path.join(AQUI, "locals.json")
    if os.path.exists(p):
        manuals = json.load(open(p, encoding="utf-8"))

    fonts = {"08": None}
    bcn, n_cor = meses_barcelona(a.bop, a.correccions)
    originals = {f["codi"]: f["original"] for f in bcn if "original" in f}
    per_prov = {"08": bcn}
    for m in a.meses:
        pr, path = m.split("=")
        per_prov[pr] = meses_altres(path, pr)

    munis, seccions, locals_ = {}, collections.defaultdict(dict), collections.defaultdict(dict)
    n_meses = 0
    for pr, files in per_prov.items():
        for f in files:
            mk = clau_muni(pr, f["mun"])
            munis[mk] = nom_municipi(f["municipi"])
            k = clau(mk, f["dist"], f["sec"], f["sub"])
            seccions[mk].setdefault(k, []).append([f["mesa"], f["ini"], f["fi"], f["codi"]])
            n_meses += 1
            if f["codi"] in locals_[mk]:
                continue
            if "local" in f:
                locals_[mk][f["codi"]] = f["local"]
                continue
            brut = f["local_brut"].strip()
            # la correcció a mà només val si el BOP no ha canviat aquell local
            if f["codi"] in manuals and not (f.get("corregit") and brut != originals.get(f["codi"])):
                locals_[mk][f["codi"]] = manuals[f["codi"]]
            elif brut in LOCALS_A_MA:
                locals_[mk][f["codi"]] = LOCALS_A_MA[brut]
            else:
                nom, adr, zona, cp, pob = separar(brut)
                locals_[mk][f["codi"]] = [titol(nom), adreca(adr), cp]

    noms, nuclis = {}, {}
    trams = collections.defaultdict(lambda: collections.defaultdict(set))
    dates = set()
    for pr in per_prov:
        vias = glob.glob(os.path.join(a.ine, "**", "VIAS.P" + pr + "*"), recursive=True)[0]
        tram = glob.glob(os.path.join(a.ine, "**", "TRAM.P" + pr + "*"), recursive=True)[0]
        dates.add(re.search(r"D(\d{6})", os.path.basename(tram)).group(1))
        for l in llegir(vias):
            if l.startswith(pr):
                noms[(clau_muni(pr, l[2:5]), l[5:10])] = punt_volat(nom_via(l[52:57].strip(), l[57:107].strip() or l[10:40].strip()))
        for l in llegir(tram):
            if not l.startswith(pr):
                continue
            mk, d, s = clau_muni(pr, l[2:5]), int(l[5:7]), int(l[7:10])
            sub = l[10:13].strip()
            sub = int(sub) if sub else 0
            k = clau(mk, d, s, sub)
            if k not in seccions.get(mk, {}):
                k2 = clau(mk, d, s, 0)
                k = k2 if k2 in seccions.get(mk, {}) else k
            via = l[20:25]
            if via == "00000":
                # Sense carrer (masies, cases i finques disperses): l'INE hi posa una pseudovia
                # amb codi propi [25:30] i el nom de la casa [195:245]; [110:135] és el nucli
                via = "S" + l[25:30]
                if (mk, via) not in noms:
                    noms[(mk, via)] = punt_volat(nom_via("", l[195:245].strip())) or nom_municipi(l[110:135].strip())
                    nuclis[(mk, via)] = nom_municipi(l[110:135].strip())
            # un mateix codi de carrer pot ser a dos nuclis (Carrer Uruguai de Mira-sol i de Valldoreix):
            # es guarden per separat
            nu = l[110:135].strip()
            # lletra del portal (79 / 79 B); 'S' amb número 0 vol dir sense número
            ini, fi = int(l[48:52]), int(l[53:57])
            li = "" if ini == 0 else l[52].strip()
            lf = "" if fi == 0 else l[57].strip()
            trams[mk][(via, nu)].add((ini, fi, int(l[47]), k, li, lf))

    os.makedirs(os.path.join(SORTIDA, "m"), exist_ok=True)
    for old in glob.glob(os.path.join(SORTIDA, "m", "*.json")):
        os.remove(old)
    codis = sorted(munis, key=lambda c: (c != "019", norm_txt(munis[c])))
    index_munis, n_carrers, sense_meses = [], 0, collections.Counter()
    for mun in codis:
        # Un carrer llarg que passa per dos nuclis es queda junt. Només se separa per nuclis quan
        # el mateix número surt a més d'un nucli (Carrer Uruguai 7 de Mira-sol i de Valldoreix).
        per_via = collections.defaultdict(dict)
        for (via, nu), ts in trams[mun].items():
            per_via[via][nu] = ts
        def es_solapen(ts1, ts2):
            for a in ts1:
                for b in ts2:
                    if (a[2] == 0 or b[2] == 0 or a[2] == b[2]) and max(a[0], b[0]) <= min(a[1], b[1]) \
                            and not (a[0] == 0 and b[0] == 0):
                        return True
            return False
        agrupats = {}
        for via, pn in per_via.items():
            nus = list(pn)
            if len(nus) > 1 and any(es_solapen(pn[x], pn[y]) for i, x in enumerate(nus) for y in nus[i + 1:]):
                for nu, ts in pn.items():
                    agrupats[(via, nu)] = ts
            else:
                agrupats[(via, nus[0] if len(nus) == 1 else "")] = set().union(*pn.values())
        carrers = [[noms.get((mun, cv[0]), "?"), sorted(ts), cv] for cv, ts in agrupats.items()]
        # sense carrer = pseudovia de l'INE i tots els trams sense número
        for c in carrers:
            c.append(c[2][0].startswith("S") and all(t[0] == 0 and t[1] == 0 for t in c[1]))
        # noms repetits de cases sense carrer: s'hi afegeix el nucli
        # noms repetits dins el municipi (Carrer de la Font d'Àger i d'Agulló): s'hi afegeix el nucli
        # l'INE escriu els nuclis sense accents: si el nucli és el poble principal, nom del municipi
        def nom_nucli(c):
            nu = nom_municipi(c[2][1]) if c[2][1] else ""
            return munis[mun] if norm_txt(nu) == norm_txt(munis[mun]) else nu
        grups = collections.defaultdict(list)
        for c in carrers:
            grups[c[0]].append(c)
        for nom, cs in grups.items():
            nus = [nom_nucli(c) for c in cs]
            if len(cs) > 1 and all(nus) and len({norm_txt(x) for x in nus}) > 1:
                for c, nu in zip(cs, nus):
                    c[0] = f"{nom} ({nu})"
        carrers.sort(key=lambda c: (c[0], c[2][0], c[2][1]))
        index_munis.append([mun, munis[mun], [c[0] for c in carrers], [i for i, c in enumerate(carrers) if c[3]]])
        n_carrers += len(carrers)
        for c in carrers:
            for t in c[1]:
                if t[3] not in seccions[mun]:
                    sense_meses[mun] += 1
        dades = {"locals": locals_[mun], "seccions": seccions[mun],
                 "carrers": [[n, [list(t[:4]) + ([t[4], t[5]] if t[4] or t[5] else []) for t in ts]]
                             for n, ts, *_ in carrers]}
        if mun == "019":
            dades["districtes"] = {str(k): v for k, v in DISTRICTES.items()}
        json.dump(dades, open(os.path.join(SORTIDA, "m", f"{mun}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, separators=(",", ":"))

    data = max(dates)
    index = {"font": "Eleccions 29N · Catalunya · Dades: INE, Cens Electoral (20%s/%s) i BOP" % (data[:2], data[2:4]),
             "municipis": index_munis}
    json.dump(index, open(os.path.join(SORTIDA, "index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"{len(codis)} municipis, {n_carrers} carrers, {n_meses} meses, {n_cor} correccions aplicades")
    if sense_meses:
        print("Trams sense mesa:", dict(sense_meses))


if __name__ == "__main__":
    main()
