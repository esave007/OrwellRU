; Orwell: Ignorance is Strength — Russian Localization Installer
; InnoSetup 6.x script
; Author: eSave

#define MyAppName "Orwell:IS_RUS"
#define MyAppVersion "0.5.1 (beta)"
#define MyAppPublisher "eSave"
#define MyAppURL "https://steamcommunity.com/app/633060"
#define SteamAppID "633060"

[Setup]
AppId={{7F3A2B1C-E4D5-4F6A-8B9C-0D1E2F3A4B5C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={code:GetGameDir}
DirExistsWarning=no
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Orwell_IS_RUS_v0.5.1_beta
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
Uninstallable=yes
UninstallDisplayName={#MyAppName} v{#MyAppVersion}
CreateUninstallRegKey=yes
PrivilegesRequired=lowest

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Messages]
russian.BeveledLabel=Orwell: Ignorance is Strength — Русификатор v0.5.1 (beta)

[CustomMessages]
russian.GameNotFound=Игра Orwell: Ignorance is Strength не найдена!%n%nУкажите папку с игрой вручную (где находится Ignorance.exe).
russian.GameFound=Игра найдена автоматически:
russian.InvalidDir=В указанной папке не найден файл Ignorance.exe!%n%nУбедитесь, что вы выбрали правильную папку с игрой.
russian.BackupCreated=Резервная копия оригинальных файлов создана в папке _backup_ru
russian.InstallingFiles=Установка русификатора...
russian.BackupStep=Создание резервной копии оригинальных файлов...
russian.AlreadyInstalled=Обнаружена предыдущая установка русификатора.%nОригинальные файлы уже сохранены в _backup_ru.
russian.RestoreComplete=Оригинальные файлы восстановлены. Русификатор удалён.
russian.WelcomeLabel=Русификатор Orwell: Ignorance is Strength
russian.WelcomeDesc=Фан-перевод на русский язык (бета-версия).%n%nПеред установкой закройте игру, если она запущена.%n%nРусификатор работает только с лицензионной Steam-версией игры.

[Files]
; Patched game files
Source: "..\patches\resources.assets"; DestDir: "{app}\Ignorance_Data"; Flags: ignoreversion
Source: "..\patches\level0"; DestDir: "{app}\Ignorance_Data"; Flags: ignoreversion
Source: "..\patches\level1"; DestDir: "{app}\Ignorance_Data"; Flags: ignoreversion
Source: "..\patches\level2"; DestDir: "{app}\Ignorance_Data"; Flags: ignoreversion
Source: "..\patches\level3"; DestDir: "{app}\Ignorance_Data"; Flags: ignoreversion
Source: "..\patches\level4"; DestDir: "{app}\Ignorance_Data"; Flags: ignoreversion
Source: "..\patches\sharedassets3.assets"; DestDir: "{app}\Ignorance_Data"; Flags: ignoreversion
Source: "..\patches\Assembly-CSharp.dll"; DestDir: "{app}\Ignorance_Data\Managed"; Flags: ignoreversion

[Code]
var
  GameDir: String;
  GameDirFound: Boolean;

function GetSteamPath: String;
var
  SteamPath: String;
begin
  Result := '';
  // Try 64-bit registry first
  if RegQueryStringValue(HKLM, 'SOFTWARE\Wow6432Node\Valve\Steam', 'InstallPath', SteamPath) then
    Result := SteamPath
  else if RegQueryStringValue(HKLM, 'SOFTWARE\Valve\Steam', 'InstallPath', SteamPath) then
    Result := SteamPath
  else if RegQueryStringValue(HKCU, 'SOFTWARE\Valve\Steam', 'SteamPath', SteamPath) then
    Result := SteamPath;
end;

function FindGameInLibraryFolders(SteamPath: String): String;
var
  VdfPath: String;
  VdfContent: AnsiString;
  VdfText: String;
  I, J: Integer;
  LibPath: String;
  GamePath: String;
begin
  Result := '';

  // Check default steamapps first
  GamePath := SteamPath + '\steamapps\common\Orwell Ignorance is Strength';
  if FileExists(GamePath + '\Ignorance.exe') then
  begin
    Result := GamePath;
    Exit;
  end;

  // Parse libraryfolders.vdf for additional library paths
  VdfPath := SteamPath + '\steamapps\libraryfolders.vdf';
  if not FileExists(VdfPath) then
    Exit;

  if not LoadStringFromFile(VdfPath, VdfContent) then
    Exit;

  VdfText := String(VdfContent);

  // Find "path" entries in VDF
  I := 1;
  while I < Length(VdfText) do
  begin
    I := Pos('"path"', VdfText);
    if I = 0 then
      Break;

    // Skip past "path" and find the value
    I := I + 6;
    // Find opening quote of value
    J := I;
    while (J <= Length(VdfText)) and (VdfText[J] <> '"') do
      J := J + 1;
    J := J + 1; // skip opening quote
    I := J;
    // Find closing quote
    while (J <= Length(VdfText)) and (VdfText[J] <> '"') do
      J := J + 1;

    if J > I then
    begin
      LibPath := Copy(VdfText, I, J - I);
      // Replace double backslashes
      StringChangeEx(LibPath, '\\', '\', True);

      GamePath := LibPath + '\steamapps\common\Orwell Ignorance is Strength';
      if FileExists(GamePath + '\Ignorance.exe') then
      begin
        Result := GamePath;
        Exit;
      end;
    end;

    // Remove processed part to continue searching
    Delete(VdfText, 1, J);
    I := 1;
  end;
end;

function TryFindGameDir: String;
var
  SteamPath: String;
  InstallLoc: String;
begin
  Result := '';

  // Method 1: Direct Steam App registry key
  if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App {#SteamAppID}', 'InstallLocation', InstallLoc) then
  begin
    if FileExists(InstallLoc + '\Ignorance.exe') then
    begin
      Result := InstallLoc;
      Exit;
    end;
  end;

  // Method 2: Find Steam, then search library folders
  SteamPath := GetSteamPath;
  if SteamPath <> '' then
  begin
    Result := FindGameInLibraryFolders(SteamPath);
  end;
end;

function GetGameDir(Param: String): String;
begin
  if GameDir <> '' then
    Result := GameDir
  else
    Result := 'C:\Program Files (x86)\Steam\steamapps\common\Orwell Ignorance is Strength';
end;

procedure InitializeWizard;
begin
  GameDir := TryFindGameDir;
  GameDirFound := (GameDir <> '');

  if GameDirFound then
  begin
    WizardForm.DirEdit.Text := GameDir;
    // Show info that game was found
    MsgBox(ExpandConstant('{cm:GameFound}') + #13#10 + GameDir, mbInformation, MB_OK);
  end
  else
  begin
    MsgBox(ExpandConstant('{cm:GameNotFound}'), mbInformation, MB_OK);
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Dir: String;
begin
  Result := True;

  if CurPageID = wpSelectDir then
  begin
    Dir := WizardForm.DirEdit.Text;
    if not FileExists(Dir + '\Ignorance.exe') then
    begin
      MsgBox(ExpandConstant('{cm:InvalidDir}'), mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure BackupFile(SourceDir, FileName, BackupDir: String);
begin
  if FileExists(SourceDir + '\' + FileName) and not FileExists(BackupDir + '\' + FileName) then
  begin
    ForceDirectories(BackupDir);
    CopyFile(SourceDir + '\' + FileName, BackupDir + '\' + FileName, True);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  AppDir, DataDir, ManagedDir, BackupDir, BackupManaged: String;
begin
  if CurStep = ssInstall then
  begin
    AppDir := WizardDirValue;
    DataDir := AppDir + '\Ignorance_Data';
    ManagedDir := DataDir + '\Managed';
    BackupDir := AppDir + '\_backup_ru';
    BackupManaged := BackupDir + '\Managed';

    // Create backup of original files (only if not already backed up)
    if not DirExists(BackupDir) then
    begin
      ForceDirectories(BackupDir);
      ForceDirectories(BackupManaged);

      BackupFile(DataDir, 'resources.assets', BackupDir);
      BackupFile(DataDir, 'level0', BackupDir);
      BackupFile(DataDir, 'level1', BackupDir);
      BackupFile(DataDir, 'level2', BackupDir);
      BackupFile(DataDir, 'level3', BackupDir);
      BackupFile(DataDir, 'level4', BackupDir);
      BackupFile(DataDir, 'sharedassets3.assets', BackupDir);
      BackupFile(ManagedDir, 'Assembly-CSharp.dll', BackupManaged);
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDir, DataDir, ManagedDir, BackupDir, BackupManaged: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    AppDir := ExpandConstant('{app}');
    DataDir := AppDir + '\Ignorance_Data';
    ManagedDir := DataDir + '\Managed';
    BackupDir := AppDir + '\_backup_ru';
    BackupManaged := BackupDir + '\Managed';

    // Restore original files from backup
    if DirExists(BackupDir) then
    begin
      if FileExists(BackupDir + '\resources.assets') then
        CopyFile(BackupDir + '\resources.assets', DataDir + '\resources.assets', False);
      if FileExists(BackupDir + '\level0') then
        CopyFile(BackupDir + '\level0', DataDir + '\level0', False);
      if FileExists(BackupDir + '\level1') then
        CopyFile(BackupDir + '\level1', DataDir + '\level1', False);
      if FileExists(BackupDir + '\level2') then
        CopyFile(BackupDir + '\level2', DataDir + '\level2', False);
      if FileExists(BackupDir + '\level3') then
        CopyFile(BackupDir + '\level3', DataDir + '\level3', False);
      if FileExists(BackupDir + '\level4') then
        CopyFile(BackupDir + '\level4', DataDir + '\level4', False);
      if FileExists(BackupDir + '\sharedassets3.assets') then
        CopyFile(BackupDir + '\sharedassets3.assets', DataDir + '\sharedassets3.assets', False);
      if FileExists(BackupManaged + '\Assembly-CSharp.dll') then
        CopyFile(BackupManaged + '\Assembly-CSharp.dll', ManagedDir + '\Assembly-CSharp.dll', False);

      // Clean up backup folder
      DelTree(BackupDir, True, True, True);

      MsgBox(ExpandConstant('{cm:RestoreComplete}'), mbInformation, MB_OK);
    end;
  end;
end;
