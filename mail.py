import os
import email
import imaplib
import smtplib
import hashlib
import datetime

from config import *
from pathlib import Path
from email.message import EmailMessage


# Cache directory
Path("cache").mkdir(exist_ok=True)

# Incoming mail
mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
mail.login(EMAIL_USER, EMAIL_PASSWORD)

# Sending mail
smail = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
smail.login(EMAIL_USER, EMAIL_PASSWORD)

# Retrieve today's messages
mail.select('Inbox')
_, data = mail.search('UTF-8', f'(SINCE {datetime.date.today().strftime("%d-%b-%Y")})')

for num in data[0].split():
    # Retrieve email by number.
    typ, data = mail.fetch(num, '(RFC822)')
    email_bytes = data[0][1]
    email_message = email.message_from_bytes(email_bytes)

    # Checking if already sent this email.
    code = hashlib.sha224(email_bytes).hexdigest()
    filepath = f"cache/{code}"
    if Path(filepath).exists():
        continue

    # Empty file to store sent mails.
    open(filepath, "w")

    # Generate outgoing message
    msg = EmailMessage()
    header = email.header.decode_header(email_message['Subject'])[0]
    # If bytes - there will be encoding. If str - None.
    if header[1] is not None:
        header = header[0].decode(header[1])
    else:
        header = header[0]
    msg['Subject'] = header
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO

    # Adding attachments
    is_media = False
    for counter, part in enumerate(email_message.walk()):
        if part.get_content_disposition() != "attachment":
            continue
        print(f"Got: {part.get_content_type()}")
        try:
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            msg.add_attachment(payload,
                               maintype=part.get_content_maintype(),
                               subtype=part.get_content_subtype(),
                               filename=part.get_filename())
            is_media = True
        except Exception as e:
            print("Exception while downloading attachment, ignoring.")
            print(e)

    # If found any media - send
    if is_media:
        try:
            smail.send_message(msg)
        except Exception as e:
            print("Failed to send email.")
            print(e)
            os.remove(filepath)
