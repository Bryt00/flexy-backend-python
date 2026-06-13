import smtplib
from email.message import EmailMessage

host = "mail.flexyridegh.com"
port = 465
user = "noreply@flexyridegh.com"
password = "McgogomeMyBrother@123##"
from_addr = "noreply@flexyridegh.com"
to_addr = "kabrytlex2468@gmail.com"

msg = EmailMessage()
msg.set_content("Your SECOND FlexyRide test OTP is: 987654.\n\nThis was sent explicitly using mail.flexyridegh.com.")
msg['Subject'] = 'FlexyRide Second Verification OTP'
msg['From'] = f"FlexyRide <{from_addr}>"
msg['To'] = to_addr

try:
    print(f"Connecting to {host} on port {port}...")
    server = smtplib.SMTP_SSL(host, port, timeout=10)
    server.login(user, password)
    server.send_message(msg)
    server.quit()
    print(f"Second OTP sent successfully to {to_addr}")
except Exception as e:
    print(f"Failed to send OTP: {e}")
