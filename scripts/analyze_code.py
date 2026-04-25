import re
from pathlib import Path
from collections import defaultdict

# Target patterns
TARGETS = {
    'python_api': list(Path('apps/api/src').rglob('*.py')),
    'python_tests': list(Path('apps/api/tests').rglob('*.py')),
    'typescript_web': list(Path('apps/web/src').rglob('*.ts')) + list(Path('apps/web/src').rglob('*.tsx')),
}

results = {
    'files': [],
    'functions': [],
    'classes': [],
    'issues': defaultdict(list),
    'tests': [],
}

# Regex patterns
PY_DEF_RE = re.compile(r'^(\s*)def\s+(\w+)\s*\((.*)\)\s*:')
PY_CLASS_RE = re.compile(r'^(\s*)class\s+(\w+)')
PY_COMMENT_RE = re.compile(r'#.*')
TS_DEF_RE = re.compile(r'^(\s*)(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\((.*)\)\s*[:{]')
TS_ARROW_RE = re.compile(r'^(\s*)(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:\((.*)\)|(.*))\s*=>')
TS_CLASS_RE = re.compile(r'^(\s*)(?:export\s+)?class\s+(\w+)')
TS_METHOD_RE = re.compile(r'^(\s*)(?:async\s+)?(\w+)\s*\((.*)\)\s*[:{]')

TODO_RE = re.compile(r'#?\s*(TODO|FIXME|HACK|XXX|BUG|NOTE):?\s*(.*)', re.I)
MAGIC_NUM_RE = re.compile(r'(?<![\w\'"])\d+\.?\d*(?![\w\'"])')
MAGIC_STR_RE = re.compile(r'["\']([^"\']{5,})["\']')

CONTROL_FLOW = ['if', 'elif', 'for', 'while', 'except', 'with', 'assert', 'and', 'or']

def count_indent(line):
    return len(line) - len(line.lstrip())

def analyze_python_file(path):
    content = path.read_text(encoding='utf-8', errors='ignore')
    lines = content.split('\n')
    file_len = len(lines)

    file_data = {
        'path': str(path),
        'lang': 'python',
        'lines': file_len,
        'functions': 0,
        'classes': 0,
        'complexity_score': 0,
    }

    # Track functions and classes
    stack = []  # (type, name, start_line, indent, params)

    for i, line in enumerate(lines):
        indent = count_indent(line)
        stripped = line.strip()

        # Pop stack if dedented
        while stack and stack[-1][3] >= indent:
            item = stack.pop()
            if item[0] == 'func':
                func_len = i - item[2]
                results['functions'].append({
                    'file': str(path),
                    'name': item[1],
                    'lines': func_len,
                    'params': item[4],
                    'start': item[2],
                })
                file_data['functions'] += 1
            elif item[0] == 'class':
                class_len = i - item[2]
                results['classes'].append({
                    'file': str(path),
                    'name': item[1],
                    'lines': class_len,
                    'start': item[2],
                })
                file_data['classes'] += 1

        # Match def
        m = PY_DEF_RE.match(line)
        if m:
            params = [p.strip() for p in m.group(3).split(',') if p.strip() and p.strip() not in ('self', 'cls', '*', '**')]
            stack.append(('func', m.group(2), i, indent, len(params)))

        # Match class
        m = PY_CLASS_RE.match(line)
        if m:
            stack.append(('class', m.group(2), i, indent, 0))

        # Complexity indicators in function context
        if any(s[0] == 'func' for s in stack):
            for kw in CONTROL_FLOW:
                if re.search(r'\b' + kw + r'\b', stripped):
                    file_data['complexity_score'] += 1

        # Deep nesting
        if indent >= 24 and stripped and not stripped.startswith('#'):
            results['issues']['deep_nesting'].append(f"{path}:{i+1} ({indent//4} levels)")

        # TODO/FIXME/HACK
        m = TODO_RE.search(line)
        if m:
            results['issues']['todos'].append(f"{path}:{i+1} [{m.group(1)}] {m.group(2).strip()}")

        # Magic numbers (simple heuristic)
        if stripped and not stripped.startswith('#'):
            nums = MAGIC_NUM_RE.findall(stripped)
            for n in nums:
                if n not in ('0', '1', '2', '100', '404', '500', '200', '401', '403', '429') and not n.startswith('0.'):
                    results['issues']['magic_numbers'].append(f"{path}:{i+1} = {n}")

    # Close remaining stack
    while stack:
        item = stack.pop()
        if item[0] == 'func':
            results['functions'].append({
                'file': str(path),
                'name': item[1],
                'lines': file_len - item[2],
                'params': item[4],
                'start': item[2],
            })
            file_data['functions'] += 1
        elif item[0] == 'class':
            results['classes'].append({
                'file': str(path),
                'name': item[1],
                'lines': file_len - item[2],
                'start': item[2],
            })
            file_data['classes'] += 1

    results['files'].append(file_data)

def analyze_ts_file(path):
    content = path.read_text(encoding='utf-8', errors='ignore')
    lines = content.split('\n')
    file_len = len(lines)

    file_data = {
        'path': str(path),
        'lang': 'typescript',
        'lines': file_len,
        'functions': 0,
        'classes': 0,
        'complexity_score': 0,
    }

    stack = []
    brace_depth = 0
    in_comment = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        indent = count_indent(line)

        # Handle multiline comments
        if '/*' in stripped:
            in_comment = True
        if '*/' in stripped:
            in_comment = False
            continue
        if in_comment or stripped.startswith('//') or stripped.startswith('*'):
            continue

        # Simple brace tracking
        brace_depth += stripped.count('{') - stripped.count('}')

        # Pop stack based on brace depth
        while stack and stack[-1][3] >= brace_depth:
            item = stack.pop()
            if item[0] == 'func':
                results['functions'].append({
                    'file': str(path),
                    'name': item[1],
                    'lines': i - item[2],
                    'params': item[4],
                    'start': item[2],
                })
                file_data['functions'] += 1
            elif item[0] == 'class':
                results['classes'].append({
                    'file': str(path),
                    'name': item[1],
                    'lines': i - item[2],
                    'params': 0,
                    'start': item[2],
                })
                file_data['classes'] += 1

        # Match function declarations
        m = TS_DEF_RE.match(line)
        if m:
            params = [p.strip() for p in m.group(3).split(',') if p.strip()]
            stack.append(('func', m.group(2), i, brace_depth, len(params)))

        # Match class
        m = TS_CLASS_RE.match(line)
        if m:
            stack.append(('class', m.group(2), i, brace_depth, 0))

        # Match methods (simplified)
        if not m:
            m = TS_METHOD_RE.match(line)
            if m and m.group(2) not in ('if', 'while', 'for', 'switch', 'catch'):
                params = [p.strip() for p in m.group(3).split(',') if p.strip()]
                stack.append(('func', m.group(2), i, brace_depth, len(params)))

        # Complexity
        if any(s[0] == 'func' for s in stack):
            for kw in CONTROL_FLOW:
                if re.search(r'\b' + kw + r'\b', stripped):
                    file_data['complexity_score'] += 1

        # Deep nesting (indent based)
        if indent >= 24 and stripped and not stripped.startswith('//'):
            results['issues']['deep_nesting'].append(f"{path}:{i+1} ({indent//2} levels)")

        # TODO/FIXME/HACK
        m = TODO_RE.search(line)
        if m:
            results['issues']['todos'].append(f"{path}:{i+1} [{m.group(1)}] {m.group(2).strip()}")

    while stack:
        item = stack.pop()
        if item[0] == 'func':
            results['functions'].append({
                'file': str(path),
                'name': item[1],
                'lines': file_len - item[2],
                'params': item[4],
                'start': item[2],
            })
            file_data['functions'] += 1
        elif item[0] == 'class':
            results['classes'].append({
                'file': str(path),
                'name': item[1],
                'lines': file_len - item[2],
                'start': item[2],
            })
            file_data['classes'] += 1

    results['files'].append(file_data)

def analyze_test_file(path):
    content = path.read_text(encoding='utf-8', errors='ignore')
    lines = content.split('\n')

    test_count = 0
    assertion_count = 0

    for line in lines:
        stripped = line.strip()
        if re.search(r'\bdef\s+test_', stripped):
            test_count += 1
        if re.search(r'\bassert\b', stripped) or re.search(r'\.assert\w*\(', stripped) or re.search(r'\.assert_\w+\(', stripped):
            assertion_count += 1

    results['tests'].append({
        'path': str(path),
        'lines': len(lines),
        'test_count': test_count,
        'assertion_count': assertion_count,
    })

# Run analysis
for category, files in TARGETS.items():
    for path in files:
        if '.venv' in str(path):
            continue
        if path.suffix == '.py':
            if 'tests' in str(path):
                analyze_test_file(path)
            else:
                analyze_python_file(path)
        elif path.suffix in ('.ts', '.tsx'):
            analyze_ts_file(path)

# Print summary
print("=" * 80)
print("CODE QUALITY & COMPLEXITY ANALYSIS REPORT")
print("=" * 80)

print("\n## FILE COUNTS")
for cat, files in TARGETS.items():
    count = len([f for f in files if '.venv' not in str(f)])
    print(f"  {cat}: {count} files")

print("\n## TOP 10 MOST COMPLEX FILES (by control flow density)")
file_scores = sorted(results['files'], key=lambda x: x['complexity_score'], reverse=True)[:10]
for i, f in enumerate(file_scores, 1):
    print(f"  {i}. {f['path']} ({f['lines']} lines, complexity: {f['complexity_score']}, funcs: {f['functions']}, classes: {f['classes']})")

print("\n## TOP 10 LONGEST FUNCTIONS")
long_funcs = sorted(results['functions'], key=lambda x: x['lines'], reverse=True)[:10]
for i, f in enumerate(long_funcs, 1):
    print(f"  {i}. {f['file']}::{f['name']} ({f['lines']} lines, {f['params']} params)")

print("\n## TOP 10 LARGEST CLASSES")
large_classes = sorted(results['classes'], key=lambda x: x['lines'], reverse=True)[:10]
for i, c in enumerate(large_classes, 1):
    print(f"  {i}. {c['file']}::{c['name']} ({c['lines']} lines)")

print("\n## HIGH PARAMETER COUNT FUNCTIONS (>= 5 params)")
high_params = [f for f in results['functions'] if f['params'] >= 5]
for f in sorted(high_params, key=lambda x: x['params'], reverse=True):
    print(f"  {f['file']}::{f['name']} ({f['params']} params)")

print("\n## QUALITY ISSUE INVENTORY")
for issue_type, items in results['issues'].items():
    print(f"\n  {issue_type.upper()}: {len(items)} occurrences")
    for item in items[:10]:
        print(f"    - {item}")
    if len(items) > 10:
        print(f"    ... and {len(items) - 10} more")

print("\n## TEST COVERAGE OVERVIEW")
total_test_lines = sum(t['lines'] for t in results['tests'])
total_tests = sum(t['test_count'] for t in results['tests'])
total_assertions = sum(t['assertion_count'] for t in results['tests'])
print(f"  Test files: {len(results['tests'])}")
print(f"  Total test lines: {total_test_lines}")
print(f"  Total test functions: {total_tests}")
print(f"  Total assertions: {total_assertions}")
print(f"  Avg assertions per test: {total_assertions/max(total_tests,1):.1f}")

src_lines = sum(f['lines'] for f in results['files'] if f['lang'] == 'python' and 'tests' not in f['path'])
print(f"  Python source lines: {src_lines}")
print(f"  Test-to-source line ratio: {total_test_lines/max(src_lines,1):.2f}")

print("\n## LARGEST FILES")
large_files = sorted(results['files'], key=lambda x: x['lines'], reverse=True)[:10]
for i, f in enumerate(large_files, 1):
    print(f"  {i}. {f['path']} ({f['lines']} lines)")

print("\n## DONE")
