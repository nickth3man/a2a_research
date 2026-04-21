"""Extract long prompt strings from Python files to .txt files."""

import re
from pathlib import Path

MAX_LEN = 79

def extract_prompts(py_file: Path) -> int:
    """Extract triple-quoted strings over 79 chars to .txt files.
    Returns number of extractions."""
    text = py_file.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    
    # Find variable assignments with triple-quoted strings
    pattern = re.compile(r'^([ \t]*(\w+)\s*=\s*)("""[\s\S]*?""")\s*$', re.MULTILINE)
    
    changed = 0
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if this line starts a triple-quoted assignment
        m = re.match(r'^([ \t]*(\w+)\s*=\s*)(""")', line)
        if m:
            indent, var_name, quote = m.groups()
            # Find the end of the triple-quoted string
            start = i
            content_lines = [line[len(indent) + len(var_name) + len('= '):]]
            i += 1
            while i < len(lines):
                if '"""' in lines[i] and lines[i].strip().endswith('"""'):
                    content_lines.append(lines[i])
                    i += 1
                    break
                content_lines.append(lines[i])
                i += 1
            
            # Get the full content
            full_content = ''.join(content_lines)
            # Check if it's a single line that's too long
            if len(full_content.strip()) <= 79 + len(indent) + len(var_name):
                new_lines.extend(lines[start:i])
                continue
                
            # Extract to .txt file
            txt_file = py_file.with_name(f"{py_file.stem}_{var_name}.txt")
            # Remove the triple quotes
            content = full_content.strip()
            if content.startswith('"""') and content.endswith('"""'):
                content = content[3:-3]
            
            txt_file.write_text(content, encoding="utf-8")
            
            # Replace with file read
            new_lines.append(f'{indent}{var_name} = (')
            new_lines.append(f'{indent}    Path(__file__).parent / "{txt_file.name}"')
            new_lines.append(f'{indent}).read_text(encoding="utf-8")')
            new_lines.append('\n')
            changed += 1
        else:
            new_lines.append(line)
            i += 1
    
    if changed:
        py_file.write_text(''.join(new_lines), encoding="utf-8")
    
    return changed


def main():
    root = Path(__file__).resolve().parent
    total = 0
    for directory in [root / "src", root / "tests"]:
        if not directory.exists():
            continue
        for py_file in directory.rglob("prompt.py"):
            total += extract_prompts(py_file)
        for py_file in directory.rglob("*_prompt.py"):
            total += extract_prompts(py_file)
    print(f"Extracted {total} prompts")


if __name__ == "__main__":
    main()
