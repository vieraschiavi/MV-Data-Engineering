; © 2026 Martín Viera. Todos los derechos reservados.
;
; Instalador de Windows de MV Data Engineering (Inno Setup 6).
;
; Qué resuelve, y por qué no alcanzaba con el .bat portable
; ---------------------------------------------------------
; El .bat exige que la máquina tenga Python 3.11+ en el PATH y, la primera vez,
; se baja medio giga de wheels: si no hay internet, si la empresa filtra PyPI o
; si el "python" del PATH es el stub de la Microsoft Store, no arranca — y el
; error que ve la persona es una pared de texto de pip.
;
; Este instalador lleva el intérprete y TODAS las dependencias adentro. No pide
; Python, no baja nada al instalar, no necesita permisos de administrador.
;
; Sin privilegios de administrador (`PrivilegesRequired=lowest`) a propósito:
; en una PC corporativa pedir admin es exactamente lo que convierte "lo instalo
; y lo pruebo" en "abro un ticket". Se instala en la carpeta del usuario.
;
; Se construye en un runner de Windows (.github/workflows/instalador-mvde.yml),
; que además lo INSTALA, lo arranca, le pide una página y lo desinstala: el
; desarrollo pasa en Linux, donde esto no se puede ni compilar ni ejecutar.

#define Nombre       "MV Data Engineering"
#define Version      "1.0.0"
#define Autor        "Martín Viera"
; Los accesos directos apuntan DIRECTO a pythonw.exe del runtime embebido.
; Un .cmd o un .bat de por medio hace parpadear una consola negra cada vez
; que se abre el programa, y encima queda esa ventana abierta detrás.
; pythonw.exe no abre ninguna: por eso el lanzador registra todo en un
; archivo y avisa los errores con un cuadro de diálogo (ver lanzador.py).
#define Motor        "runtime\pythonw.exe"
#define Lanzador     "packaging\lanzador.py"

[Setup]
AppId={{8F3C2A61-4D7E-4B29-9A15-6E0B2C7D48A3}
AppName={#Nombre}
AppVersion={#Version}
AppPublisher={#Autor}
DefaultDirName={autopf}\{#Nombre}
DefaultGroupName={#Nombre}
DisableProgramGroupPage=yes
; La carpeta se puede elegir: alguien con el disco C lleno tiene que poder
; mandarlo a otra unidad sin pelearse con el instalador.
DisableDirPage=no
PrivilegesRequired=lowest
OutputBaseFilename=MV_DataEngineering_Setup
OutputDir=..\dist_instalador
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
SetupIconFile=mvde.ico
UninstallDisplayIcon={app}\packaging\mvde.ico
; `x64compatible` existe recién desde Inno Setup 6.3: en 6.2 el compilador
; CORTA con error. Pero `x64` a secas, en 6.3+, se sustituye por `x64os`, que
; NO deja instalar en Windows ARM64 por emulación — y las laptops ARM ya se
; venden. Se elige según la versión del compilador y quedan las dos cosas: se
; construye con 6.2 y, con 6.3+, instala también en ARM64.
#if VER >= EncodeVer(6,3,0)
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
#else
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
#endif
; El runtime embebido pesa; sin esto Inno estima de menos y Windows avisa mal
; sobre el espacio libre.
ExtraDiskSpaceRequired=520000000

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "escritorio"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Todo lo que produjo preparar_runtime.ps1 en la carpeta de staging.
Source: "..\dist_app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#Nombre}";            Filename: "{app}\{#Motor}"; Parameters: """{app}\{#Lanzador}"""; IconFilename: "{app}\packaging\mvde.ico"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#Nombre}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#Nombre}";      Filename: "{app}\{#Motor}"; Parameters: """{app}\{#Lanzador}"""; IconFilename: "{app}\packaging\mvde.ico"; WorkingDir: "{app}"; Tasks: escritorio

[Run]
Filename: "{app}\{#Motor}"; Parameters: """{app}\{#Lanzador}"""; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#Nombre}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Lo que el programa escribe DESPUÉS de instalarse: cachés de Python y el
; entorno de trabajo. Sin esto la desinstalación deja la carpeta a medio
; borrar y una reinstalación posterior arranca sucia.
Type: filesandordirs; Name: "{app}\runtime\Lib\site-packages\__pycache__"
Type: filesandordirs; Name: "{app}\.mvde_tmp"
Type: dirifempty;     Name: "{app}"
