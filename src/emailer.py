import os
import smtplib
import html
from email.message import EmailMessage
from typing import List


def _env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v


def send_email(subject: str, body: str, to_emails: List[str]) -> None:
    """
    Sends multipart email (plain text + HTML).
    The HTML part uses <pre> so Gmail won't collapse it behind "Show quoted text".
    """
    host = _env("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = _env("SMTP_USER")
    password = _env("SMTP_PASS")
    email_from = os.getenv("EMAIL_FROM", user)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = ", ".join(to_emails)

    # Plain text fallback
    msg.set_content(body)

    # HTML version (prevents Gmail "Show quoted text" collapsing)
    body_html = f"""\
<html>
  <body>
    <pre style="white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; font-size: 13px; line-height: 1.35;">
{html.escape(body)}
    </pre>
  </body>
</html>
"""
    msg.add_alternative(body_html, subtype="html")

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
