#!/usr/bin/env python3
"""
Binary patcher for Unity assets.
Replaces UTF-8 strings directly in binary files.

Unity string format:
  [4 bytes LE: string length][UTF-8 bytes][padding to 4-byte alignment with zeros]

This approach works when:
- The replacement string has the SAME byte length as the original (after encoding)
- OR when changing size within a TextAsset (which is a byte array, not a string)

For TextAssets (ResX XML): we can pad with XML comments or spaces to match size.
For MonoBehaviour strings: we MUST match the byte length exactly.
"""
import os, sys, struct, shutil, json
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path

GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")
PROJECT = Path(r"C:\Projects\OrwellRU")


def find_unity_string(data, text, start=0):
    """Find a length-prefixed Unity string in binary data.
    Returns list of offsets to the length prefix."""
    encoded = text.encode("utf-8")
    prefix = struct.pack("<I", len(encoded))
    needle = prefix + encoded

    positions = []
    pos = start
    while True:
        pos = data.find(needle, pos)
        if pos == -1:
            break
        positions.append(pos)
        pos += 1
    return positions


def replace_unity_string_same_size(data, offset, old_text, new_text):
    """Replace a Unity string at given offset. New text must encode to same byte length."""
    old_bytes = old_text.encode("utf-8")
    new_bytes = new_text.encode("utf-8")

    if len(new_bytes) != len(old_bytes):
        raise ValueError(
            f"Byte length mismatch: old={len(old_bytes)}, new={len(new_bytes)}. "
            f"Pad or trim the translation."
        )

    # Verify
    stored_len = struct.unpack_from("<I", data, offset)[0]
    assert stored_len == len(old_bytes), f"Length mismatch at offset {offset}"

    result = bytearray(data)
    result[offset+4:offset+4+len(new_bytes)] = new_bytes
    return bytes(result)


def replace_unity_string_any_size(data, offset, old_text, new_text):
    """Replace a Unity string at given offset, handling different sizes.
    WARNING: This changes the file size and breaks object offsets in the header!
    Only use for the last object in a file, or when you'll fix headers manually."""
    old_bytes = old_text.encode("utf-8")
    new_bytes = new_text.encode("utf-8")

    old_len = len(old_bytes)
    new_len = len(new_bytes)
    old_padding = (4 - (old_len % 4)) % 4
    new_padding = (4 - (new_len % 4)) % 4

    old_total = 4 + old_len + old_padding
    new_total = 4 + new_len + new_padding

    before = data[:offset]
    after = data[offset + old_total:]
    new_chunk = struct.pack("<I", new_len) + new_bytes + b'\x00' * new_padding

    return before + new_chunk + after


def replace_in_textasset_xml(data, textasset_start, old_xml_content, replacements):
    """
    Replace text within a TextAsset that contains XML (like SmartLocalization).
    TextAsset binary: [PPtr 12 bytes][m_Name string][m_Script byte_array]
    m_Script is stored as: [4-byte length][raw bytes]

    We replace XML values within m_Script, then adjust the length prefix.
    Since TextAsset is a byte array (not a Unity string), we can change its size
    IF we correctly update the length prefix.

    But safer approach: pad the XML to keep same size.
    """
    # Find the XML content position
    old_xml_bytes = old_xml_content.encode("utf-8")
    xml_pos = data.find(old_xml_bytes)
    if xml_pos == -1:
        return None, "XML content not found"

    # Apply replacements
    new_xml = old_xml_content
    for old, new in replacements.items():
        new_xml = new_xml.replace(old, new)

    new_xml_bytes = new_xml.encode("utf-8")

    # Pad to same size with trailing spaces before closing </root>
    diff = len(old_xml_bytes) - len(new_xml_bytes)
    if diff > 0:
        # Need to add padding
        new_xml = new_xml.rstrip()
        new_xml += " " * diff
        # Recalculate
        new_xml_bytes = new_xml.encode("utf-8")
        if len(new_xml_bytes) < len(old_xml_bytes):
            new_xml_bytes += b' ' * (len(old_xml_bytes) - len(new_xml_bytes))
    elif diff < 0:
        # Russian text is longer - need to trim or compress XML
        # Try removing unnecessary whitespace in XML
        import re
        new_xml = re.sub(r'  +', ' ', new_xml)
        new_xml_bytes = new_xml.encode("utf-8")
        if len(new_xml_bytes) > len(old_xml_bytes):
            return None, f"Russian XML is {len(new_xml_bytes) - len(old_xml_bytes)} bytes longer than original"

    result = bytearray(data)
    result[xml_pos:xml_pos+len(old_xml_bytes)] = new_xml_bytes
    return bytes(result), "OK"


def pad_translation(original, translation, target_byte_len=None):
    """Pad a Russian translation to match the byte length of the original English text.
    Adds trailing spaces if needed."""
    if target_byte_len is None:
        target_byte_len = len(original.encode("utf-8"))

    trans_bytes = translation.encode("utf-8")
    diff = target_byte_len - len(trans_bytes)

    if diff > 0:
        # Pad with spaces
        return translation + " " * diff
    elif diff < 0:
        # Too long - need to trim
        return None  # Can't auto-pad, need manual shortening
    return translation


def scan_and_catalog_strings(filepath, min_length=5):
    """Scan a binary file and catalog all Unity strings with their offsets."""
    with open(filepath, "rb") as f:
        data = f.read()

    results = []
    i = 0
    while i < len(data) - 8:
        str_len = struct.unpack_from("<I", data, i)[0]
        if 4 <= str_len <= 50000 and i + 4 + str_len <= len(data):
            try:
                s = data[i+4:i+4+str_len].decode("utf-8")
                printable = sum(1 for c in s if c.isprintable() or c in '\n\r\t') / max(len(s), 1)
                if printable > 0.9 and len(s.strip()) >= min_length:
                    import re
                    if re.search(r'[a-zA-Z]{3,}', s):
                        results.append({
                            "offset": i,
                            "byte_length": str_len,
                            "text": s
                        })
                        # Skip past this string
                        padding = (4 - (str_len % 4)) % 4
                        i += 4 + str_len + padding
                        continue
            except (UnicodeDecodeError, ValueError):
                pass
        i += 4  # Align to 4-byte boundary for speed

    return results, data


def test_same_size_replacement():
    """Test replacing a string with same-byte-length Russian text."""
    res_path = GAME_DATA / "resources.assets"

    print("--- Scanning resources.assets for replaceable strings ---")

    # Read the file
    with open(res_path, "rb") as f:
        data = f.read()

    # Test: find "End of communication." (20 chars, 20 bytes)
    # Russian: "Связь завершена.    " (pad to 20 bytes)
    test_cases = [
        # (original, russian_translation)
        ("Thursday", "Четверг."),  # 8 bytes each? No: Thursday=8 bytes, Четверг.=15 bytes
        ("April 2017", "Апрель 2017"),  # 10 vs 19 bytes
    ]

    # Let's find what strings exist and their byte lengths
    print("\nSmartLocalization strings in Language.en:")

    # The TextAsset contains XML, so we need to work with the XML content
    # Find the Language.en TextAsset XML
    import UnityPy
    env = UnityPy.load(str(res_path))
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            d = obj.read()
            if d.m_Name == "Language.en":
                raw = d.m_Script
                xml_text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)

                # Parse and show entries with byte lengths
                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml_text)
                for elem in root.findall(".//data"):
                    key = elem.get("name", "")
                    val_elem = elem.find("value")
                    val = val_elem.text if val_elem is not None and val_elem.text else ""
                    if val:
                        print(f"  {key}: '{val}' ({len(val.encode('utf-8'))} bytes)")
                break

    print("\nFor TextAssets (XML), we can change the byte array length directly.")
    print("For MonoBehaviour strings, we must match byte lengths exactly.")

    # Now test: find MonoBehaviour strings and see byte lengths
    print("\nSample MonoBehaviour strings with byte lengths:")
    strings, data = scan_and_catalog_strings(res_path, min_length=10)

    # Show first 20 that look like translatable content
    shown = 0
    for s in strings:
        text = s["text"]
        if any(kw in text for kw in ["Nation", "Orwell", "you", "the", "is", "Are"]):
            if shown < 20 and len(text) < 200:
                print(f"  offset={s['offset']}, bytes={s['byte_length']}: '{text[:100]}'")
                shown += 1


def main():
    print("=" * 60)
    print("BINARY PATCHER - Analysis")
    print("=" * 60)

    test_same_size_replacement()

    print("\n" + "=" * 60)
    print("CONCLUSION")
    print("=" * 60)
    print("""
Two approaches for string replacement:

1. TextAssets (SmartLocalization XML):
   - Can change byte array size freely
   - Replace XML content, update length prefix
   - Use UnityPy to save (or direct binary edit of byte array)

2. MonoBehaviour strings (dialogue, UI, articles):
   - Must match EXACT byte length
   - Russian text is longer -> pad with spaces OR shorten translation
   - Alternative: change file size but must fix Unity header offsets

   Best approach: Use UABEA CLI or AssetsTools.NET for proper serialization
   OR: pad translations to exact byte length
""")


if __name__ == "__main__":
    main()
