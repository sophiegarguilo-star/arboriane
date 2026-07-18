# -*- coding: utf-8 -*-
"""
Rendu HTML autonome d'un livre (L10c, choix « HTML d'abord » — D4).

Un seul fichier, deux usages : lecture en ligne (sommaire cliquable, envoyable
par mail) et impression / PDF navigateur (`@media print`, format A4 ou A5).

Le style est piloté par un THÈME (Héritage / Épuré / Sépia) ; par-dessus,
l'utilisateur personnalise format, taille du texte, couverture, titre… Aucune
dépendance externe : tout est inline.
"""

import html

from services import personnes
from services.livre import recit, chapitres, ascendance, descendance, annexes
from services.livre import livret_ascendance

_FORMATS = {"a4": ("A4", "2.2cm 2cm"), "a5": ("A5", "1.6cm 1.4cm")}

# Un thème = palette + police + ornements. `fleuron`/`orn` = "" pour aucun.
THEMES = {
    "heritage": {
        "nom": "Héritage", "fond": "#d9d5cc", "papier": "#fbf9f4", "encre": "#26221c",
        "doux": "#7c7268", "or": "#9c7b3f", "orclair": "#c8a86a",
        "police": '"Iowan Old Style","Palatino Linotype","Book Antiqua",Palatino,Georgia,serif',
        "fleuron": "❧", "orn_couv": "❦", "maj_titre": True, "lettrine": True,
    },
    "epure": {
        "nom": "Épuré", "fond": "#eceae6", "papier": "#ffffff", "encre": "#232323",
        "doux": "#8a8a8a", "or": "#3f6f8f", "orclair": "#c7d4dc",
        "police": '"Avenir Next","Segoe UI",system-ui,-apple-system,Helvetica,Arial,sans-serif',
        "fleuron": "", "orn_couv": "", "maj_titre": False, "lettrine": False,
    },
    "sepia": {
        "nom": "Sépia", "fond": "#ded2ba", "papier": "#f5ecd8", "encre": "#4a3a29",
        "doux": "#8a745a", "or": "#9a6b34", "orclair": "#cbab7f",
        "police": '"Hoefler Text","Baskerville Old Face",Baskerville,Georgia,"Times New Roman",serif',
        "fleuron": "✦", "orn_couv": "❈", "maj_titre": True, "lettrine": True,
    },
}
_TITRES = {"unions": "Union%s & enfants"}
_LIB_SOMMAIRE = {"comment_lire": "Comment lire ce livre", "biographie": "Biographie",
                 "filiation": "Filiation", "unions": "Unions & enfants",
                 "ascendance": "Les aïeux", "descendance": "La descendance",
                 "album": "Album photos", "preface": "Préface",
                 "chronologie": "Chronologie", "index": "Index",
                 "dedicace": "Dédicace", "remerciements": "Remerciements",
                 "introduction": "Introduction"}

# Sections de texte libre saisies par l'utilisateur (titre fixe par type, sauf
# « chapitre » dont le titre est libre). Voir _texte_libre / composeur.
_TITRES_TEXTE = {"dedicace": "Dédicace", "remerciements": "Remerciements",
                 "introduction": "Introduction", "preface": "Préface"}


def _ancre(s):
    """Identifiant d'ancre d'une section : la clé unique si présente (chapitres
    personnels, ajoutés plusieurs fois), sinon le type (sections uniques)."""
    return s.get("cle") or s.get("type") or ""


def _e(s):
    return html.escape(str(s or ""))


def _theme(mep):
    return THEMES.get(mep.get("theme"), THEMES["heritage"])


def _css(mep):
    t = _theme(mep)
    taille = max(85, min(130, int(mep.get("taille", 100)))) / 100.0
    taille_page, marge = _FORMATS.get(mep.get("format"), _FORMATS["a4"])
    # Ornement sous les titres de chapitre : fleuron du thème, sinon fin filet.
    if t["fleuron"]:
        orn = ('.page h2::after{{content:"{f}";display:block;text-align:center;'
               'color:var(--or);font-size:calc(1rem*var(--f));letter-spacing:.4em;'
               'margin:8px 0 30px;}}').format(f=t["fleuron"])
    else:
        orn = ('.page h2::after{content:"";display:block;width:40px;height:2px;'
               'background:var(--or);margin:14px auto 30px;}')
    maj = ("text-transform:uppercase;letter-spacing:.18em;font-size:calc(1.15rem*var(--f));"
           if t["maj_titre"]
           else "letter-spacing:.01em;font-size:calc(1.5rem*var(--f));font-weight:500;")
    lettrine = ('.bio p.premier::first-letter{float:left;font-size:3.5em;line-height:.72;'
                'padding:.05em .1em 0 0;color:var(--or);font-weight:400;}'
                if t["lettrine"] else "")
    orn_c = ('.couverture .orn-c::before{content:"%s";}' % t["orn_couv"]) if t["orn_couv"] \
            else '.couverture .orn-c{width:44px;height:1px;background:var(--or-clair);}'
    return """
    :root {{ --f:{f:.3f}; --encre:{encre}; --or:{or}; --or-clair:{orclair};
      --doux:{doux}; --papier:{papier}; }}
    * {{ box-sizing:border-box; }}
    body {{ font-family:{police}; color:var(--encre); background:{fond};
      margin:0; padding:30px 16px; font-size:calc(18px*var(--f)); line-height:1.78;
      -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility; }}
    .livre {{ max-width:720px; margin:0 auto; }}
    .page {{ position:relative; background:var(--papier); padding:64px 68px 72px;
      margin:0 auto 30px; box-shadow:0 6px 30px rgba(60,50,30,.16); border-radius:2px; }}
    .page h2 {{ text-align:center; font-weight:400; color:var(--encre); margin:0 0 4px; {maj} }}
    {orn}
    .page p {{ margin:0 0 4px; text-align:justify; hyphens:auto; text-indent:1.4em; }}
    .page p.premier {{ text-indent:0; }}
    .doux {{ color:var(--doux); }}
    em, .italique {{ font-style:italic; }}
    .dedicace {{ display:flex; flex-direction:column; justify-content:center; min-height:60vh; }}
    .dedicace p {{ text-align:center; font-style:italic; text-indent:0; color:var(--doux);
      font-size:calc(1.15rem*var(--f)); line-height:2; }}
    {lettrine}
    .couverture {{ min-height:80vh; display:flex; flex-direction:column;
      align-items:center; justify-content:center; text-align:center; padding:80px 56px; }}
    .couverture .cadre {{ border-top:1px solid var(--or-clair);
      border-bottom:1px solid var(--or-clair); padding:52px 20px; width:100%; max-width:460px; }}
    .couverture .surtitre {{ text-transform:uppercase; letter-spacing:.42em;
      font-size:calc(.66rem*var(--f)); color:var(--or); margin-bottom:26px; }}
    .couverture h1 {{ font-weight:400; font-size:calc(2.9rem*var(--f)); line-height:1.12; margin:0 0 14px; }}
    .couverture .soustitre {{ font-style:italic; color:var(--doux);
      font-size:calc(1.1rem*var(--f)); margin-bottom:4px; }}
    .couverture .orn-c {{ color:var(--or); font-size:calc(1.3rem*var(--f)); margin:26px auto; }}
    {orn_c}
    .couverture .qui {{ letter-spacing:.16em; text-transform:uppercase; font-size:calc(.82rem*var(--f)); }}
    .couverture .dates {{ color:var(--doux); font-size:calc(.82rem*var(--f)); margin-top:6px; }}
    .couverture .pied {{ margin-top:44px; font-size:calc(.76rem*var(--f)); color:var(--doux); font-style:italic; }}
    .couverture.sobre .initiale {{ display:none; }}
    .initiale {{ width:104px; height:104px; border-radius:50%; margin:0 auto 30px;
      border:1px solid var(--or-clair); color:var(--or); display:flex;
      align-items:center; justify-content:center; font-size:calc(2.4rem*var(--f)); }}
    .sommaire ol {{ list-style:none; padding:0; margin:0; max-width:420px; margin-inline:auto; }}
    .sommaire li {{ display:flex; align-items:baseline; gap:10px; padding:11px 0; }}
    .sommaire li .pointille {{ flex:1; border-bottom:1px dotted var(--or-clair); transform:translateY(-3px); }}
    .sommaire a {{ color:var(--encre); text-decoration:none; letter-spacing:.04em; }}
    .sommaire .num {{ color:var(--or); font-variant-numeric:tabular-nums; }}
    .paire {{ display:flex; gap:16px; padding:7px 0; justify-content:center; }}
    .paire .role {{ min-width:70px; text-align:right; color:var(--or); letter-spacing:.08em;
      font-size:calc(.82rem*var(--f)); text-transform:uppercase; align-self:center; }}
    .fratrie {{ text-align:center; margin-top:22px; }}
    .union {{ text-align:center; margin:0 0 30px; }}
    .union .couple {{ font-size:calc(1.15rem*var(--f)); }}
    .union .quand {{ display:block; color:var(--doux); font-style:italic;
      font-size:calc(.92rem*var(--f)); margin-top:4px; }}
    .union .enfants {{ margin-top:12px; }}
    .union .enfants .et {{ color:var(--or); display:block; font-size:calc(.72rem*var(--f));
      letter-spacing:.22em; text-transform:uppercase; margin-bottom:4px; }}
    hr.filet {{ border:0; border-top:1px solid var(--or-clair); width:120px; margin:34px auto 0; opacity:.6; }}
    .gen {{ margin:0 0 26px; }}
    .gen h3 {{ text-align:center; font-weight:400; color:var(--or); margin:0 0 14px;
      font-size:calc(.92rem*var(--f)); letter-spacing:.14em; text-transform:uppercase; }}
    .aieul {{ display:flex; gap:14px; align-items:baseline; padding:6px 0;
      border-bottom:1px solid rgba(0,0,0,.05); }}
    .aieul:last-child {{ border-bottom:0; }}
    .aieul .sosa {{ flex:0 0 auto; min-width:34px; text-align:right; color:var(--or);
      font-variant-numeric:tabular-nums; font-size:calc(.86rem*var(--f)); }}
    .aieul .txt {{ flex:1; text-align:left; }}
    .couverture .portrait {{ width:150px; height:150px; object-fit:cover; border-radius:50%;
      border:1px solid var(--or-clair); margin:0 auto 30px; display:block; }}
    .galerie {{ display:grid; grid-template-columns:repeat(2,1fr); gap:20px; }}
    .galerie .photo {{ margin:0; text-align:center; }}
    .galerie .photo img {{ width:100%; height:auto; border-radius:2px;
      box-shadow:0 2px 10px rgba(60,50,30,.18); }}
    .galerie figcaption {{ margin-top:8px; font-style:italic; color:var(--doux);
      font-size:calc(.86rem*var(--f)); }}
    .frise-e {{ display:flex; gap:18px; align-items:baseline; padding:8px 0;
      border-bottom:1px solid rgba(0,0,0,.05); }}
    .frise-e:last-child {{ border-bottom:0; }}
    .frise-e .an {{ flex:0 0 auto; min-width:54px; color:var(--or);
      font-variant-numeric:tabular-nums; }}
    #index h3 {{ text-align:center; font-weight:400; color:var(--or);
      text-transform:uppercase; letter-spacing:.14em; font-size:calc(.9rem*var(--f));
      margin:22px 0 10px; }}
    .index-liste {{ columns:2; column-gap:28px; text-align:left; text-indent:0;
      font-size:calc(.92rem*var(--f)); line-height:1.6; }}
    .partie {{ text-align:center; min-height:34vh; display:flex; flex-direction:column;
      justify-content:center; page-break-before:always; }}
    .partie .sur {{ text-transform:uppercase; letter-spacing:.32em; color:var(--or);
      font-size:calc(.72rem*var(--f)); margin-bottom:10px; }}
    .chap .chap-num {{ text-align:center; text-transform:uppercase; letter-spacing:.2em;
      color:var(--or); font-size:calc(.72rem*var(--f)); margin-bottom:6px; }}
    .chap .renvoi {{ text-indent:0; text-align:center; font-style:italic; color:var(--doux);
      margin-top:18px; font-size:calc(.9rem*var(--f)); }}
    .mini-arbre {{ width:100%; height:auto; margin:6px 0 22px; }}
    .mini-arbre .mb {{ fill:var(--papier); stroke:var(--or-clair); }}
    .mini-arbre .mn {{ fill:var(--encre); font-size:11px; }}
    .mini-arbre .mp {{ fill:var(--doux); font-size:9px; }}
    .mini-arbre .ml {{ stroke:var(--or-clair); fill:none; }}
    .fiche {{ border:1px solid var(--or-clair); border-radius:3px; padding:16px 20px;
      margin:8px 0 6px; text-indent:0; }}
    .fiche h3 {{ text-align:center; text-transform:uppercase; letter-spacing:.14em;
      color:var(--or); font-size:calc(.72rem*var(--f)); font-weight:400; margin:0 0 12px; }}
    .fiche .lg {{ display:flex; gap:10px; padding:4px 0; text-indent:0; }}
    .fiche .lg .r {{ flex:0 0 auto; min-width:78px; color:var(--or); letter-spacing:.06em;
      font-size:calc(.76rem*var(--f)); text-transform:uppercase; align-self:center; }}
    .fiche .enf {{ margin:8px 0 0; text-indent:0; }}
    .fiche .enf .r {{ display:block; color:var(--or); letter-spacing:.06em;
      font-size:calc(.72rem*var(--f)); text-transform:uppercase; margin-bottom:4px; }}
    .fiche .per {{ color:var(--doux); font-size:calc(.86rem*var(--f)); }}
    @page {{ size:{taille_page}; margin:{marge}; }}
    @media print {{
      body {{ background:#fff; padding:0; font-size:11.4pt; }}
      .livre {{ max-width:none; }}
      .page {{ box-shadow:none; margin:0; padding:0; page-break-after:always; }}
      .couverture {{ min-height:88vh; }}
      a {{ color:inherit; text-decoration:none; }}
    }}
    """.format(f=taille, encre=t["encre"], **{"or": t["or"]}, orclair=t["orclair"],
               doux=t["doux"], papier=t["papier"], fond=t["fond"], police=t["police"],
               maj=maj, orn=orn, lettrine=lettrine, orn_c=orn_c,
               taille_page=taille_page, marge=marge)


def _titre(texte):
    return "<h2>%s</h2>" % _e(texte)


def _fichier_media(m):
    """Nom de fichier d'un média, qu'il soit un dict {fichier,…} ou une chaîne."""
    return (m.get("fichier") or "") if isinstance(m, dict) else str(m or "")


def _media_principal(f):
    """Fichier du portrait de couverture : le média « principal », sinon le 1er.
    Tolère les médias stockés en chaîne (pas seulement en dict)."""
    medias = f.get("medias") or []
    if not medias:
        return ""
    prim = next((m for m in medias if isinstance(m, dict) and m.get("principale")),
                medias[0])
    return _fichier_media(prim)


def _medaillon(f, lire_media):
    """Portrait rond si une photo existe (et lisible), sinon médaillon à initiale."""
    if lire_media:
        fic = _media_principal(f)
        uri = lire_media(fic) if fic else ""
        if uri:
            return '<img class="portrait" alt="" src="%s">' % uri
    initiale = (f.get("nom_complet", "").strip()[:1] or "•").upper()
    return '<div class="initiale">%s</div>' % _e(initiale)


def _couverture(livre, f, lire_media=None):
    mep = livre.get("mise_en_page", {})
    style = "sobre" if mep.get("couverture") == "sobre" else "classique"
    nom = f.get("nom_complet", "")
    periode = f.get("periode", "")
    return """
    <section class="page couverture {style}">
      <div class="cadre">
        <div class="surtitre">Histoire de famille</div>
        {medaillon}
        <h1>{titre}</h1>
        {sous}
        <div class="orn-c"></div>
        <div class="qui">{nom}</div>
        {dates}
      </div>
      {pied}
    </section>""".format(
        style=style, titre=_e(livre.get("titre", "")), nom=_e(nom),
        medaillon=_medaillon(f, lire_media),
        sous=('<div class="soustitre">%s</div>' % _e(livre["sous_titre"]))
             if livre.get("sous_titre") else "",
        dates=('<div class="dates">%s</div>' % _e(periode)) if periode else "",
        pied=('<div class="pied">Établi par %s</div>' % _e(livre["auteur"]))
             if livre.get("auteur") else "")


def _comment_lire():
    return ("""
    <section class="page" id="comment_lire">%s
      <p class="premier">Ce livre raconte une vie à partir de faits vérifiés :
      chaque phrase s'appuie sur une date, un lieu ou un acte conservé. Rien n'est
      inventé ; quand une information manque, elle est simplement passée sous silence.</p>
      <p>Les personnes encore vivantes peuvent être masquées (indiquées par
      « ——— ») afin que l'ouvrage puisse circuler librement dans la famille.</p>
      <p class="doux">Aucune connaissance en généalogie n'est nécessaire :
      laissez-vous porter par le récit.</p>
    </section>""" % _titre("Comment lire ce livre"))


def _biographie(base, f, masquer):
    paras = recit.biographie(base, f, masquer)
    if not paras:
        return ""
    corps = "".join('<p class="%s">%s</p>' % ("premier" if i == 0 else "", _e(p))
                    for i, p in enumerate(paras))
    return ('<section class="page bio" id="biographie">%s%s</section>'
            % (_titre("Biographie"), corps))


def _filiation(base, f, masquer):
    d = chapitres.filiation(base, f, masquer)
    if not d["parents"] and not d["fratrie"]:
        return ""
    lignes = "".join(
        '<div class="paire"><span class="role">%s</span><span>%s</span></div>'
        % (_e(p["role"]), _e(p["nom"])) for p in d["parents"])
    if d["fratrie"]:
        noms = ", ".join("%s%s" % (_e(x["nom"]),
                                   (" <span class='doux'>(%s)</span>" % _e(x["periode"]))
                                   if x["periode"] else "")
                         for x in d["fratrie"])
        lignes += ('<div class="fratrie"><span class="role" style="display:block;'
                   'text-align:center;margin-bottom:6px">Frères et sœurs</span>%s</div>' % noms)
    return '<section class="page" id="filiation">%s%s</section>' % (_titre("Filiation"), lignes)


def _unions(base, f, masquer):
    us = chapitres.unions(base, f, masquer)
    if not us:
        return ""
    blocs = []
    for i, u in enumerate(us):
        tete = u["conjoint"] or "Conjoint·e non identifié·e"
        quoi = " ".join(x for x in (u["quand"],
                                    ("à %s" % u["lieu"]) if u["lieu"] else "") if x)
        enfants = ""
        if u["enfants"]:
            noms = ", ".join(_e(e["nom"]) for e in u["enfants"])
            n = len(u["enfants"])
            enfants = ('<div class="enfants"><span class="et">%d enfant%s</span>%s</div>'
                       % (n, "s" if n > 1 else "", noms))
        sep = '<hr class="filet">' if i else ""
        blocs.append('%s<div class="union"><span class="couple">%s</span>%s%s</div>'
                     % (sep, _e(tete),
                        ('<span class="quand">%s</span>' % _e(quoi)) if quoi else "", enfants))
    titre = _TITRES["unions"] % ("s" if len(us) > 1 else "")
    return '<section class="page" id="unions">%s%s</section>' % (_titre(titre), "".join(blocs))


def _ascendance(base, f, masquer, section):
    gens = ascendance.chapitre(base, f["id"], section.get("generations", 4), masquer)
    if not gens:
        return ""
    blocs = []
    for bloc in gens:
        entrees = []
        for a in bloc["ancetres"]:
            if a["repet"]:
                corps = ('<strong>%s</strong> <span class="doux">— déjà présenté·e (Sosa %d)</span>'
                         % (_e(a["nom"]), a["repet"]))
            else:
                per = (' <span class="doux">(%s)</span>' % _e(a["periode"])) if a["periode"] else ""
                note = (' — %s' % _e(a["notice"])) if a["notice"] else ""
                corps = '<strong>%s</strong>%s%s' % (_e(a["nom"]), per, note)
            entrees.append('<div class="aieul"><span class="sosa">%d</span>'
                           '<span class="txt">%s</span></div>' % (a["sosa"], corps))
        blocs.append('<div class="gen"><h3>%s</h3>%s</div>'
                     % (_e(bloc["titre"]), "".join(entrees)))
    return '<section class="page" id="ascendance">%s%s</section>' % (_titre("Les aïeux"), "".join(blocs))


def _descendance(base, f, masquer, section):
    gens = descendance.chapitre(base, f["id"], section.get("generations", 3), masquer)
    if not gens:
        return ""
    blocs = []
    for bloc in gens:
        entrees = []
        for p in bloc["personnes"]:
            per = (' <span class="doux">(%s)</span>' % _e(p["periode"])) if p["periode"] else ""
            note = (' — %s' % _e(p["notice"])) if p["notice"] else ""
            entrees.append('<div class="aieul"><span class="sosa">%s</span>'
                           '<span class="txt"><strong>%s</strong>%s%s</span></div>'
                           % (_e(p["numero"]), _e(p["nom"]), per, note))
        blocs.append('<div class="gen"><h3>%s</h3>%s</div>'
                     % (_e(bloc["titre"]), "".join(entrees)))
    return ('<section class="page" id="descendance">%s%s</section>'
            % (_titre("La descendance"), "".join(blocs)))


def _album(f, lire_media):
    """Album des photos rattachées au référent (images intégrées, légendes).
    Saute le portrait déjà présent en couverture (évite de l'encoder 2 fois)."""
    if not lire_media:
        return ""
    portrait = _media_principal(f)
    figs = []
    for m in (f.get("medias") or []):
        fic = _fichier_media(m)
        if fic and fic == portrait:
            continue
        uri = lire_media(fic) if fic else ""
        if not uri:
            continue
        titre = _e(m.get("titre", "")) if isinstance(m, dict) else ""
        figs.append('<figure class="photo"><img alt="" src="%s">%s</figure>'
                    % (uri, ('<figcaption>%s</figcaption>' % titre) if titre else ""))
    if not figs:
        return ""
    return ('<section class="page album" id="album">%s<div class="galerie">%s</div></section>'
            % (_titre("Album"), "".join(figs)))


def _texte_libre(section):
    """Section de texte saisi par l'utilisateur (préface, dédicace, remerciements,
    introduction, chapitre personnel). Une ligne = un paragraphe. Vide -> "" (la
    section n'apparaît alors ni dans le corps ni au sommaire)."""
    txt = (section.get("texte") or "").strip()
    if not txt:
        return ""
    t = section.get("type")
    # « chapitre » : titre libre ; les autres : titre fixe du type.
    titre = ((section.get("titre") or "").strip()
             or _TITRES_TEXTE.get(t) or "Chapitre")
    paras = [p for p in txt.split("\n") if p.strip()]
    corps = "".join('<p class="%s">%s</p>' % ("premier" if i == 0 else "", _e(p))
                    for i, p in enumerate(paras))
    classe = "page dedicace" if t == "dedicace" else "page"
    return '<section class="%s" id="%s">%s%s</section>' % (
        classe, _e(_ancre(section)), _titre(titre), corps)


def _chronologie(base, f, masquer):
    frise = annexes.frise(base, f, masquer)
    if not frise:
        return ""
    rows = "".join('<div class="frise-e"><span class="an">%d</span>'
                   '<span class="ev">%s</span></div>' % (e["annee"], _e(e["texte"]))
                   for e in frise)
    return '<section class="page" id="chronologie">%s%s</section>' % (_titre("Chronologie"), rows)


def _index(base, f, masquer):
    idx = annexes.index(base, f, masquer)
    if not idx["noms"] and not idx["lieux"]:
        return ""
    body = ""
    if idx["noms"]:
        body += ('<h3>Personnes</h3><p class="index-liste">%s</p>'
                 % ", ".join(_e(n) for n in idx["noms"]))
    if idx["lieux"]:
        body += ('<h3>Lieux</h3><p class="index-liste">%s</p>'
                 % ", ".join(_e(l) for l in idx["lieux"]))
    return '<section class="page" id="index">%s%s</section>' % (_titre("Index"), body)


_RENDUS = {
    "comment_lire": lambda base, f, m, s: _comment_lire(),
    "preface": lambda base, f, m, s: _texte_libre(s),
    "dedicace": lambda base, f, m, s: _texte_libre(s),
    "remerciements": lambda base, f, m, s: _texte_libre(s),
    "introduction": lambda base, f, m, s: _texte_libre(s),
    "chapitre": lambda base, f, m, s: _texte_libre(s),
    "biographie": lambda base, f, m, s: _biographie(base, f, m),
    "chronologie": lambda base, f, m, s: _chronologie(base, f, m),
    "filiation": lambda base, f, m, s: _filiation(base, f, m),
    "unions": lambda base, f, m, s: _unions(base, f, m),
    "ascendance": lambda base, f, m, s: _ascendance(base, f, m, s),
    "descendance": lambda base, f, m, s: _descendance(base, f, m, s),
    "index": lambda base, f, m, s: _index(base, f, m),
}


# Sections de texte/ouverture réutilisées telles quelles dans le livret
# d'ascendance (les sections « données d'UNE personne » n'y ont pas de sens).
_SECTIONS_OUVERTURE = ("comment_lire", "preface", "dedicace", "remerciements",
                       "introduction", "chapitre")


def _mb(cx, y, w, h, p):
    """Une boîte du mini-arbre : nom (tronqué) + période. "" si personne absente."""
    if not p or not p.get("nom"):
        return ""
    x = cx - w / 2
    nom = p["nom"]
    nom = nom if len(nom) <= 22 else nom[:21] + "…"
    per = ('<text x="%g" y="%g" class="mp" text-anchor="middle">%s</text>'
           % (cx, y + h - 6, _e(p["periode"]))) if p.get("periode") else ""
    return ('<rect x="%g" y="%g" width="%g" height="%g" rx="4" class="mb"/>'
            '<text x="%g" y="%g" class="mn" text-anchor="middle">%s</text>%s'
            % (x, y, w, h, cx, y + 15, _e(nom), per))


def _mini_arbre(fam):
    """Mini-arbre du chapitre : les 4 aïeux (haut), le couple (milieu), les
    enfants (bas). SVG autonome, sobre, aux couleurs du thème."""
    a = fam.get("aieux") or {}
    pere, mere = fam.get("pere"), fam.get("mere")
    enfants = [e for e in (fam.get("enfants") or []) if e.get("nom")]
    W, w, h = 620, 138, 34
    xs = {"pp": 78, "pm": 236, "mp": 384, "mm": 542}    # 4 aïeux
    xpere, xmere = 157, 463                              # couple
    boxes, liens = [], []
    for cle, cx in xs.items():
        if a.get(cle):
            boxes.append(_mb(cx, 6, w, h, a[cle]))
    # liens aïeux -> couple
    if pere and (a.get("pp") or a.get("pm")):
        for cle in ("pp", "pm"):
            if a.get(cle):
                liens.append('<path class="ml" d="M%g 40 L%g 80"/>' % (xs[cle], xpere))
    if mere and (a.get("mp") or a.get("mm")):
        for cle in ("mp", "mm"):
            if a.get(cle):
                liens.append('<path class="ml" d="M%g 40 L%g 80"/>' % (xs[cle], xmere))
    if pere:
        boxes.append(_mb(xpere, 80, w, h, pere))
    if mere:
        boxes.append(_mb(xmere, 80, w, h, mere))
    # couple -> enfants
    ycpl, ybus, yenf = 114, 138, 158
    mid = (xpere + xmere) / 2
    if enfants:
        montre = enfants[:6]
        n = len(montre)
        pas = min(150, (W - 40) / max(1, n))
        x0 = W / 2 - pas * (n - 1) / 2
        xchild = [x0 + i * pas for i in range(n)]
        liens.append('<path class="ml" d="M%g %g L%g %g"/>' % (mid, ycpl, mid, ybus))
        liens.append('<path class="ml" d="M%g %g L%g %g"/>'
                     % (min(xchild), ybus, max(xchild), ybus))
        for i, e in enumerate(montre):
            liens.append('<path class="ml" d="M%g %g L%g %g"/>' % (xchild[i], ybus, xchild[i], yenf))
            boxes.append(_mb(xchild[i], yenf, min(w, pas - 8), h, e))
        H = 200
        if len(enfants) > 6:
            boxes.append('<text x="%g" y="196" class="mp" text-anchor="middle">+%d autre(s)</text>'
                         % (W / 2, len(enfants) - 6))
    else:
        H = 128
    if not boxes:
        return ""
    return ('<svg class="mini-arbre" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" '
            'role="img" aria-label="Mini-arbre de la famille">%s%s</svg>'
            % (W, H, "".join(liens), "".join(boxes)))


def _fiche_famille(fam):
    """Fiche familiale encadrée : couple, mariage, enfants (style tableau)."""
    def lg(role, p):
        if not p or not p.get("nom"):
            return ""
        per = (' <span class="per">(%s)</span>' % _e(p["periode"])) if p.get("periode") else ""
        return ('<div class="lg"><span class="r">%s</span><span>%s%s</span></div>'
                % (role, _e(p["nom"]), per))
    lignes = lg("Père", fam.get("pere")) + lg("Mère", fam.get("mere"))
    mar = fam.get("mariage") or {}
    dt = mar.get("date") or ""
    # « le 24/06/1976 » pour une date complète, « en 1976 » pour une simple année.
    quand = ("%s %s" % ("le" if ("/" in dt or " " in dt.strip()) else "en", dt)) if dt else ""
    quoi = " ".join(x for x in [quand,
                                ("à %s" % mar["lieu"]) if mar.get("lieu") else ""] if x)
    if quoi:
        lignes += '<div class="lg"><span class="r">Mariage</span><span>%s</span></div>' % _e(quoi)
    enf = fam.get("enfants") or []
    if enf:
        items = ", ".join("%s%s" % (_e(e["nom"]),
                                    (" <span class='per'>(%s)</span>" % _e(e["periode"]))
                                    if e.get("periode") else "") for e in enf)
        lignes += ('<div class="enf"><span class="r">%d enfant%s</span>%s</div>'
                   % (len(enf), "s" if len(enf) > 1 else "", items))
    if not lignes:
        return ""
    return '<div class="fiche"><h3>Fiche familiale</h3>%s</div>' % lignes


def _chapitre_couple(ch):
    """Une page-chapitre d'un couple (livret d'ascendance)."""
    paras = ch.get("paras") or []
    corps = "".join('<p class="%s">%s</p>' % ("premier" if i == 0 else "", _e(p))
                    for i, p in enumerate(paras))
    if not corps and not ch.get("renvoi"):
        corps = '<p class="doux premier">Peu d\'éléments connus à ce jour.</p>'
    num = "Chapitre %d" % ch["num"]
    if ch.get("sosa"):
        num += " · Sosa %s" % ch["sosa"]
    fam = ch.get("famille") or {}
    arbre = _mini_arbre(fam) if fam else ""
    fiche = _fiche_famille(fam) if fam else ""
    renvoi = ('<p class="renvoi">%s</p>' % _e(ch["renvoi"])) if ch.get("renvoi") else ""
    return ('<section class="page chap" id="chap%d"><div class="chap-num">%s</div>'
            '%s%s%s%s%s</section>' % (ch["num"], _e(num), _titre(ch["titre"]),
                                      arbre, corps, fiche, renvoi))


def _rendre_ascendance(base, livre, f, lire_media, masquer):
    """Livret d'ascendance complète : ouverture + parties par génération +
    chapitres par couple + index. Voir services.livre.livret_ascendance."""
    mep = livre.get("mise_en_page", {})
    gen = int(livre.get("generations") or 4)
    parties = livret_ascendance.chapitres(base, livre.get("referent"), gen, masquer)

    corps = [_couverture(livre, f, lire_media)]
    # Sommaire : les parties (générations).
    liens = ['<li><span class="num">%s</span><a href="#partie%d">%s</a>'
             '<span class="pointille"></span></li>' % (_e("%02d" % (i + 1)), p["generation"],
                                                       _e(p["titre"]))
             for i, p in enumerate(parties)]
    if liens:
        corps.append('<section class="page sommaire" id="sommaire">%s<ol>%s</ol></section>'
                     % (_titre("Sommaire"), "".join(liens)))
    # Sections d'ouverture actives (dans leur ordre), puis les chapitres.
    for s in livre.get("sections", []):
        if s.get("actif") and s.get("type") in _SECTIONS_OUVERTURE:
            rendu = _RENDUS.get(s["type"])
            html_s = rendu(base, f, masquer, s) if rendu else ""
            if html_s:
                corps.append(html_s)
    for i, p in enumerate(parties):
        if p["generation"] >= 1:
            corps.append('<section class="page partie" id="partie%d">'
                         '<div class="sur">Génération %d</div>%s</section>'
                         % (p["generation"], p["generation"], _titre(p["titre"])))
        else:
            corps.append('<span id="partie%d"></span>' % p["generation"])
        for ch in p["chapitres"]:
            corps.append(_chapitre_couple(ch))
    # Index en fin d'ouvrage s'il est actif.
    if any(s.get("actif") and s.get("type") == "index" for s in livre.get("sections", [])):
        corps.append(_index(base, f, masquer))

    return """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titre}</title>
<style>{css}</style></head>
<body><div class="livre">{corps}</div></body></html>""".format(
        titre=_e(livre.get("titre", "Livre")), css=_css(mep),
        corps="".join(x for x in corps if x))


def rendre(base, livre, lire_media=None):
    """Renvoie le document HTML complet (chaîne) du livre. `lire_media` est un
    callable(fichier) -> data-URI (ou "") pour intégrer photos et portrait."""
    ref = livre.get("referent")
    f = personnes.fiche(base, ref) if ref else None
    if not f:
        raise ValueError("La personne de ce livre est introuvable.")
    masquer = bool(livre.get("masquer_vivants", True))
    if livre.get("type") == "ascendance":
        return _rendre_ascendance(base, livre, f, lire_media, masquer)
    actives = [s for s in livre.get("sections", []) if s.get("actif")]

    corps = [_couverture(livre, f, lire_media)]
    liens = []
    for s in actives:
        t = s.get("type")
        if t == "couverture":
            continue
        if t == "album":
            html_section = _album(f, lire_media)
        else:
            rendu = _RENDUS.get(t)
            if not rendu:
                continue
            html_section = rendu(base, f, masquer, s)
        if html_section:
            corps.append(html_section)
            # Libellé du sommaire : titre libre d'un chapitre, sinon libellé du type.
            if t == "chapitre":
                label = (s.get("titre") or "").strip() or "Chapitre"
            else:
                label = _LIB_SOMMAIRE.get(t)
            if label:
                n = len(liens) + 1
                liens.append('<li><span class="num">%s</span>'
                             '<a href="#%s">%s</a><span class="pointille"></span></li>'
                             % (_e("%02d" % n), _e(_ancre(s)), _e(label)))
    if liens:
        sommaire = ('<section class="page sommaire" id="sommaire">%s<ol>%s</ol></section>'
                    % (_titre("Sommaire"), "".join(liens)))
        corps.insert(1, sommaire)

    return """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titre}</title>
<style>{css}</style></head>
<body><div class="livre">{corps}</div></body></html>""".format(
        titre=_e(livre.get("titre", "Livre")), css=_css(livre.get("mise_en_page", {})),
        corps="".join(corps))
