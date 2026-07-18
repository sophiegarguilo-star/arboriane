# Signaler une faille de sécurité

Merci de **ne pas ouvrir d'issue publique** pour une faille : une issue est
lisible par tous, y compris par qui voudrait en abuser avant qu'un correctif
n'existe.

Écrivez à **arboriane.app@gmail.com**, avec « sécurité » dans l'objet.

Décrivez ce que vous avez trouvé, comment le reproduire, et ce que cela permet
de faire. Une capture ou un fichier d'exemple aident beaucoup — mais **n'envoyez
jamais votre généalogie réelle** : une famille de démonstration suffit toujours à
démontrer un défaut.

Vous recevrez un accusé de réception. Le correctif est publié dès qu'il est prêt
et vérifié, avec mention de votre signalement si vous le souhaitez.

## Ce qui est concerné

Arboriane est une application **locale**. Son serveur n'écoute que sur
`127.0.0.1`, aucune donnée ne quitte la machine, et il n'existe aucun compte ni
service en ligne. Les failles qui nous intéressent sont donc celles qui
permettraient :

- de lire ou d'écrire un fichier **hors du dossier de l'arbre** ouvert ;
- d'exécuter du code par un fichier GEDCOM, un scan ou une image importés ;
- d'atteindre l'application depuis une **autre machine** du réseau, ou depuis un
  site web ouvert dans le même navigateur ;
- d'exposer la clé de l'assistant, chiffrée localement.

## Ce qui n'en est pas

L'installateur **n'est pas signé numériquement** : Windows affiche « éditeur
inconnu ». Ce n'est pas une faille, c'est un choix — un certificat de signature
est payant, et Arboriane est gratuite. Chaque version publie l'empreinte SHA-256
de son installateur pour que vous puissiez vérifier ce que vous téléchargez.

Les versions **antérieures à la dernière** ne reçoivent pas de correctif : mettez
à jour.
