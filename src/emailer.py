import os
import smtplib
import html
from email.message import EmailMessage
from typing import List, Optional, Tuple


def _env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v


def send_email(
    subject: str,
    body: str,
    to_emails: List[str],
    attachments: Optional[List[Tuple[str, bytes, str]]] = None,  # (filename, content, mime)
) -> None:
    """
    Sends multipart email (plain text + HTML) and optional attachments.
    - HTML uses <pre> to reduce Gmail collapsing.
    - Attachments prevent losing content due to Gmail trimming.
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

    # HTML version (helps avoid Gmail "quoted text" collapse)
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

    # Attachments (filename, bytes, mime like "text/plain")
    for att in attachments or []:
        filename, content, mime = att
        maintype, subtype = mime.split("/", 1)
        msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
