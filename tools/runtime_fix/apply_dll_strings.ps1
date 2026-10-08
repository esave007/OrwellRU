# Applies translated/dll_strings.json to an Assembly-CSharp.dll that is already patched (e.g. the installed
# one): every ldstr that still holds an English original from the json gets its translation. Strings that
# are translated already are left alone, so the script can be run again safely.
# (tools/PatchDll does the same starting from the original DLL.)
#
#   powershell -File apply_dll_strings.ps1 -Dll <Assembly-CSharp.dll> -Cecil <Mono.Cecil.dll> [-Out <file>]
param(
    [Parameter(Mandatory = $true)][string]$Dll,
    [Parameter(Mandatory = $true)][string]$Cecil,
    [string]$Out = ""
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Out) { $Out = $Dll }
Add-Type -Path $Cecil
# ConvertFrom-Json of PowerShell 5 rejects keys that differ only in case ("Log Out" / "Log out")
Add-Type -AssemblyName System.Web.Extensions
$serializer = New-Object System.Web.Script.Serialization.JavaScriptSerializer
$serializer.MaxJsonLength = [int]::MaxValue
$json = $serializer.DeserializeObject((Get-Content -Raw -Encoding UTF8 (Join-Path $here "..\..\translated\dll_strings.json")))
$map = New-Object 'System.Collections.Generic.Dictionary[string,string]'
foreach ($v in $json["translations"].Values) {
    $en = [string]$v["original"]; $ru = [string]$v["translation"]
    if ($en -and $ru -and $en -cne $ru) { $map[$en] = $ru }
}
$resolver = New-Object Mono.Cecil.DefaultAssemblyResolver
$resolver.AddSearchDirectory((Split-Path -Parent (Resolve-Path $Dll)))
$rp = New-Object Mono.Cecil.ReaderParameters
$rp.AssemblyResolver = $resolver
$rp.InMemory = $true
$asm = [Mono.Cecil.AssemblyDefinition]::ReadAssembly((Resolve-Path $Dll).Path, $rp)
$n = 0
foreach ($t in $asm.MainModule.GetTypes()) {
    foreach ($m in $t.Methods) {
        if (-not $m.HasBody) { continue }
        foreach ($i in $m.Body.Instructions) {
            if ($i.OpCode.Code -eq [Mono.Cecil.Cil.Code]::Ldstr -and $map.ContainsKey([string]$i.Operand)) {
                $i.Operand = $map[[string]$i.Operand]
                $n++
            }
        }
    }
}
if ($n -gt 0) { $asm.Write($Out) }
Write-Output "replaced $n strings"
