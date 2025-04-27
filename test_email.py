import smtplib
from email.mime.text import MIMEText

def send_test_email():
    # Email configuration
    sender_email = "your-email@gmail.com"  # Replace with your Gmail
    sender_password = "your-password"  # Replace with your Gmail password
    recipient_email = "recipient@example.com"  # Replace with recipient email
    
    # Create message
    message = MIMEText("This is a test email from OverseenBudget")
    message['Subject'] = "Test Email"
    message['From'] = sender_email
    message['To'] = recipient_email
    
    try:
        # Connect to Gmail's SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        
        # Login
        server.login(sender_email, sender_password)
        
        # Send email
        server.send_message(message)
        print("Email sent successfully!")
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
    finally:
        server.quit()

if __name__ == "__main__":
    send_test_email() 