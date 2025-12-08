import os
import smtplib
import html
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
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
    Goal: avoid Gmail collapsing the body as "quoted text".
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

    # Make it look like a "new" message (helps Gmail not treat as reply/quote)
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg["X-Entity-Ref-ID"] = make_msgid()  # harmless, sometimes helps threading heuristics

    # If anything sets these (threading), remove them
    if "In-Reply-To" in msg:
        del msg["In-Reply-To"]
    if "References" in msg:
        del msg["References"]

    # Plain text fallback
    msg.set_content(body)

    # HTML version: use DIV (NOT <pre>) but preserve whitespace
    safe = html.escape(body)
    body_html = f"""\
<html>
  <body>
    <div style="
      white-space: pre-wrap;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
      font-size: 13px;
      line-height: 1.35;
    ">{safe}</div>
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
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(user, password)
        server.send_message(msg)