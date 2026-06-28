"""Mailer: build and send formatted HTML email via SMTP."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def build_email(paper: dict) -> str:
    """Build an HTML email body from a paper dict."""
    title = paper.get("title", "Untitled")
    abstract = paper.get("abstract", "")
    year = paper.get("year", "")
    source = paper.get("source", "Unknown")
    url = paper.get("url", "")
    citations = paper.get("citation_count", 0)
    reason = paper.get("reason", "")

    citations_str = f"{citations:,}" if citations else "N/A"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px 0;">
<tr>
<td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">

  <!-- Header -->
  <tr>
    <td style="padding: 32px 40px 0 40px;">
      <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: #888; margin-bottom: 8px;">Daily AI Paper</div>
      <h1 style="margin: 0 0 8px 0; font-size: 22px; line-height: 1.35; color: #1a1a1a;">{title}</h1>
    </td>
  </tr>

  <!-- Meta -->
  <tr>
    <td style="padding: 8px 40px 20px 40px;">
      <span style="display: inline-block; background: #eef2ff; color: #4338ca; padding: 3px 10px; border-radius: 4px; font-size: 12px; margin-right: 6px;">{source}</span>
      <span style="display: inline-block; background: #f0fdf4; color: #166534; padding: 3px 10px; border-radius: 4px; font-size: 12px; margin-right: 6px;">{year}</span>
      <span style="display: inline-block; background: #fffbeb; color: #92400e; padding: 3px 10px; border-radius: 4px; font-size: 12px;">{citations_str} citations</span>
    </td>
  </tr>

  <!-- Abstract -->
  <tr>
    <td style="padding: 0 40px 24px 40px;">
      <div style="border-left: 3px solid #6366f1; padding-left: 16px;">
        <p style="margin: 0; font-size: 15px; line-height: 1.7; color: #374151;">{abstract}</p>
      </div>
    </td>
  </tr>

  <!-- Link -->
  <tr>
    <td style="padding: 0 40px 24px 40px;">
      <a href="{url}" style="display: inline-block; background: #6366f1; color: #fff; text-decoration: none; padding: 10px 24px; border-radius: 6px; font-size: 14px; font-weight: 500;">Read Full Paper →</a>
    </td>
  </tr>

  <!-- Why -->
  <tr>
    <td style="padding: 0 40px 24px 40px;">
      <div style="background: #f9fafb; border-radius: 6px; padding: 16px;">
        <p style="margin: 0; font-size: 13px; color: #6b7280;">
          <strong>💡 Why this paper?</strong><br>
          {reason}
        </p>
      </div>
    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="padding: 20px 40px; border-top: 1px solid #e5e7eb;">
      <p style="margin: 0; font-size: 11px; color: #9ca3af;">📬 Delivered by PaperBot · Daily AI paper for students</p>
    </td>
  </tr>

</table>
</td>
</tr>
</table>
</body>
</html>"""
    return html


def send_email(html_body: str, subject: str) -> None:
    """Send an HTML email via SMTP. Config from environment variables."""
    smtp_server = os.environ["SMTP_SERVER"]
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    sender = os.environ["SMTP_EMAIL"]
    password = os.environ["SMTP_PASSWORD"]
    recipient = os.environ["RECIPIENT_EMAIL"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"PaperBot <{sender}>"
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
