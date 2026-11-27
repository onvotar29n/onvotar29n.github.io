# On voto? · 29N Catalunya

Cercador per saber la mesa i el col·legi electoral a partir de l'adreça i del primer cognom.
És una web estàtica: `index.html` + `dades/` (`index.json` amb els municipis i els carrers, i un fitxer `dades/m/<codi>.json` per municipi, que només es baixa quan cal). Les cerques es fan al navegador i no s'envia ni es desa cap dada.

## Publicar
- **GitHub Pages**: Settings → Pages → Deploy from branch → `main` / root (cal que el repositori sigui públic al pla gratuït).
- La web es pot indexar als cercadors. L'adreça canònica és https://onvotar29n.junts.cat/.

## Actualitzar les dades (abans de cada elecció)
1. Baixa el *Callejero del Censo Electoral* de l'INE (província de Barcelona, el període més recent):
   https://www.ine.es/dyngs/DAB/es/index.htm?cid=1390
2. Meses i locals: text del BOP de Barcelona (`eines/meses/BOP_08_barcelona.txt`) i PDF dels BOP de Girona, Lleida i Tarragona i de les correccions de Barcelona, convertits amb:
   ```
   pip install pdfplumber
   python3 eines/llegir_bops_cat.py girona Girona.pdf UP.P17... eines/meses/meses_17_girona.json
   python3 eines/llegir_bops_cat.py lleida lleida.pdf UP.P25... eines/meses/meses_25_lleida.json
   python3 eines/llegir_bops_cat.py tarragona Tarragona.pdf UP.P43... eines/meses/meses_43_tarragona.json
   python3 eines/llegir_bops_cat.py correccions correccions.pdf - eines/meses/correccions_08_barcelona.json
   ```
3. Genera les dades (la carpeta de l'INE ha de contenir els TRAM i VIAS de les quatre províncies):
   ```
   python3 eines/construir_catalunya.py --ine CARPETA_INE --bop eines/meses/BOP_08_barcelona.txt \
     --correccions eines/meses/correccions_08_barcelona.json \
     --meses 17=eines/meses/meses_17_girona.json 25=eines/meses/meses_25_lleida.json 43=eines/meses/meses_43_tarragona.json
   ```
   Això torna a generar la carpeta `dades/`. A `eines/locals.json` hi ha noms i adreces de locals corregits a mà, que tenen preferència.

`eines/construir_dades.py` és l'eina antiga només per a Barcelona ciutat (a partir de l'Excel); ja no la fa servir la web.

Codi QR: [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) (MIT, Kazuhiko Arase).

Fonts: INE (Cens Electoral, CC BY 4.0) i llistes oficials de locals i meses.
Elaborat per Jaume Oliva Sala.
