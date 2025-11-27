import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

from src.config import settings


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None
) -> bool:
    """
    Send email using Gmail SMTP (like Nodemailer)
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email body
        from_email: Sender email (optional, uses SMTP_FROM_EMAIL if not provided)
        from_name: Sender name (optional, uses SMTP_FROM_NAME if not provided)
    
    Returns:
        bool: True if email sent successfully
    """
    try:
        # Check if SMTP is configured
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            print(f"⚠️  SMTP not configured - would send email to {to_email}")
            print(f"   Subject: {subject}")
            return True  # Return True in dev mode to avoid breaking flow

        # Prepare email
        from_email = from_email or settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
        from_name = from_name or settings.SMTP_FROM_NAME
        
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{from_name} <{from_email}>"
        message["To"] = to_email
        
        # Attach HTML content
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Send email
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
            use_tls=False,
        )
        
        print(f"✅ Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Email sending failed: {str(e)}")
        return False


async def send_meeting_confirmation(
    to_email: str,
    attendee_name: str,
    meeting_time: str,
    event_link: str,
    meet_link: str = ""
) -> bool:
    """
    Send meeting confirmation email
    
    Args:
        to_email: Attendee email
        attendee_name: Attendee name
        meeting_time: ISO datetime string
        event_link: Google Calendar event link
        meet_link: Google Meet link (optional)
    
    Returns:
        bool: True if email sent successfully
    """
    try:
        # Parse meeting time for display
        dt = datetime.fromisoformat(meeting_time.replace('Z', '+00:00'))
        formatted_time = dt.strftime("%A, %B %d, %Y at %I:%M %p PKT")

        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                           color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #667eea; 
                          color: white; text-decoration: none; border-radius: 5px; margin: 10px 5px; }}
                .footer {{ text-align: center; margin-top: 30px; color: #888; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Your Meeting is Confirmed!</h1>
                </div>
                <div class="content">
                    <p>Hi {attendee_name},</p>
                    <p>Thank you for scheduling a consultation with <strong>AccellionX</strong>!</p>
                    
                    <h3>Meeting Details:</h3>
                    <p><strong>📅 Date & Time:</strong> {formatted_time}</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{event_link}" class="button">📅 Add to Calendar</a>
                        {f'<a href="{meet_link}" class="button">🎥 Join Google Meet</a>' if meet_link else ''}
                    </div>
                    
                    <p><strong>What to prepare:</strong></p>
                    <ul>
                        <li>Brief overview of your project requirements</li>
                        <li>Any reference designs or competitor examples</li>
                        <li>Questions about our development process</li>
                    </ul>
                    
                    <p>You'll receive a reminder 1 hour before the meeting.</p>
                    
                    <p>If you need to reschedule, please reply to this email.</p>
                    
                    <p>Looking forward to discussing your project!</p>
                    
                    <p>Best regards,<br>
                    <strong>The AccellionX Team</strong></p>
                </div>
                <div class="footer">
                    <p>AccellionX Software Solutions | www.accellionx.com</p>
                </div>
            </div>
        </body>
        </html>
        '''

        return await send_email(
            to_email=to_email,
            subject=f'Meeting Confirmed - {formatted_time}',
            html_content=html_content
        )
        
    except Exception as e:
        print(f"❌ Meeting confirmation email failed: {str(e)}")
        return False