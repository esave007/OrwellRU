#!/usr/bin/env python3
"""
Custom binary patcher for Unity 5.x serialized files (level0-4, sharedassets).
Unlike UnityPy's save(), this preserves the exact file structure and only
modifies targeted objects, avoiding crashes.

Handles:
- Parsing Unity serialized file header/metadata
- Replacing raw object data with different sizes
- Rebuilding file with correct offsets, alignment, and sizes
"""
import os, sys, struct, json
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path


class UnitySerializedFile:
    """Parser and patcher for Unity 5.x serialized files."""

    def __init__(self, path):
        with open(path, 'rb') as f:
            self.data = bytearray(f.read())
        self.path = path
        self._parse_header()
        self._parse_metadata()

    def _parse_header(self):
        """Parse 20-byte BE header."""
        (self.metadata_size, self.file_size, self.version,
         self.data_offset) = struct.unpack_from('>IIII', self.data, 0)
        self.endianness = self.data[16]  # 0=LE
        assert self.version == 17, f"Expected version 17, got {self.version}"
        assert self.endianness == 0, "Expected little-endian"

    def _parse_metadata(self):
        """Parse metadata section (LE)."""
        pos = 20

        # Unity version string (null-terminated)
        end = self.data.index(0, pos)
        self.unity_version = self.data[pos:end].decode('ascii')
        pos = end + 1

        # Platform, type tree flag
        self.target_platform = struct.unpack_from('<i', self.data, pos)[0]
        pos += 4
        self.enable_type_tree = self.data[pos]
        pos += 1

        # Type table
        type_count = struct.unpack_from('<i', self.data, pos)[0]
        pos += 4
        self.types = []
        for _ in range(type_count):
            class_id = struct.unpack_from('<i', self.data, pos)[0]
            pos += 4
            is_stripped = self.data[pos]
            pos += 1
            script_type_index = struct.unpack_from('<h', self.data, pos)[0]
            pos += 2
            script_hash = None
            if class_id == 114:  # MonoBehaviour
                script_hash = bytes(self.data[pos:pos+16])
                pos += 16
            type_hash = bytes(self.data[pos:pos+16])
            pos += 16
            self.types.append({
                'class_id': class_id,
                'is_stripped': is_stripped,
                'script_type_index': script_type_index,
                'script_hash': script_hash,
                'type_hash': type_hash,
            })

        # Object table
        object_count = struct.unpack_from('<i', self.data, pos)[0]
        pos += 4
        self.objects = []
        self.object_table_offset = pos  # Remember where table starts
        for _ in range(object_count):
            # Align to 4 bytes
            pos = (pos + 3) & ~3
            path_id = struct.unpack_from('<q', self.data, pos)[0]
            offset = struct.unpack_from('<I', self.data, pos + 8)[0]
            size = struct.unpack_from('<I', self.data, pos + 12)[0]
            type_index = struct.unpack_from('<I', self.data, pos + 16)[0]
            self.objects.append({
                'path_id': path_id,
                'offset': offset,  # relative to data_offset
                'size': size,
                'type_index': type_index,
                'table_entry_pos': pos,  # position of this entry in file
            })
            pos += 20

        # Remember end of object table for metadata size tracking
        self.after_objects_pos = pos

        # Script type references
        script_count = struct.unpack_from('<i', self.data, pos)[0]
        pos += 4
        self.script_types = []
        for _ in range(script_count):
            file_index = struct.unpack_from('<i', self.data, pos)[0]
            local_id = struct.unpack_from('<q', self.data, pos + 4)[0]
            self.script_types.append((file_index, local_id))
            pos += 12

        # External references
        ext_count = struct.unpack_from('<i', self.data, pos)[0]
        pos += 4
        self.externals = []
        for _ in range(ext_count):
            # asset_path (null-term)
            end = self.data.index(0, pos)
            asset_path = self.data[pos:end].decode('ascii')
            pos = end + 1
            guid = bytes(self.data[pos:pos+16])
            pos += 16
            ext_type = struct.unpack_from('<i', self.data, pos)[0]
            pos += 4
            end = self.data.index(0, pos)
            file_path = self.data[pos:end].decode('ascii')
            pos = end + 1
            self.externals.append({
                'asset_path': asset_path,
                'guid': guid,
                'type': ext_type,
                'file_path': file_path,
            })

        # User info (null-term)
        end = self.data.index(0, pos)
        self.user_info = self.data[pos:end].decode('ascii')
        pos = end + 1
        self.metadata_end = pos

    def get_object_data(self, path_id):
        """Get raw data for an object by path_id."""
        for obj in self.objects:
            if obj['path_id'] == path_id:
                abs_offset = self.data_offset + obj['offset']
                return bytes(self.data[abs_offset:abs_offset + obj['size']])
        return None

    def get_class_id(self, path_id):
        """Get class_id for an object."""
        for obj in self.objects:
            if obj['path_id'] == path_id:
                return self.types[obj['type_index']]['class_id']
        return None

    def rebuild_with_replacements(self, replacements, output_path):
        """
        Rebuild the file with replaced object data.
        replacements: dict of {path_id: new_raw_bytes}
        """
        # Sort objects by offset (they should already be sorted)
        sorted_objs = sorted(self.objects, key=lambda o: o['offset'])

        # Build new data section
        new_data_parts = []
        new_offsets = {}
        current_offset = 0

        for obj in sorted_objs:
            # 8-byte alignment
            aligned = (current_offset + 7) & ~7
            padding = aligned - current_offset
            if padding > 0:
                new_data_parts.append(b'\x00' * padding)
                current_offset = aligned

            new_offsets[obj['path_id']] = current_offset

            if obj['path_id'] in replacements:
                obj_data = replacements[obj['path_id']]
            else:
                abs_offset = self.data_offset + obj['offset']
                obj_data = bytes(self.data[abs_offset:abs_offset + obj['size']])

            new_data_parts.append(obj_data)
            current_offset += len(obj_data)

        new_data = b''.join(new_data_parts)

        # Build metadata with updated object table
        # We keep everything the same except object offsets and sizes
        metadata = bytearray(self.data[20:20 + self.metadata_size])

        for obj in self.objects:
            entry_pos = obj['table_entry_pos'] - 20  # relative to metadata start
            new_offset = new_offsets[obj['path_id']]
            if obj['path_id'] in replacements:
                new_size = len(replacements[obj['path_id']])
            else:
                new_size = obj['size']

            struct.pack_into('<I', metadata, entry_pos + 8, new_offset)
            struct.pack_into('<I', metadata, entry_pos + 12, new_size)

        # Calculate new data_offset (align to 16 bytes, matching original behavior)
        header_plus_meta = 20 + len(metadata)
        new_data_offset = (header_plus_meta + 15) & ~15

        # Padding between metadata and data
        meta_padding = new_data_offset - header_plus_meta

        # New file size
        new_file_size = new_data_offset + len(new_data)

        # Build header (BE)
        header = struct.pack('>IIII', len(metadata), new_file_size, self.version, new_data_offset)
        header += bytes([self.endianness, 0, 0, 0])

        # Write output
        with open(output_path, 'wb') as f:
            f.write(header)
            f.write(metadata)
            f.write(b'\x00' * meta_padding)
            f.write(new_data)

        actual_size = os.path.getsize(str(output_path))
        print(f"Saved: {output_path}")
        print(f"  Original: {self.file_size} bytes, New: {actual_size} bytes")
        print(f"  Objects modified: {len(replacements)}")
        print(f"  Data offset: {self.data_offset} -> {new_data_offset}")

        return actual_size


def find_and_replace_strings(raw_data, translations):
    """
    Find and replace length-prefixed UTF-8 strings in MonoBehaviour raw data.
    translations: dict of {english: russian}
    Returns: new raw data, count of replacements
    """
    data = bytearray(raw_data)
    count = 0

    # Sort by length descending to avoid partial matches
    sorted_trans = sorted(translations.items(), key=lambda x: len(x[0]), reverse=True)

    for eng, rus in sorted_trans:
        eng_bytes = eng.encode('utf-8')
        rus_bytes = rus.encode('utf-8')
        prefix = struct.pack('<I', len(eng_bytes))
        needle = prefix + eng_bytes

        pos = 0
        while True:
            pos = data.find(needle, pos)
            if pos == -1:
                break

            old_len = len(eng_bytes)
            new_len = len(rus_bytes)
            old_padding = (4 - (old_len % 4)) % 4
            new_padding = (4 - (new_len % 4)) % 4
            old_total = 4 + old_len + old_padding
            new_total = 4 + new_len + new_padding

            # Replace: new length prefix + new text + new padding
            replacement = struct.pack('<I', new_len) + rus_bytes + b'\x00' * new_padding
            data[pos:pos + old_total] = replacement
            count += 1
            pos += new_total

    return bytes(data), count


if __name__ == "__main__":
    # Test: parse level4
    level4 = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data\level4")
    usf = UnitySerializedFile(str(level4))
    print(f"Parsed {usf.path}:")
    print(f"  Unity: {usf.unity_version}, Objects: {len(usf.objects)}")
    print(f"  Types: {len(usf.types)}, Externals: {len(usf.externals)}")

    # Show a sample object
    for pid in [964, 1018]:
        raw = usf.get_object_data(pid)
        print(f"\n  path_id={pid}: {len(raw)} bytes, class={usf.get_class_id(pid)}")
        # Find strings in it
        i = 0
        while i < len(raw) - 4:
            slen = struct.unpack_from('<I', raw, i)[0]
            if 10 <= slen <= 5000 and i + 4 + slen <= len(raw):
                try:
                    s = raw[i+4:i+4+slen].decode('utf-8')
                    if s.isprintable() or '<link' in s:
                        if len(s) > 50:
                            print(f"    @{i}: [{slen}] {s[:80]}...")
                        elif len(s) > 10:
                            print(f"    @{i}: [{slen}] {s}")
                        padding = (4 - (slen % 4)) % 4
                        i += 4 + slen + padding
                        continue
                except:
                    pass
            i += 1
