import py_compile
import os

root = r'f:\stocks-project\src'
errors = []
count = 0

for dirpath, dirnames, filenames in os.walk(root):
    for fn in filenames:
        if fn.endswith('.py'):
            fpath = os.path.join(dirpath, fn)
            count += 1
            try:
                py_compile.compile(fpath, doraise=True)
            except py_compile.PyCompileError as e:
                errors.append(str(e))

with open(r'f:\stocks-project\syntax_results.txt', 'w') as out:
    out.write(f'Compiled {count} files, {len(errors)} errors\n')
    for e in errors:
        out.write(str(e) + '\n')
