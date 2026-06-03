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
from teams_reporter import send_teams_report


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

    print("Mail sender:", EMAIL_REPORT["sender"])
    print("Mail receiver:", ", ".join(receivers))

    now = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")

    step_rows = ""
    for step in step_results:
        step_status = str(step.get("status", ""))
        icon = "&#9989;" if step_status == "PASS" else "&#10060;"
        color = "#d1fae5" if step_status == "PASS" else "#fee2e2"

        step_rows += f"""
        <tr style="background:{color}">
            <td style="padding:10px;border:1px solid #d1d5db">{html.escape(str(step.get('step', '')))}</td>
            <td style="padding:10px;border:1px solid #d1d5db;font-weight:700">{icon} {html.escape(step_status)}</td>
            <td style="padding:10px;border:1px solid #d1d5db">{html.escape(str(step.get('name', '')))}</td>
            <td style="padding:10px;border:1px solid #d1d5db">{html.escape(str(step.get('reason', '')))}</td>
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
    <body style="margin:0;background:#f4f6f8;font-family:Arial,sans-serif;color:#111827">
        <div style="max-width:1080px;margin:0 auto;padding:20px">
            <div style="background:#ffffff;border:1px solid #e5e7eb">
                <div style="background:#1f3f68;color:#ffffff;padding:22px 24px">
                    <div style="font-size:22px;font-weight:700">Support Portal Automation Report</div>
                    <div style="font-size:13px;margin-top:6px">Generated: {html.escape(now)} | Duration: {html.escape(duration)}</div>
                </div>
                <div style="padding:18px 24px 24px">
                    <div style="font-size:14px;font-weight:700;margin-bottom:14px">
                        Code Review: PASS &nbsp;|&nbsp; Test Execution:
                        <span style="background:{'#dcfce7' if status == 'PASS' else '#fee2e2'};color:{'#047857' if status == 'PASS' else '#b91c1c'};padding:7px 18px;border-radius:5px">{html.escape(status)}</span>
                    </div>
                    <table style="border-collapse:collapse;width:100%;font-size:13px">
                        <thead>
                            <tr style="background:#344153;color:#ffffff;text-align:left">
                                <th style="padding:10px;border:1px solid #4b5563">Step</th>
                                <th style="padding:10px;border:1px solid #4b5563">Status</th>
                                <th style="padding:10px;border:1px solid #4b5563">Name</th>
                                <th style="padding:10px;border:1px solid #4b5563">Reason</th>
                            </tr>
                        </thead>
                        <tbody>{step_rows}</tbody>
                    </table>
                    <div style="font-size:12px;color:#4b5563;margin-top:14px"><b>Video Recording:</b> {video_line}</div>
                </div>
            </div>
        </div>
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
        smtp_username = EMAIL_REPORT.get("username", EMAIL_REPORT["sender"])
        server.login(smtp_username, EMAIL_REPORT["password"])
        server.sendmail(EMAIL_REPORT["sender"], receivers, msg.as_string())
        server.quit()
        print("Mail sent successfully")
        if attached:
            print("Video attached:", video_path)
        else:
            print("Video not found - email sent without video")
        send_teams_report(
            title=f"Support Portal Automation Report - {status}",
            status=status,
            html_body=html_body,
            video_path=video_path,
            step_results=step_results,
            duration=duration,
            flow_details={"report_name": "Support Portal Automation Report"},
        )
    except Exception as e:
        print("Mail failed:", e)
        raise


if __name__ == "__main__":
    print("Starting Support Portal Test...")
    start_time = time.time()

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/Support_Page_Test.py", "-v", "-s", "--tb=short", "--headed"],
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
