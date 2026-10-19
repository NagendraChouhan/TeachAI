import smtplib
from email.message import EmailMessage
from .. import config


def check_recipients(to: list[str]) -> list[str]:
    if not config.EMAIL_WHITELIST:
        return to
    ok = lambda e: e.lower() in config.EMAIL_WHITELIST or e.lower().split("@")[-1] in config.EMAIL_WHITELIST
    bad = [e for e in to if not ok(e)]
    if bad:
        raise ValueError(f"Not in EMAIL_WHITELIST: {', '.join(bad)}")
    return to


def send_email(to: list[str], subject: str, body: str, attachment: str | None) -> None:
    check_recipients(to)
    if not (config.SMTP_USER and config.SMTP_PASSWORD):
        raise RuntimeError("SMTP_USER / SMTP_PASSWORD not set in backend/.env")
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = config.SMTP_USER, ", ".join(to), subject
    msg.set_content(body)
    if attachment:
        path = config.OUTPUTS / attachment
        maintype, subtype = ("application", "pdf") if path.suffix == ".pdf" else (
            "application", "vnd.openxmlformats-officedocument.presentationml.presentation")
        msg.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as s:
        s.starttls()
        s.login(config.SMTP_USER, config.SMTP_PASSWORD)
        s.send_message(msg)
