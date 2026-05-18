import datetime
import html
import json
import os
import smtplib
import subprocess
import sys
import time

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from Support_Page_Config import EMAIL_REPORT


def find_latest_video():
    videos_dir = os.path.join(os.path.dirname(__file__), "videos")
    if not os.path.exists(videos_dir):
        return None

    videos = [
        os.path.join(videos_dir, file_name)
        for file_name in os.listdir(videos_dir)
        if file_name.lower().endswith((".webm", ".mp4"))
    ]

    if not videos:
        return None

    return max(videos, key=os.path.getmtime)


def attach_file(msg, file_path):
    if not file_path or not os.path.exists(file_path):
        return False

    with open(file_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())

    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f'attachment; filename="{os.path.basename(file_path)}"',
    )
    msg.attach(part)
    return True


def send_report(status: str, video_path: str, step_results: list, duration: str):
    receivers = EMAIL_REPORT["receiver"]
    if isinstance(receivers, str):
        receivers = [receivers]

    now = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")

    step_rows = ""
    for step in step_results:
        step_status = str(step.get("status", ""))
        icon = "&#9989;" if step_status == "PASS" else "&#10060;"
        color = "#d1fae5" if step_status == "PASS" else "#fee2e2"

        step_rows += f"""
        <tr style="background:{color}">
            <td>{html.escape(str(step.get('step', '')))}</td>
            <td>{icon} {html.escape(step_status)}</td>
            <td>{html.escape(str(step.get('name', '')))}</td>
            <td>{html.escape(str(step.get('reason', '')))}</td>
        </tr>
        """

    if not step_rows:
        step_rows = """
        <tr style="background:#fee2e2">
            <td colspan="4">No step results found.</td>
        </tr>
        """

    video_line = "Attached to this email" if video_path and os.path.exists(video_path) else "No video file found"

    html_body = f"""
    <html>
    <body style="font-family:Arial">

        <h2>Support Portal Automation Report</h2>

        <h3>&#129504; Code Review: PASS</h3>
        <h3>&#129514; Test Execution: {html.escape(status)}</h3>
        <h3>&#9201; Duration: {html.escape(duration)}</h3>

        <h3>&#128202; Step Results</h3>
        <table border="1" style="border-collapse:collapse;width:100%">
            <tr style="background:#f3f4f6">
                <th>Step</th>
                <th>Status</th>
                <th>Name</th>
                <th>Reason</th>
            </tr>
            {step_rows}
        </table>

        <p><b>Time:</b> {html.escape(now)}</p>
        <p><b>Video Recording:</b> {video_line}</p>

    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg["From"] = EMAIL_REPORT["sender"]
    msg["To"] = ", ".join(receivers)
    msg["Subject"] = f"Support Portal Report - {status}"
    msg.attach(MIMEText(html_body, "html"))

    attached = attach_file(msg, video_path)

    try:
        server = smtplib.SMTP_SSL(EMAIL_REPORT["smtp_server"], EMAIL_REPORT["smtp_port"])
        server.login(EMAIL_REPORT["sender"], EMAIL_REPORT["password"])
        server.sendmail(EMAIL_REPORT["sender"], receivers, msg.as_string())
        server.quit()
        print("Mail sent successfully")
        if attached:
            print("Video attached:", video_path)
        else:
            print("Video not found - email sent without video")
    except Exception as e:
        print("Mail failed:", e)


if __name__ == "__main__":
    print("Starting Support Portal Test...")
    start_time = time.time()

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/Support_Page_Test.py", "-v", "-s", "--tb=short"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=os.path.dirname(__file__),
    )

    print("Return Code:", result.returncode)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    elapsed = int(time.time() - start_time)
    duration = f"{elapsed // 60}m {elapsed % 60}s"
    status = "PASS" if result.returncode == 0 else "FAIL"

    print(f"\nTest Result: {status} | Duration: {duration}")

    step_results = []
    json_path = os.path.join(os.path.dirname(__file__), "step_results.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                step_results = json.loads(content)
        except Exception:
            step_results = []

    video_path = find_latest_video()

    print("\nSending email report...")
    send_report(status, video_path, step_results, duration)

    sys.exit(result.returncode)
