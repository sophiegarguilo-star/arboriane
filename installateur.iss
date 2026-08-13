; ============================================================================
;  Arboriane — script d'installation Inno Setup
;  Génère un installeur Windows : raccourcis Bureau + menu Démarrer,
;  désinstallation propre. Aucune donnée n'est touchée (les arbres vivent dans
;  Documents\Arboriane, hors du dossier d'installation).
;
;  Pour compiler : installer Inno Setup 6 (https://jrsoftware.org/isdl.php),
;  puis double-cliquer ce fichier et cliquer « Compile », ou lancer
;  outils/deployer.py --release (qui lance d'abord la barrière : tests + banc).
;  Ne pas compiler cet installeur à la main : la barrière serait contournée.
; ============================================================================

#define AppName "Arboriane"
#define AppVersion "1.10.4"
#define AppPublisher "Arboriane"
#define AppExe "Arboriane.exe"

[Setup]
AppId={{9E1B7A54-2C3D-4F6A-9B10-ARBORIANE0001}}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; L'utilisateur CHOISIT le dossier d'installation en install neuve ; sur une
; mise à jour, le dossier existant est réutilisé automatiquement (auto).
DisableDirPage=auto
; Ferme Arboriane s'il tourne, pour pouvoir remplacer les fichiers.
CloseApplications=yes
RestartApplications=no
; installation sans droits administrateur (dans le profil de l'utilisateur)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist
OutputBaseFilename=Installer-Arboriane
SetupIconFile=web\favicon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; visuels de l'assistant, aux couleurs d'Arboriane
WizardImageFile=installateur\wizard-grande.bmp
WizardSmallImageFile=installateur\wizard-petite.bmp
WizardImageStretch=yes
DisableWelcomePage=no
AppComments=Généalogie 100 % locale et privée
SetupLogging=no

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le &Bureau"; GroupDescription: "Raccourcis :"

[Files]
; tout le dossier one-folder produit par PyInstaller
Source: "dist\Arboriane\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Désinstaller {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Lancer {#AppName} maintenant"; Flags: nowait postinstall skipifsilent

[Code]
{ Détecte une version déjà installée (clé de désinstallation Inno) pour
  afficher un message de mise à jour rassurant. Les données de l'utilisateur
  (arbres, sources, photos) vivent dans Documents\Arboriane, HORS du dossier
  d'installation : une mise à jour ne les touche jamais. }
function VersionPrecedenteInstallee(): Boolean;
var
  chemin: String;
begin
  chemin := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{9E1B7A54-2C3D-4F6A-9B10-ARBORIANE0001}_is1';
  Result := RegKeyExists(HKCU, chemin) or RegKeyExists(HKLM, chemin);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if VersionPrecedenteInstallee() then
    MsgBox('Une version d''Arboriane est déjà installée sur cet ordinateur.'
      + #13#10#13#10
      + 'L''assistant va la METTRE À JOUR vers la version ' + '{#AppVersion}' + '.'
      + #13#10#13#10
      + 'Vos arbres, sources et photos (rangés dans Documents\Arboriane) '
      + 'sont CONSERVÉS : la mise à jour ne remplace que le programme.'
      + #13#10#13#10
      + 'Si Arboriane est ouvert, fermez-le avant de continuer.',
      mbInformation, MB_OK);
end;
