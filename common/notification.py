import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate

def send_gmail(subject, body):
    """
    Gmailを使ってメールを送信する共通関数
    """
    from_email = os.environ.get("GMAIL_USER")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    to_email = os.environ.get("MAIL_TO")

    if not all([from_email, app_password, to_email]):
        print("Mail settings are not configured properly.")
        return

    # メールの作成
    msg = MIMEText(body)
    msg['Subject'] = f"[MyStockApp] {subject}" # タイトルにアプリ名を付与
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Date'] = formatdate()

    # 送信処理
    try:
        # GmailのSMTPサーバー設定
        smtpobj = smtplib.SMTP('smtp.gmail.com', 587)
        smtpobj.starttls()
        smtpobj.login(from_email, app_password)
        smtpobj.sendmail(from_email, to_email, msg.as_string())
        smtpobj.close()
        print(f"Email sent: {subject}")
    except Exception as e:
        print(f"Error sending email: {e}")