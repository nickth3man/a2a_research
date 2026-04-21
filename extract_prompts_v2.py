"""Extract triple-quoted prompt strings to .txt files."""

import ast
from pathlib import Path

def extract_prompts(py_file: Path) -> int:
    """Extract triple-quoted string assignments to .txt files."""
    text = py_file.read_text(encoding="utf-8")
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    
    extractions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(
                node.value, ast.Constant
            ) and isinstance(node.value.value, str):
                s = node.value.value
                if '\n' in s and len(s) > 100:
                    extractions.append((target.id, s, node.lineno))
    
    if not extractions:
        return 0
    
    # Build new content
    new_lines = lines.copy()
    offset = 0
    for var_name, content, lineno in sorted(extractions, key=lambda x: x[2]):
        txt_file = py_file.with_name(f"{py_file.stem}_{var_name}.txt")
        txt_file.write_text(content, encoding="utf-8")
        
        # Find the assignment lines
        start_idx = lineno - 1 + offset
        # Find where the assignment ends
        end_idx = start_idx
        quote_count = 0
        for i in range(start_idx, len(new_lines)):
            if '"""' in new_lines[i]:
                quote_count += new_lines[i].count('"""')
            if quote_count >= 2:
                end_idx = i
                break
        
        indent = len(new_lines[start_idx]) - len(new_lines[start_idx].lstrip())
        indent_str = new_lines[start_idx][:indent]
        replacement = [
            f'{indent_str}{var_name} = (\n',
            f'{indent_str}    Path(__file__).parent / "{txt_file.name}"\n',
            f'{indent_str}).read_text(encoding="utf-8")\n',
        ]
        new_lines[start_idx:end_idx+1] = replacement
        offset += len(replacement) - (end_idx - start_idx + 1)
    
    # Add Path import if needed
    new_text = ''.join(new_lines)
    if 'from pathlib import Path' not in new_text:
        # Insert after any existing imports
        import_idx = 0
        for i, line in enumerate(new_lines):
            if line.strip().startswith(('import ', 'from ')):
                import_idx = i + 1
        new_lines.insert(import_idx, 'from pathlib import Path\n')
    
    py_file.write_text(''.join(new_lines), encoding="utf-8")
    return len(extractions)


def main():
    root = Path(__file__).resolve().parent
    total = 0
    for directory in [root / "src", root / "tests"]:
        if not directory.exists():
            continue
        for py_file in directory.rglob("*.py"):
            total += extract_prompts(py_file)
    print(f"Extracted {total} prompts")


if __name__ == "__main__":
    main()
