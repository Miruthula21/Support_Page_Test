# ============================================================
#   SUPPORT PAGE AUTOMATION AGENT
#   >> Double-click this file OR run: python Support_Page_Agent.py
#   >> No CMD path typing | No manual report | Fully Automatic
# ============================================================

import os
import sys
import json
import time
import datetime
import subprocess
import ast

# ─────────────────────────────────────────────────────────────
#  HELPER — Print styled section headers
# ─────────────────────────────────────────────────────────────

def header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def line():
    print("-" * 60)


# ─────────────────────────────────────────────────────────────
#  STEP 1 — AUTO-LOCATE Support_Page_Test folder
# ─────────────────────────────────────────────────────────────

def find_project_folder():
    header("STEP 1 | AUTO-LOCATING PROJECT FOLDER")

    # Check if agent is already placed INSIDE the project folder
    current_dir = os.path.abspath(os.path.dirname(__file__))
    if os.path.exists(os.path.join(current_dir, "Support_Page_Run.py")):
        print(f"  [OK] Project folder found (agent is inside project):")
        print(f"       {current_dir}")
        return current_dir

    # Check Desktop
    desktop = os.path.join(os.path.expanduser("~"), "Desktop", "Support_Page_Test")
    if os.path.exists(desktop):
        print(f"  [OK] Project folder found on Desktop:")
        print(f"       {desktop}")
        return desktop

    # Search entire Desktop for Support_Page_Test
    desktop_root = os.path.join(os.path.expanduser("~"), "Desktop")
    print(f"  [..] Searching Desktop for Support_Page_Test folder...")
    for root, dirs, files in os.walk(desktop_root):
        if "Support_Page_Run.py" in files:
            print(f"  [OK] Found project at: {root}")
            return root

    # Not found anywhere
    print("  [!!] ERROR: Could not find Support_Page_Test folder!")
    print("  [i]  Place Support_Page_Agent.py inside your")
    print("       Support_Page_Test folder and run again.")
    input("\n  Press Enter to exit...")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
#  STEP 2 — REVIEW THE TEST CODE
# ─────────────────────────────────────────────────────────────

def review_test_code(project_path):
    header("STEP 2 | REVIEWING TEST CODE")

    test_file = os.path.join(project_path, "tests", "Support_Page_Test.py")

    if not os.path.exists(test_file):
        print("  [!!] Test file not found:", test_file)
        input("\n  Press Enter to exit...")
        sys.exit(1)

    print(f"  [i]  File     : tests/Support_Page_Test.py")

    # Read the file
    with open(test_file, "r", encoding="utf-8") as f:
        source_code = f.read()

    # Syntax check
    try:
        ast.parse(source_code)
        print("  [OK] Syntax Check       : No errors found")
    except SyntaxError as e:
        print(f"  [!!] Syntax Error       : Line {e.lineno} - {e.msg}")
        input("\n  Fix the error and run again. Press Enter to exit...")
        sys.exit(1)

    # Count test functions
    tree       = ast.parse(source_code)
    test_funcs = [
        n.name for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
    ]
    print(f"  [OK] Test Functions     : {len(test_funcs)} found")
    for fn in test_funcs:
        print(f"         -> {fn}")

    # Line count
    total_lines = len(source_code.splitlines())
    print(f"  [OK] Total Lines        : {total_lines}")

    # Check config
    if os.path.exists(os.path.join(project_path, "Support_Page_Config.py")):
        print("  [OK] Config File        : Support_Page_Config.py found")
    else:
        print("  [!!] Config File        : Support_Page_Config.py NOT found!")

    # Check run file
    if os.path.exists(os.path.join(project_path, "Support_Page_Run.py")):
        print("  [OK] Run File           : Support_Page_Run.py found")
    else:
        print("  [!!] Run File           : Support_Page_Run.py NOT found!")
        input("\n  Press Enter to exit...")
        sys.exit(1)

    # Check step_results.json
    if os.path.exists(os.path.join(project_path, "step_results.json")):
        print("  [OK] Step Results File  : step_results.json found")
    else:
        print("  [i]  Step Results File  : Will be created after test run")

    print("\n  [OK] Code Review Complete - Ready to run!")


# ─────────────────────────────────────────────────────────────
#  STEP 3 — RUN THE TESTS AUTOMATICALLY
# ─────────────────────────────────────────────────────────────

def run_tests(project_path):
    header("STEP 3 | RUNNING PLAYWRIGHT TESTS AUTOMATICALLY")

    run_file   = os.path.join(project_path, "Support_Page_Run.py")
    start_time = time.time()
    now        = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")

    print(f"  [i]  Started  : {now}")
    print(f"  [i]  Running  : Support_Page_Run.py")
    print(f"  [i]  This runs pytest + sends email automatically")
    line()
    print("  LIVE OUTPUT:")
    line()

    # Run Support_Page_Run.py with live streaming output
    process = subprocess.Popen(
        [sys.executable, run_file],
        cwd      = project_path,
        stdout   = subprocess.PIPE,
        stderr   = subprocess.STDOUT,
        text     = True,
        encoding = "utf-8",
        errors   = "replace"
    )

    # Stream output live so you can watch progress
    all_output = []
    for output_line in process.stdout:
        print("  " + output_line, end="")
        all_output.append(output_line.strip())

    process.wait()

    # Calculate duration
    end_time = time.time()
    elapsed  = int(end_time - start_time)
    minutes  = elapsed // 60
    seconds  = elapsed % 60
    duration = f"{minutes}m {seconds}s"

    line()
    print(f"\n  [i]  Duration  : {duration}")
    print(f"  [i]  Exit Code : {process.returncode}")

    if process.returncode == 0:
        print("  [OK] Tests completed successfully!")
    else:
        print("  [!!] Tests completed with failures!")

    return process.returncode, duration, all_output


# ─────────────────────────────────────────────────────────────
#  STEP 4 — READ step_results.json + SHOW FULL REPORT REVIEW
# ─────────────────────────────────────────────────────────────

def read_and_review_report(project_path, exit_code, duration):
    header("STEP 4 | AGENT REPORT REVIEW")

    json_path = os.path.join(project_path, "step_results.json")

    # Wait briefly so JSON file is fully written after test run
    time.sleep(2)

    if not os.path.exists(json_path):
        print("  [!!] step_results.json not found - cannot show step review")
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            print("  [!!] step_results.json is empty")
            return
        steps = json.loads(content)
    except Exception as e:
        print(f"  [!!] Could not read step_results.json: {e}")
        return

    # Categorise steps
    passed  = [s for s in steps if s.get("status") == "PASS"]
    failed  = [s for s in steps if s.get("status") != "PASS"]
    total   = len(steps)
    overall = "PASS" if exit_code == 0 else "FAIL"

    # ── Overall Summary ──────────────────────────────────────
    print(f"\n  OVERALL RESULT  : {overall}")
    print(f"  DURATION        : {duration}")
    print(f"  TOTAL STEPS     : {total}")
    print(f"  PASSED          : {len(passed)}")
    print(f"  FAILED          : {len(failed)}")

    # ── Passed Steps ─────────────────────────────────────────
    line()
    print("\n  PASSED STEPS [OK]:")
    if passed:
        for s in passed:
            print(f"    Step {str(s['step']).zfill(2)}  [PASS]  {s['name']}")
    else:
        print("    None")

    # ── Failed Steps ─────────────────────────────────────────
    line()
    print("\n  FAILED STEPS [!!]:")
    if failed:
        for s in failed:
            reason = s.get("reason") or "No reason provided"
            print(f"    Step {str(s['step']).zfill(2)}  [FAIL]  {s['name']}")
            print(f"             Reason : {reason}")
    else:
        print("    None - All steps passed!")

    # ── Agent Final Verdict ───────────────────────────────────
    line()
    print("\n  AGENT VERDICT:")
    if not failed:
        print("    All test steps passed successfully.")
        print("    The Support Portal automation is working correctly.")
        print("    Email report has been sent to your inbox.")
    else:
        print(f"    {len(failed)} step(s) failed out of {total} total steps.")
        print("    Please review the failed steps listed above.")
        print("    Email report with failure details has been sent.")
        print("\n    Steps needing attention:")
        for s in failed:
            reason = s.get("reason") or "No reason provided"
            print(f"      -> Step {s['step']}: {s['name']}")
            print(f"         Reason: {reason}")


# ─────────────────────────────────────────────────────────────
#  MAIN — Agent Entry Point
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("   SUPPORT PAGE AUTOMATION AGENT")
    print("   Fully Automatic - No manual steps needed")
    print("=" * 60)
    print(f"   Started : {datetime.datetime.now().strftime('%d %b %Y, %I:%M:%S %p')}")

    # STEP 1 - Auto-find project folder (no manual path needed)
    project_path = find_project_folder()

    # STEP 2 - Review test code for errors before running
    review_test_code(project_path)

    # STEP 3 - Run Support_Page_Run.py (runs pytest + sends email)
    exit_code, duration, output = run_tests(project_path)

    # STEP 4 - Read step_results.json and show full pass/fail review
    read_and_review_report(project_path, exit_code, duration)

    # Done
    header("AGENT COMPLETE")
    print(f"  Finished : {datetime.datetime.now().strftime('%d %b %Y, %I:%M:%S %p')}")
    print("  Email report sent to your inbox")
    print("  Full summary shown above")
    print("=" * 60)

    input("\n  Press Enter to close...\n")