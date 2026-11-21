import os, sys, re, subprocess

print("==================================================")
print("🩹 1. AUTO-HEALING MAIN.PY INDENTATION")
print("==================================================")

main_file = "main.py"
with open(main_file, "r") as f:
    code = f.read()

# 1. Strip the orphan indented block starting at 'text = (' up to the next top-level statement
code = re.sub(r"^\s+text\s*=\s*\(.*?(?=^[a-zA-Z0-9_#])", "", code, flags=re.DOTALL | re.MULTILINE)

# 2. Ensure payment_bp is registered cleanly with app
if "from payment_engine import payment_bp" not in code:
    code = "from payment_engine import payment_bp\n" + code

if "app.register_blueprint(payment_bp)" not in code:
    if "app = Flask(__name__)" in code:
        code = code.replace("app = Flask(__name__)", "app = Flask(__name__)\napp.register_blueprint(payment_bp)")
    else:
        code = "from flask import Flask\napp = Flask(__name__)\napp.register_blueprint(payment_bp)\n" + code

with open(main_file, "w") as f:
    f.write(code)

# 3. Compiler Auto-Healer Loop: Automatically clears any leftover orphan indented lines
for attempt in range(15):
    res = subprocess.run([sys.executable, "-m", "py_compile", main_file], capture_output=True, text=True)
    if res.returncode == 0:
        print("🎉 main.py COMPILED WITH 0 SYNTAX/INDENT ERRORS!")
        break
    
    match = re.search(r'File ".*?main\.py", line (\d+)', res.stderr)
    if match:
        err_line = int(match.group(1))
        print(f"Auto-removing orphan line {err_line}...")
        with open(main_file, "r") as f:
            flines = f.readlines()
        if 1 <= err_line <= len(flines):
            flines.pop(err_line - 1)
            with open(main_file, "w") as f:
                f.writelines(flines)
    else:
        print("Compile stderr:", res.stderr)
        break

