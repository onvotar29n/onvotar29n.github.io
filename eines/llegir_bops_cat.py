#!/usr/bin/env python3
"""Llegeix els PDF del BOP de Girona, Lleida i Tarragona (relació de seccions, meses i locals)
i el PDF de correccions de Barcelona. Cal pdfplumber (pip install pdfplumber).

Cada província té un format diferent: es llegeixen les paraules amb la seva posició i es
reparteixen per columnes. Les cel·les que ocupen més d'una línia s'enganxen a la fila.

Ús:
  python3 llegir_bops_cat.py girona Girona.pdf UP.P17... sortida.json
  python3 llegir_bops_cat.py lleida lleida.pdf UP.P25... sortida.json
  python3 llegir_bops_cat.py tarragona Tarragona.pdf UP.P43... sortida.json
  python3 llegir_bops_cat.py correccions correccions.pdf - sortida.json
"""
import json, re, sys, unicodedata
import pdfplumber

# Columnes: (nom, x inicial). Una paraula va a la columna amb la x inicial més gran <= x0.
COLS = {
    "girona": [("mun", 30), ("municipi", 55), ("dist", 205), ("sec", 222), ("sub", 242), ("mesa", 262),
               ("ini", 282), ("fi", 299), ("local", 312), ("adreca", 490)],
    "lleida": [("municipi", 95), ("dist", 165), ("sec", 180), ("sub", 200), ("mesa", 210), ("ini", 234),
               ("fi", 248), ("local", 264), ("adreca", 364), ("cp", 478)],
    "tarragona": [("prov", 90), ("mun", 110), ("municipi", 124), ("dist", 239), ("sec", 249), ("sub", 261),
                  ("mesa", 272), ("ini", 286), ("fi", 300), ("local", 312), ("adreca", 452)],
    "correccions": [("prov", 50), ("mun", 66), ("municipi", 100), ("dist", 185), ("sec", 205), ("sub", 221),
                    ("mesa", 230), ("ini", 243), ("fi", 255), ("codi", 275), ("local", 318), ("adreca", 470)],
}
# En aquests formats la part d'una cel·la que no cap queda a la línia de sobre de la fila
ENGANXA_A_LA_SEGUENT = {"lleida"}


def norm(x):
    return "".join(c for c in unicodedata.normalize("NFD", x.upper()) if unicodedata.category(c) != "Mn")


def linies(page):
    ws = sorted((w for w in page.extract_words(keep_blank_chars=False) if w.get("upright", True)),
                key=lambda w: (round(w["top"]), w["x0"]))
    out, vistes = [], set()
    for w in ws:
        # alguns PDF escriuen el mateix text dues vegades (negreta simulada)
        vk = (w["text"], round(w["x0"]), round(w["top"]))
        if vk in vistes:
            continue
        vistes.add(vk)
        if out and abs(w["top"] - out[-1]["top"]) <= 2.5:
            out[-1]["ws"].append(w)
        else:
            out.append({"top": w["top"], "ws": [w]})
    return out


def columnes(ws, cols):
    d = {}
    for w in sorted(ws, key=lambda w: w["x0"]):
        nom = None
        for n, x in cols:
            if w["x0"] >= x - 0.5:
                nom = n
        if nom:
            d.setdefault(nom, []).append(w["text"])
    out = {k: " ".join(v) for k, v in d.items()}
    # números partits en dues paraules ('1 0' -> '10')
    for k in ("dist", "sec", "sub"):
        if k in out and re.fullmatch(r"\d( \d)+", out[k]):
            out[k] = out[k].replace(" ", "")
    return out


def es_fila(d):
    return bool(re.fullmatch(r"\d{1,2}", d.get("dist", "")) and re.fullmatch(r"\d{1,3}", d.get("sec", ""))
                and re.fullmatch(r"[A-Z]", d.get("mesa", "")) and re.fullmatch(r"[A-ZÑ]", d.get("ini", ""))
                and re.fullmatch(r"[A-ZÑ]", d.get("fi", "")))


def llegir(fmt, pdf):
    cols = COLS[fmt]
    files = []
    for page in pdfplumber.open(pdf).pages:
        ls = linies(page)
        # Marca les línies que són fila (tenen districte, secció, mesa i lletres)
        for l in ls:
            l["d"] = columnes(l["ws"], cols)
            l["fila"] = es_fila(l["d"])
        anchors = [l for l in ls if l["fila"]]
        for l in ls:
            if l["fila"] or not anchors:
                continue
            txt = " ".join(w["text"] for w in l["ws"])
            if re.search(r"CSV|FIRMANTE|DIRECCI[OÓ]N DE|INFORME DE FIRMA|Butllet|Página|MUNICIPI|Municipio|LOCALS EN|Local Electoral|C\.Prov|DTE\. SECC|^L\. L\.$|DONDE|DEBE|BOP número|Pàg\. ", txt):
                continue
            # quina fila? la més propera (o, si cal, la següent)
            lim = 20 if fmt in ENGANXA_A_LA_SEGUENT else 14
            seg = [a for a in anchors if a["top"] > l["top"] and a["top"] - l["top"] < lim]
            ant = [a for a in anchors if a["top"] < l["top"] and l["top"] - a["top"] < 14]
            if fmt in ENGANXA_A_LA_SEGUENT:
                a = seg[0] if seg else (ant[-1] if ant else None)
                pos = "abans"
            else:
                a = ant[-1] if ant else (seg[0] if seg else None)
                pos = "despres" if ant else "abans"
            if a is None:
                continue
            for k, v in l["d"].items():
                a.setdefault("extra", []).append((pos, l["top"], k, v))
        etiq = [(l["top"], "dice" if "DONDE" in l["ws"][0]["text"] else "debe") for l in ls
                if l["ws"][0]["text"] in ("DONDE", "DEBE")]
        for a in anchors:
            d = dict(a["d"])
            prev = [e for t, e in etiq if t < a["top"]]
            d["estat"] = prev[-1] if prev else ""
            # cada cel·la: els trossos de totes les seves línies, de dalt a baix
            trossos = {k: [(a["top"], v)] for k, v in a["d"].items()}
            for pos, top, k, v in a.get("extra", []):
                if k not in ("dist", "sec", "sub", "mesa", "ini", "fi"):
                    trossos.setdefault(k, []).append((top, v))
            for k, ts in trossos.items():
                d[k] = " ".join(v for t, v in sorted(ts)).strip()
            d["top"], d["pagina"] = a["top"], page.page_number
            files.append(d)
    return files


def munis_ine(up):
    """Codi i nom de cada municipi segons el fitxer UP de l'INE."""
    out = {}
    for l in open(up, encoding="latin-1"):
        if l[5:12] == "0000000":
            out[l[2:5]] = l[94:154].strip()
    return out


def netejar(fmt, files, up):
    munis = munis_ine(up) if up != "-" else {}
    per_nom = {norm(n): c for c, n in munis.items()}
    out = []
    for d in files:
        r = {k: d.get(k, "").strip() for k in ("municipi", "dist", "sec", "sub", "mesa", "ini", "fi", "local", "adreca", "cp", "codi")}
        r["local"] = r["local"].replace("AIGUESTOS ES-", "AIGUESTOSES-")
        r["pagina"], r["estat"] = d["pagina"], d.get("estat", "")
        if fmt == "girona":
            r["mun"] = d["mun"][-3:]
        elif fmt in ("tarragona", "correccions"):
            m = re.match(r"^(\d{3})\s*(.*)$", d.get("mun", ""))
            r["mun"] = m.group(1) if m else d.get("mun", "")
            if m and m.group(2):
                r["municipi"] = (m.group(2) + " " + r["municipi"]).strip()
            r["prov"] = d.get("prov", "")
        else:
            r["mun"] = per_nom.get(norm(r["municipi"]), "")
        r["dist"], r["sec"] = int(r["dist"]), int(r["sec"])
        r["sub"] = int(r["sub"]) if r["sub"].isdigit() else 0
        adr = r["adreca"]
        if fmt == "tarragona":
            # 'C PAU CASALS 2 -SANTES CREUS -43815 AIGUAMÚRCIA -'
            parts = [p.strip() for p in adr.split(" -")]
            r["adreca"] = parts[0]
            cp = next((p for p in parts[1:] if re.match(r"^\d{5}\b", p)), "")
            r["cp"] = cp[:5]
            r["zona"] = next((p for p in parts[1:] if p and not re.match(r"^\d{5}\b", p) and p != "-"), "")
        elif fmt == "girona":
            # 'CIRCU REI JAUME I CONQUERIDOR, DEL 31' -> 'CIRCU REI JAUME I CONQUERIDOR (DEL) 31'
            adr = re.sub(r",\s*(DE LA|DE LES|DE L'|DELS|DEL|DE|D')\s+(?=\d|S/N)", lambda m: " (" + m.group(1) + ") ", adr)
            # el número és l'últim de l'adreça; el que ve després (sense xifres) és el nucli o barri
            m = re.match(r"^(.*\s(?:\d+[A-Z]?|S/N|SN|KM[\s\d.,]*))(?:\s+([^\d]*))?$", adr)
            if m:
                r["adreca"], r["zona"] = m.group(1), (m.group(2) or "")
        elif fmt == "lleida":
            r["adreca"] = re.sub(r",\s*$", "", adr)
            m = re.match(r"^(.*?\s(?:\d+\s?[A-Z]{0,3}|S/N|SN|KM[\s\d.,]*)),\s*(.*)$", r["adreca"])
            if m:
                r["adreca"], r["zona"] = m.group(1), m.group(2)
        elif fmt == "correccions":
            m = re.search(r",\s*(\d{5})\s", adr)
            r["cp"] = m.group(1) if m else ""
        out.append(r)
    return out


if __name__ == "__main__":
    fmt, pdf, up, sortida = sys.argv[1:5]
    files = netejar(fmt, llegir(fmt, pdf), up)
    json.dump(files, open(sortida, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    sense = sorted({f["municipi"] for f in files if not f["mun"]})
    print(f"{fmt}: {len(files)} meses, {len({f['mun'] for f in files})} municipis; sense codi: {sense}")
