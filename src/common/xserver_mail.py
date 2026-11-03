"""Fetch OTP emails from the shared Xserver mailbox using IMAP SSL.

Configure XSERVER_IMAP_HOST, XSERVER_EMAIL_ADDRESS and
XSERVER_EMAIL_PASSWORD as environment variables. Optional filters:
OTP_SENDER, OTP_SUBJECT, OTP_MAX_AGE_MINUTES (default 10), OTP_PATTERN.
"""
from __future__ import annotations

import email
import imaplib
import os
import re
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.message import Message
from email.utils import parsedate_to_datetime
from typing import Optional

from dotenv import load_dotenv

IMAP_PORT = 993
DEFAULT_OTP_PATTERN = r"(?<!\\d)(\\d{6})(?!\\d)"

load_dotenv()

class OTPNotFoundError(RuntimeError):
    """No recent matching OTP email was found."""


def _decode_header(value: Optional[str]) -> str:
    if not value:
        return ""
    pieces = []
    for part, charset in decode_header(value):
        pieces.append(part.decode(charset or "utf-8", errors="replace")
                      if isinstance(part, bytes) else part)
    return "".join(pieces)


def _body_text(message: Message) -> str:
    plain, html = [], []
    parts = message.walk() if message.is_multipart() else [message]
    for part in parts:
        if part.get_content_disposition() == "attachment":
            continue
        kind = part.get_content_type()
        if kind not in ("text/plain", "text/html"):
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        text = payload.decode(part.get_content_charset() or "utf-8",
                             errors="replace")
        (plain if kind == "text/plain" else html).append(text)
    return "\\n".join(plain or html)


def _date_utc(message: Message) -> Optional[datetime]:
    value = message.get("Date")
    if not value:
        return None
    try:
        result = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def get_latest_otp(
    *,
    sender_contains: Optional[str] = None,
    subject_contains: Optional[str] = None,
    max_age_minutes: Optional[int] = None,
    otp_pattern: Optional[str] = None,
    mailbox: str = "INBOX",
) -> str:
    """Extract the OTP from the newest recent email matching optional filters."""
    host = os.getenv("XSERVER_IMAP_HOST")
    address = os.getenv("XSERVER_EMAIL_ADDRESS")
    password = os.getenv("XSERVER_EMAIL_PASSWORD")
    print('host:', host,'address:', address,'password:', password)
    if not all((host, address, password)):
        raise RuntimeError(
            "Set XSERVER_IMAP_HOST, XSERVER_EMAIL_ADDRESS, "
            "XSERVER_EMAIL_PASSWORD environment variables."
        )

    sender_filter = sender_contains or os.getenv("OTP_SENDER")
    subject_filter = subject_contains or os.getenv("OTP_SUBJECT")
    age = max_age_minutes if max_age_minutes is not None else int(
        os.getenv("OTP_MAX_AGE_MINUTES", "10"))
    if age <= 0:
        raise ValueError("max_age_minutes must be positive")
    regex = re.compile(otp_pattern or os.getenv("OTP_PATTERN",
                                                DEFAULT_OTP_PATTERN))
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=age)
    conn = None

    try:
        conn = imaplib.IMAP4_SSL(host, IMAP_PORT)
        conn.login(address, password)
        status, _ = conn.select(mailbox, readonly=True)
        if status != "OK":
            raise RuntimeError(f"Unable to select mailbox: {mailbox}")

        status, data = conn.search(None, "SINCE", cutoff.strftime("%d-%b-%Y"))
        if status != "OK":
            raise RuntimeError("IMAP search failed")
        ids = data[0].split() if data and data[0] else []

        for msg_id in reversed(ids):
            status, fetched = conn.fetch(msg_id, "(BODY.PEEK[])")
            if status != "OK" or not fetched:
                continue
            raw = next((item[1] for item in fetched
                        if isinstance(item, tuple) and isinstance(item[1], bytes)),
                       None)
            if raw is None:
                continue
            msg = email.message_from_bytes(raw)
            received = _date_utc(msg)
            if received is None or received < cutoff:
                continue
            sender = _decode_header(msg.get("From"))
            subject = _decode_header(msg.get("Subject"))
            if sender_filter and sender_filter.casefold() not in sender.casefold():
                continue
            if subject_filter and subject_filter.casefold() not in subject.casefold():
                continue
            match = regex.search(_body_text(msg))
            if match:
                return match.group(1) if match.lastindex else match.group(0)

        raise OTPNotFoundError(
            "No recent OTP email matched. Check sender/subject/pattern filters."
        )
    finally:
        if conn is not None:
            try:
                conn.logout()
            except (imaplib.IMAP4.error, OSError):
                pass


if __name__ == "__main__":
    try:
        get_latest_otp()
        print("OTP email found (code intentionally not printed).")
    except Exception as exc:
        print(f"OTP retrieval failed: {exc}")
