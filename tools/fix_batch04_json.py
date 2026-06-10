#!/usr/bin/env python3
"""Fix unescaped quotes in batch_level3_04.json"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

with open('C:/Projects/OrwellRU/translated/batch_level3_04.json', 'r', encoding='utf-8') as f:
    content = f.read()

# The problem: line 102 has "Treat your brother like that" with unescaped quotes
# In the JSON file, this looks like:  ...like that?\r\n "Treat your brother like that", those...
# The " chars around "Treat your brother like that" are not escaped

# Find the pattern and escape the quotes
# Pattern in the file: ...like that?\r\n "Treat...that", those...
target = 'like that?\\r\\n "Treat your brother like that", those'
replacement = 'like that?\\r\\n \\"Treat your brother like that\\", those'
content = content.replace(target, replacement)

try:
    data = json.loads(content)
    print(f'Fixed! {len(data)} entries')
    with open('C:/Projects/OrwellRU/translated/batch_level3_04.json', 'w', encoding='utf-8') as f:
        f.write(content)
except json.JSONDecodeError as e:
    print(f'Still broken: {e}')
    print(repr(content[e.pos-30:e.pos+30]))
