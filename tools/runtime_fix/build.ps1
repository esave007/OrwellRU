# Builds OrwellRuFix.dll and injects "OrwellRuFix.Loader.Init()" at the start of
# TMPro.TextMeshProUGUI.Awake in Assembly-CSharp.dll, then points the DateTime.ToString/Parse calls of the
# game's date/clock code at OrwellRuFix.RuDate (Russian date and 24-hour clock). Idempotent.
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
$pluginAsm = [Mono.Cecil.AssemblyDefinition]::ReadAssembly((Join-Path $Out "OrwellRuFix.dll"))
$changed = $false

$awake = $asm.MainModule.GetType("TMPro.TextMeshProUGUI").Methods | Where-Object { $_.Name -eq "Awake" }
$first = $awake.Body.Instructions[0]
if ($first.OpCode.Code -eq "Call" -and $first.Operand.DeclaringType.FullName -eq "OrwellRuFix.Loader") {
    Write-Host "Assembly-CSharp.dll already has the loader call"
} else {
    $init = $pluginAsm.MainModule.GetType("OrwellRuFix.Loader").Methods | Where-Object { $_.Name -eq "Init" }
    $il = $awake.Body.GetILProcessor()
    $il.InsertBefore($first, $il.Create([Mono.Cecil.Cil.OpCodes]::Call, $asm.MainModule.ImportReference($init)))
    $changed = $true
    Write-Host "loader call injected into TMPro.TextMeshProUGUI.Awake"
}

# Russian date and clock: DateTime.ToString(format[, provider]) and DateTime.Parse(string) in the game's
# date/clock code -> OrwellRuFix.RuDate.Format(ref DateTime, format[, provider]) / RuDate.Parse(string).
# The stack layout is the same (the instance calls get the DateTime by address), so only the operand changes.
$ruDate = $pluginAsm.MainModule.GetType("OrwellRuFix.RuDate")
$fmt2 = $asm.MainModule.ImportReference(($ruDate.Methods | Where-Object { $_.Name -eq "Format" -and $_.Parameters.Count -eq 2 }))
$fmt3 = $asm.MainModule.ImportReference(($ruDate.Methods | Where-Object { $_.Name -eq "Format" -and $_.Parameters.Count -eq 3 }))
$parse = $asm.MainModule.ImportReference(($ruDate.Methods | Where-Object { $_.Name -eq "Parse" }))
$dateMethods = @{
    "DateTool"                         = "Start", "IncreaseDayIndex", "GetDate"
    "IngameMenuTool"                   = "SetDate"
    "TimeTool"                         = "UpdateTimeLabel"
    "Orwell.Documents.RelativeTimestamp" = "GetNewTimeStampText"
}
$redirected = 0
foreach ($typeName in $dateMethods.Keys) {
    $type = $asm.MainModule.GetType($typeName)
    foreach ($m in ($type.Methods | Where-Object { $dateMethods[$typeName] -contains $_.Name })) {
        foreach ($ins in $m.Body.Instructions) {
            if ($ins.OpCode.Code -ne "Call" -or $ins.Operand.DeclaringType.FullName -ne "System.DateTime") { continue }
            $target = $null
            if ($ins.Operand.Name -eq "ToString" -and $ins.Operand.Parameters.Count -eq 1) { $target = $fmt2 }
            elseif ($ins.Operand.Name -eq "ToString" -and $ins.Operand.Parameters.Count -eq 2) { $target = $fmt3 }
            elseif ($ins.Operand.Name -eq "Parse" -and $ins.Operand.Parameters.Count -eq 1) { $target = $parse }
            if ($target) { $ins.Operand = $target; $redirected++ }
        }
    }
}
if ($redirected) {
    $changed = $true
    Write-Host "$redirected DateTime calls redirected to OrwellRuFix.RuDate"
} else {
    Write-Host "Assembly-CSharp.dll already uses OrwellRuFix.RuDate"
}

if ($changed) { $asm.Write((Join-Path $Out "Assembly-CSharp.dll")) }
