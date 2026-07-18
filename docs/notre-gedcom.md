# Le GEDCOM d'Arboriane

Arboriane importe et exporte du **GEDCOM 5.5.1** (encodage UTF-8 à l'export).
Tout ce que vous saisissez est écrit en balises **standard** quand elles
existent ; les quelques extensions propres au logiciel commencent par un
souligné `_` (comme le veut la norme pour les balises non standard). Ce
document les liste pour que rien ne soit une « boîte noire ».

## Encodage à l'import (L12)

À l'import, Arboriane **détecte l'encodage** du fichier (au lieu de supposer
UTF-8) : BOM (UTF-8 / UTF-16) puis balise `1 CHAR` de l'en-tête —
`UTF-8`, `ANSI` (Windows-1252), `IBMPC` (CP850), `UNICODE` (UTF-16), `ANSEL`
(ancienne norme GEDCOM, décodée au mieux, diacritiques courants). Les accents
des vieux fichiers sont ainsi rétablis automatiquement. L'encodage détecté est
affiché dans l'écran d'import.

## Validation des dates (L12)

L'écran **Qualité des sources** signale les *dates douteuses* : celles qui ne
suivent pas une forme reconnue (jour mois année, année seule, `ABT/BEF/AFT…`,
intervalles `BET…AND…`, calendrier républicain `@#DFRENCH R@…`, ou leurs
équivalents français). Elles restent enregistrées telles quelles — c'est juste
une aide pour repérer ce qui s'exportera mal.

## Extensions propres à Arboriane (balises `_`)

| Balise | Niveau | Sens | Standard de repli |
|--------|--------|------|-------------------|
| `_SOSA` | individu | Numéro de Sosa figé (voir « Parenté avancée ») | recalculable, non exporté par défaut |
| `_TYPE` | dépôt (REPO) | Type de dépôt (Archives dép., mairie…) | — |
| `_ROLE` | citation (SOUR) | Rôle de la personne dans l'acte (témoin, parrain…) | note de la citation |

Les autres informations utilisent des balises **standard** : `NAME`
(avec `NPFX`/`NSFX`/`SPFX`/`NICK`/`_MARNM` pour le nom marital), `SEX`
(M/F/U + X/N en extension GEDCOM 5.5.1), `BIRT`/`DEAT`/`MARR` et autres
événements, `OCCU`, `RESI`, `OBJE`/`FILE`, `SOUR`/`PAGE`/`QUAY`, `REPO`/`CALN`,
`RESN`, `NOTE` (avec `CONC`/`CONT` découpés à 255 octets).

## Principe : rien n'est perdu

Les événements gardent leur **texte de lieu et de date d'origine** ; les données
dérivées (Sosa, implexe, index, lieux hiérarchiques) sont **recalculables** et
ne remplacent jamais la source. Un aller-retour export → import → export
produit un fichier **identique**.
