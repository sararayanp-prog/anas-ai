import os, sys, re

print("==================================================")
print("🔧 POSITIONING FLASK APP AT TOP SCOPE")
print("==================================================")

main_file = "main.py"
with open(main_file, "r") as f:
    code = f.read()

# 1. Remove any misplaced app = Flask(...)
code = re.sub(r"app\s*=\s*Flask\([^\)]*\)\n?", "", code)

# 2. Ensure Flask is imported properly
if "from flask import" in code:
    first_part, rest = code.split("from flask import", 1)
    import_line, rest_code = rest.split("\n", 1)
    if "Flask" not in import_line:
        import_line = " Flask, " + import_line.strip()
    code = first_part + "from flask import" + import_line + "\n" + rest_code
else:
    code = "from flask import Flask, request, jsonify, render_template\n" + code

# 3. Insert app = Flask(__name__) right after all top-level imports
lines = code.split("\n")
insert_idx = 0
for idx, l in enumerate(lines):
    stripped = l.strip()
    if stripped.startswith("import ") or stripped.startswith("from ") or stripped.startswith("#") or not stripped:
        continue
    insert_idx = idx
    break

lines.insert(insert_idx, "\napp = Flask(__name__)\n")
final_code = "\n".join(lines)

with open(main_file, "w") as f:
    f.write(final_code)

print("✅ Flask app initialized at top of main.py!")

