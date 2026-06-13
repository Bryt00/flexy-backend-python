import smtplib
from email.mime.text import MIMEText

host = "mail.flexyridegh.com"
port = 465
user = "noreply@flexyridegh.com"
password = "McgogomeMyBrother@123##"
from_addr = "noreply@flexyridegh.com"
to_addr = "kabrytlex2468@gmail.com"

msg = MIMEText("This is a test email from FlexyRide")
msg['Subject'] = "FlexyRide Test"
msg['From'] = "FlexyRide <noreply@flexyridegh.com>"
msg['To'] = to_addr

try:
    server = smtplib.SMTP_SSL(host, port)
    server.login(user, password)
    server.sendmail(from_addr, [to_addr], msg.as_string())
    server.quit()
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
