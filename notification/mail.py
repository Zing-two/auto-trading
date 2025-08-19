import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

def send_email(subject: str, body: str, to:str):
    sender = os.getenv("GOOGLE_EMAIL_SENDER")
    receiver = to
    password = os.getenv("GOOGLE_EMAIL_PASSWORD")

    message = MIMEMultipart()
    message['From'] = sender
    message['To'] = receiver
    message['Subject'] = subject

    message.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, message.as_string())
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    print("hello")
    subject="test"
    body="hi"
    to="juhyun.kim0204@gmail.com"
    send_email(subject, body, to)