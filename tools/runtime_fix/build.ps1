# Builds OrwellRuFix.dll and injects "OrwellRuFix.Loader.Init()" at the start of
# TMPro.TextMeshProUGUI.Awake in Assembly-CSharp.dll (idempotent).
#
#   powershell -File build.ps1 -Managed "<game>\Ignorance_Data\Managed" [-Cecil <Mono.Cecil.dll>] [-Out <dir>]
#
# Needs only the .NET Framework 4 C# compiler that ships with Windows and Mono.Cecil
# (>= 0.10, e.g. from NuGet; the build was tested with 0.10.4).
# Without -Out the files in -Managed are replaced (back them up first).
param(
    [Parameter(Mandatory = $true)][string]$Managed,
    [string]$Cecil = "",
    [string]$Out = ""
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Out) { $Out = $Managed }
if (-not $Cecil) { $Cecil = Join-Path $Managed "Mono.Cecil.dll" }  # Cecil >= 0.10 (e.g. from NuGet)
New-Item -ItemType Directory -Force $Out | Out-Null

$csc = Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe"
$refs = "mscorlib.dll", "System.dll", "System.Core.dll", "UnityEngine.dll", "UnityEngine.UI.dll", "Assembly-CSharp.dll", "Assembly-CSharp-firstpass.dll" |
    ForEach-Object { "/r:" + (Join-Path $Managed $_) }
$tmpDll = Join-Path $env:TEMP "OrwellRuFix.dll"
& $csc /nologo /codepage:65001 /target:library /optimize+ /nostdlib+ /noconfig /out:$tmpDll @refs (Join-Path $here "OrwellRuFix.cs")
if ($LASTEXITCODE -ne 0) { throw "compilation failed" }

Add-Type -Path $Cecil
# Unity 5.6 runs a .NET 2.0 profile Mono: mark the plugin as a v2 assembly.
$plugin = [Mono.Cecil.AssemblyDefinition]::ReadAssembly($tmpDll)
$plugin.MainModule.Runtime = [Mono.Cecil.TargetRuntime]::Net_2_0
$plugin.Write((Join-Path $Out "OrwellRuFix.dll"))

$resolver = New-Object Mono.Cecil.DefaultAssemblyResolver
$resolver.AddSearchDirectory($Managed)
$rp = New-Object Mono.Cecil.ReaderParameters
$rp.AssemblyResolver = $resolver
$rp.InMemory = $true
$asm = [Mono.Cecil.AssemblyDefinition]::ReadAssembly((Join-Path $Managed "Assembly-CSharp.dll"), $rp)
$awake = $asm.MainModule.GetType("TMPro.TextMeshProUGUI").Methods | Where-Object { $_.Name -eq "Awake" }
$first = $awake.Body.Instructions[0]
if ($first.OpCode.Code -eq "Call" -and $first.Operand.DeclaringType.FullName -eq "OrwellRuFix.Loader") {
    Write-Host "Assembly-CSharp.dll already has the loader call"
} else {
    $pluginAsm = [Mono.Cecil.AssemblyDefinition]::ReadAssembly((Join-Path $Out "OrwellRuFix.dll"))
    $init = $pluginAsm.MainModule.GetType("OrwellRuFix.Loader").Methods | Where-Object { $_.Name -eq "Init" }
    $il = $awake.Body.GetILProcessor()
    $il.InsertBefore($first, $il.Create([Mono.Cecil.Cil.OpCodes]::Call, $asm.MainModule.ImportReference($init)))
    $asm.Write((Join-Path $Out "Assembly-CSharp.dll"))
    Write-Host "loader call injected into TMPro.TextMeshProUGUI.Awake"
}
