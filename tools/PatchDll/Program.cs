using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using Mono.Cecil;
using Mono.Cecil.Cil;

namespace PatchDll;

class Program
{
    static int Main(string[] args)
    {
        // Paths
        string projectRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
        string backupDll = Path.Combine(projectRoot, "backup", "Assembly-CSharp.dll");
        string translationsJson = Path.Combine(projectRoot, "translated", "dll_strings.json");
        string outputDir = Path.Combine(projectRoot, "patches");
        string outputDll = Path.Combine(outputDir, "Assembly-CSharp.dll");

        // Allow override via args
        if (args.Length >= 1) backupDll = args[0];
        if (args.Length >= 2) translationsJson = args[1];
        if (args.Length >= 3) outputDll = args[2];

        Console.WriteLine($"=== Orwell RU — DLL Patcher (Mono.Cecil) ===");
        Console.WriteLine($"Input DLL:    {backupDll}");
        Console.WriteLine($"Translations: {translationsJson}");
        Console.WriteLine($"Output DLL:   {outputDll}");
        Console.WriteLine();

        // Validate files exist
        if (!File.Exists(backupDll))
        {
            Console.Error.WriteLine($"ERROR: Input DLL not found: {backupDll}");
            return 1;
        }
        if (!File.Exists(translationsJson))
        {
            Console.Error.WriteLine($"ERROR: Translations file not found: {translationsJson}");
            return 1;
        }

        // Load translations from JSON
        var translations = LoadTranslations(translationsJson);
        Console.WriteLine($"Loaded {translations.Count} translations");

        // Track what was replaced
        var replaced = new Dictionary<string, int>();
        int totalReplacements = 0;

        // Load assembly with Mono.Cecil, with resolver pointing to Managed folder
        var resolver = new DefaultAssemblyResolver();
        string managedDir = @"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data\Managed";
        string backupDir = Path.GetDirectoryName(backupDll)!;
        resolver.AddSearchDirectory(managedDir);
        resolver.AddSearchDirectory(backupDir);

        var readerParams = new ReaderParameters
        {
            ReadWrite = false,
            AssemblyResolver = resolver
        };
        using var assembly = AssemblyDefinition.ReadAssembly(backupDll, readerParams);

        Console.WriteLine($"Assembly: {assembly.FullName}");
        Console.WriteLine($"Module: {assembly.MainModule.Name}");
        Console.WriteLine();

        // Iterate all types (including nested)
        foreach (var type in GetAllTypes(assembly.MainModule))
        {
            foreach (var method in type.Methods)
            {
                if (!method.HasBody) continue;

                foreach (var instruction in method.Body.Instructions)
                {
                    if (instruction.OpCode != OpCodes.Ldstr) continue;

                    string original = (string)instruction.Operand;
                    if (translations.TryGetValue(original, out string? translation))
                    {
                        instruction.Operand = translation;
                        totalReplacements++;

                        if (replaced.ContainsKey(original))
                            replaced[original]++;
                        else
                            replaced[original] = 1;
                    }
                }
            }
        }

        // Ensure output directory exists
        Directory.CreateDirectory(Path.GetDirectoryName(outputDll)!);

        // Save patched assembly
        assembly.Write(outputDll);

        Console.WriteLine($"=== Results ===");
        Console.WriteLine($"Total ldstr replacements: {totalReplacements}");
        Console.WriteLine($"Unique strings replaced:  {replaced.Count} / {translations.Count}");
        Console.WriteLine();

        // Report what was replaced
        if (replaced.Count > 0)
        {
            Console.WriteLine("Replaced strings:");
            foreach (var kvp in replaced)
            {
                string ru = translations[kvp.Key];
                string truncEn = kvp.Key.Length > 40 ? kvp.Key[..40] + "..." : kvp.Key;
                string truncRu = ru.Length > 40 ? ru[..40] + "..." : ru;
                Console.WriteLine($"  [{kvp.Value}x] \"{truncEn}\" -> \"{truncRu}\"");
            }
        }

        // Report NOT replaced
        var notReplaced = new List<string>();
        foreach (var key in translations.Keys)
        {
            if (!replaced.ContainsKey(key))
                notReplaced.Add(key);
        }

        if (notReplaced.Count > 0)
        {
            Console.WriteLine();
            Console.WriteLine($"WARNING: {notReplaced.Count} translations NOT found in IL:");
            foreach (var s in notReplaced)
            {
                string trunc = s.Length > 60 ? s[..60] + "..." : s;
                Console.WriteLine($"  \"{trunc}\"");
            }
        }

        Console.WriteLine();
        Console.WriteLine($"Output: {outputDll}");
        Console.WriteLine($"Size: {new FileInfo(outputDll).Length:N0} bytes");

        return 0;
    }

    static Dictionary<string, string> LoadTranslations(string jsonPath)
    {
        var result = new Dictionary<string, string>();
        var jsonText = File.ReadAllText(jsonPath);
        using var doc = JsonDocument.Parse(jsonText);

        var root = doc.RootElement;
        if (!root.TryGetProperty("translations", out var translationsObj))
        {
            throw new Exception("JSON must have a 'translations' object");
        }

        foreach (var prop in translationsObj.EnumerateObject())
        {
            var entry = prop.Value;
            string original = entry.GetProperty("original").GetString()!;
            string translation = entry.GetProperty("translation").GetString()!;

            // Skip entries where translation == original (no change needed)
            if (original == translation) continue;

            result[original] = translation;
        }

        return result;
    }

    static IEnumerable<TypeDefinition> GetAllTypes(ModuleDefinition module)
    {
        foreach (var type in module.Types)
        {
            yield return type;
            foreach (var nested in GetNestedTypes(type))
                yield return nested;
        }
    }

    static IEnumerable<TypeDefinition> GetNestedTypes(TypeDefinition type)
    {
        foreach (var nested in type.NestedTypes)
        {
            yield return nested;
            foreach (var deeper in GetNestedTypes(nested))
                yield return deeper;
        }
    }
}
