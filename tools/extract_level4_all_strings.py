#!/usr/bin/env python3
"""
Extract ALL human-readable English strings from level4 backup.
Parses every object, extracts length-prefixed UTF-8 strings,
filters to English text, groups by path_id.
Output: originals/level4_all_strings.json
"""
import os, sys, struct, json, re
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile

PROJECT = Path(r"C:\Projects\OrwellRU")
BACKUP_LEVEL4 = PROJECT / "backup" / "level4"
OUTPUT = PROJECT / "originals" / "level4_all_strings.json"

# ──────────────────────────────────────────────────────────────
# FILTERS
# ──────────────────────────────────────────────────────────────

# Strings we want to FIND even if they look short/simple
ALWAYS_INCLUDE_STRINGS = {
    "TASK", "CANCEL", "NEXT STEP", "APPLICANT", "E-Mail", "E-mail",
    "Paired with", "Occupation", "Operating System", "Drag and drop",
    "Name", "Date of birth", "Address", "Nationality",
    "Files", "Close", "Open", "Back", "Next", "Done", "Submit",
    "Search", "Filter", "Sort", "View", "Edit", "Delete",
    "Password", "Username", "Login", "Logout",
    "Yes", "No", "OK", "Apply", "Reset",
    "Loading", "Error", "Warning",
    "Episode", "Chapter", "Save", "Load",
}

# Regexes — patterns that are DEFINITELY technical (skip)
SKIP_PATTERNS = [
    re.compile(r'^TextMeshPro/'),          # Shader names
    re.compile(r'^Stencil\s'),             # Shader params
    re.compile(r'^_[A-Za-z]+$'),           # _FieldName
    re.compile(r'^m_[A-Za-z]+$'),          # m_FieldName
    re.compile(r'^\w+\.\w+\.\w+$'),        # com.package.name
    re.compile(r'^[\w/]+\.(tna|mp3|wav|png|jpg|mat|prefab|unity|shader)$'),
    re.compile(r'^www\.'),                 # URLs
    re.compile(r'^https?://'),
    re.compile(r'^#[0-9a-fA-F]{6}$'),     # Hex colors
    re.compile(r'^[0-9a-fA-F]{32}$'),     # MD5/GUIDs
    re.compile(r'^[A-Z_]{2,}$'),           # ALL_CAPS_IDENTIFIER (but allow short English words)
    re.compile(r'^[a-z_]+$'),              # all_lowercase_no_spaces identifier
    re.compile(r'^\w+State(\s|$)'),        # FooState class names
    re.compile(r'^\w+Line(\s|$)'),
    re.compile(r'^(New|Update|Use|Stop|Empty|If)[A-Z]\w+(State|Line)\s'),
    re.compile(r'^insider_'),
    re.compile(r'^website_'),
    re.compile(r'^image_'),
    re.compile(r'^call_'),
    re.compile(r'^data_'),
    re.compile(r'^flag_'),
    re.compile(r'^CHAR_'),
    re.compile(r'^browser\.hist'),
    re.compile(r'^UnityEngine\.'),
    re.compile(r'UnityEngine\.UI\.(MaskableGraphic|Scrollbar|Button|Toggle|Slider)'),
    re.compile(r'CullStateChangedEvent'),
    re.compile(r'ScrollEvent,\s+UnityEngine'),
    re.compile(r'^\d+[A-Z]{2}\d+'),       # Booking refs like 12AB3456
]

# What makes a string "English human-readable"
ENGLISH_WORD_RE = re.compile(
    r'\b(the|a|an|is|are|was|were|has|have|had|will|would|could|should|'
    r'can|may|might|shall|do|does|did|be|been|being|'
    r'I|you|he|she|it|we|they|this|that|these|those|'
    r'and|or|but|if|then|when|where|who|what|how|'
    r'not|no|yes|all|any|some|more|most|'
    r'your|our|their|his|her|its|my|'
    r'with|from|into|onto|upon|over|under|about|'
    r'for|of|in|on|at|to|by|up|out|off)\b',
    re.IGNORECASE
)

# Short strings that are clearly English UI labels (2+ words or title-case)
SHORT_ENGLISH_RE = re.compile(r'^[A-Z][a-z]+([ \-][A-Za-z]+)+$')  # "E-Mail", "Next Step"

# Contains letter sequences that look like English words
HAS_LATIN_WORD_RE = re.compile(r'[A-Za-z]{4,}')

# Rich text tags (TextMeshPro markup) — strings with these are usually game content
RICH_TEXT_RE = re.compile(r'<[a-z/]', re.IGNORECASE)

# Target strings for guaranteed inclusion
TARGET_STRINGS_RE = re.compile(
    r'\b(TASK|CANCEL|NEXT\s+STEP|APPLICANT|E-Mail|Paired\s+with|'
    r'Occupation|Operating\s+System|Drag\s+and\s+drop|'
    r'Date\s+of\s+birth|INSUFFICIENT|APTITUDE|PIONEER|ORWELL)\b',
    re.IGNORECASE
)


def is_human_readable_english(text: str) -> bool:
    """
    Returns True if this string is likely human-readable English game content.
    Errs on the side of INCLUSION — we'd rather have too many than miss something.
    """
    # Exact match in always-include set
    stripped = text.strip()
    if stripped in ALWAYS_INCLUDE_STRINGS:
        return True

    # Minimum length
    if len(stripped) < 2:
        return False

    # Skip purely whitespace / line-breaks
    if not stripped.replace('\n', '').replace('\r', '').replace('\t', '').strip():
        return False

    # Skip technical patterns
    for pat in SKIP_PATTERNS:
        if pat.search(stripped):
            return False

    # Pure number / punctuation only
    if re.match(r'^[\d\s\.\,\-\+\(\)\[\]\/\*\:]+$', stripped):
        return False

    # Skip pure CamelCase/PascalCase identifiers (no spaces, mixed case, no punctuation)
    if re.match(r'^[A-Z][a-zA-Z0-9]+$', stripped) and len(stripped) < 30 and ' ' not in stripped:
        # Allow short proper-looking words that could be labels
        if len(stripped) > 12:  # Very long PascalCase → technical
            return False

    # Rich text / HTML markup → almost certainly game content
    if RICH_TEXT_RE.search(text):
        return True

    # Target strings we definitely want
    if TARGET_STRINGS_RE.search(text):
        return True

    # Contains English function words → real content
    if ENGLISH_WORD_RE.search(text):
        return True

    # Multi-word with capitals (title case labels)
    if SHORT_ENGLISH_RE.match(stripped):
        return True

    # Contains sentence-ending punctuation and Latin letters → content
    if re.search(r'[.!?]', text) and HAS_LATIN_WORD_RE.search(text):
        return True

    # Longer strings with any Latin words → include
    if len(text) > 20 and HAS_LATIN_WORD_RE.search(text):
        return True

    # Multi-line with Latin content → dialogue/article
    if '\n' in text and HAS_LATIN_WORD_RE.search(text):
        return True

    return False


def extract_strings_from_raw(raw: bytes, min_len: int = 2):
    """
    Scan raw object data for length-prefixed UTF-8 strings.
    Format: [uint32 LE length][utf8 bytes][0-3 padding bytes]
    Returns list of dicts with offset, text, byte_length, padding.
    """
    results = []
    i = 0
    data_len = len(raw)

    while i <= data_len - 4:
        str_len = struct.unpack_from('<I', raw, i)[0]

        # Sanity: max 100KB string, min_len chars
        if min_len <= str_len <= 100_000 and i + 4 + str_len <= data_len:
            try:
                raw_str = raw[i+4 : i+4+str_len]
                text = raw_str.decode('utf-8')

                # Check printability (allow \r\n\t, reject binary garbage)
                # Also reject strings that START with null bytes (Unity event serialization artifacts)
                if text.startswith('\x00'):
                    i += 1
                    continue

                printable = sum(
                    1 for c in text
                    if c.isprintable() or c in '\r\n\t'
                )
                ratio = printable / len(text)

                if ratio >= 0.85:
                    padding = (4 - (str_len % 4)) % 4
                    results.append({
                        "offset": i,
                        "byte_length": str_len,
                        "padding": padding,
                        "total_slot": 4 + str_len + padding,
                        "text": text,
                    })
                    i += 4 + str_len + padding
                    continue

            except (UnicodeDecodeError, ValueError):
                pass

        i += 1

    return results


def get_class_name(class_id: int) -> str:
    """Map Unity class_id to human-readable name."""
    CLASS_NAMES = {
        1: "GameObject", 4: "Transform", 20: "Camera", 23: "MeshRenderer",
        33: "MeshFilter", 43: "Mesh", 48: "Shader", 49: "TextAsset",
        54: "Rigidbody2D", 61: "BoxCollider2D", 65: "PolygonCollider2D",
        96: "TrailRenderer", 102: "TextMesh",
        114: "MonoBehaviour", 115: "MonoScript",
        128: "Font", 141: "BuildSettings",
        156: "GUITexture", 192: "LayerMask",
        194: "AudioManager", 195: "InputManager",
        196: "Mono Manager", 197: "RenderSettings",
        198: "LightManager", 199: "LightmapSettings",
        205: "AudioListener", 210: "Physics2DSettings",
        213: "Texture2D", 221: "RectTransform",
        224: "RectTransform",  # duplicate alias
        228: "EditorBuildSettings", 237: "NavMeshSettings",
        258: "NavMeshAgent", 280: "TerrainData",
        319: "AvatarMask", 328: "ParticleSystemRenderer",
        329: "ParticleSystem", 330: "ParticleSystemForceField",
        331: "SpeedTreeImporter", 362: "NavMeshObstacle",
    }
    return CLASS_NAMES.get(class_id, f"ClassID_{class_id}")


def main():
    print("=" * 70)
    print("LEVEL4 ALL STRINGS EXTRACTOR")
    print(f"Source: {BACKUP_LEVEL4}")
    print("=" * 70)

    # Parse backup
    print(f"\nParsing backup file...")
    usf = UnitySerializedFile(str(BACKUP_LEVEL4))
    print(f"  Unity version: {usf.unity_version}")
    print(f"  File size:     {usf.file_size:,} bytes")
    print(f"  Objects:       {len(usf.objects)}")
    print(f"  Types:         {len(usf.types)}")
    print(f"  Data offset:   0x{usf.data_offset:X}")

    # Count by class
    class_counts = {}
    for obj in usf.objects:
        cid = usf.types[obj['type_index']]['class_id']
        name = get_class_name(cid)
        class_counts[name] = class_counts.get(name, 0) + 1

    print(f"\nObject types:")
    for name, count in sorted(class_counts.items(), key=lambda x: -x[1]):
        print(f"  {name}: {count}")

    # ── Extract strings from every object ──────────────────────────────────
    print(f"\nExtracting strings from all {len(usf.objects)} objects...")

    # Results: dict keyed by path_id
    by_path_id = {}          # path_id → list of string entries
    total_raw = 0            # all strings before filtering
    total_human = 0          # human-readable strings
    objects_with_text = 0

    for obj in usf.objects:
        pid = obj['path_id']
        class_id = usf.types[obj['type_index']]['class_id']
        class_name = get_class_name(class_id)

        raw = usf.get_object_data(pid)
        if raw is None or len(raw) < 8:
            continue

        all_strings = extract_strings_from_raw(raw, min_len=2)
        total_raw += len(all_strings)

        human_strings = []
        for s in all_strings:
            if is_human_readable_english(s["text"]):
                human_strings.append(s)
                total_human += 1

        if human_strings:
            objects_with_text += 1
            by_path_id[pid] = {
                "path_id": pid,
                "class_id": class_id,
                "class_name": class_name,
                "object_size": obj['size'],
                "offset_in_file": usf.data_offset + obj['offset'],
                "strings": human_strings,
            }

    print(f"\nResults:")
    print(f"  Total strings scanned:    {total_raw:,}")
    print(f"  Human-readable English:   {total_human:,}")
    print(f"  Objects with text:        {objects_with_text}")

    # ── Save JSON ──────────────────────────────────────────────────────────
    # Convert to serializable format
    output_data = {
        "source_file": str(BACKUP_LEVEL4),
        "unity_version": usf.unity_version,
        "file_size": usf.file_size,
        "total_objects": len(usf.objects),
        "objects_with_text": objects_with_text,
        "total_strings": total_human,
        "objects": {}
    }

    for pid, entry in sorted(by_path_id.items()):
        output_data["objects"][str(pid)] = {
            "path_id": pid,
            "class_id": entry["class_id"],
            "class_name": entry["class_name"],
            "object_size": entry["object_size"],
            "offset_in_file": entry["offset_in_file"],
            "strings": [
                {
                    "offset": s["offset"],
                    "byte_length": s["byte_length"],
                    "padding": s["padding"],
                    "total_slot": s["total_slot"],
                    "text": s["text"],
                }
                for s in entry["strings"]
            ]
        }

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved: {OUTPUT}")

    # ── Print summary grouped by path_id ──────────────────────────────────
    print("\n" + "=" * 70)
    print("SUMMARY — Human-readable strings grouped by path_id")
    print("=" * 70)

    # Check for target strings
    target_hits = {
        "TASK": [], "CANCEL": [], "NEXT STEP": [], "APPLICANT": [],
        "E-Mail": [], "Paired with": [], "Occupation": [],
        "Operating System": [], "Drag and drop": [],
    }

    for pid, entry in sorted(by_path_id.items()):
        strs = entry["strings"]
        cname = entry["class_name"]

        # Only print objects with "interesting" content
        has_real_content = any(
            len(s["text"].strip()) > 5 and
            re.search(r'[A-Za-z]{3,}', s["text"])
            for s in strs
        )
        if not has_real_content:
            continue

        print(f"\n  path_id={pid} [{cname}] — {len(strs)} string(s):")
        for s in strs:
            text = s["text"]
            # Check target hits
            for target in target_hits:
                if target.lower() in text.lower():
                    target_hits[target].append(pid)

            # Print preview
            preview = text.replace('\r', '\\r').replace('\n', '\\n')
            if len(preview) > 120:
                preview = preview[:117] + "..."
            print(f"    @{s['offset']:5d} [{s['byte_length']:5d}b]: {preview!r}")

    # ── Target string report ──────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("TARGET STRING SEARCH RESULTS")
    print("=" * 70)
    for target, pids in target_hits.items():
        if pids:
            unique_pids = sorted(set(pids))
            print(f"  '{target}': found in path_ids {unique_pids}")
        else:
            print(f"  '{target}': NOT FOUND")

    # ── Class breakdown ───────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("STRINGS BY CLASS TYPE")
    print("=" * 70)
    class_string_count = {}
    for pid, entry in by_path_id.items():
        cname = entry["class_name"]
        class_string_count[cname] = class_string_count.get(cname, 0) + len(entry["strings"])
    for cname, count in sorted(class_string_count.items(), key=lambda x: -x[1]):
        print(f"  {cname}: {count} string(s)")

    print(f"\nDone. Output: {OUTPUT}")
    print(f"Total: {total_human} human-readable strings in {objects_with_text} objects")


if __name__ == "__main__":
    main()
