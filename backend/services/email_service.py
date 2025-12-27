"""
Email Service using Gmail SMTP.
Sends verification emails and password reset links.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Gmail SMTP Configuration
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_EMAIL", "mentorsmantra@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_NAME = os.getenv("FROM_NAME", "Mentors Mantra")

# Frontend URL for links in emails
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


class EmailService:
    """Service for sending emails via Gmail SMTP."""
    
    def __init__(self):
        self.smtp_host = SMTP_HOST
        self.smtp_port = SMTP_PORT
        self.smtp_user = SMTP_USER
        self.smtp_password = SMTP_PASSWORD.replace(" ", "")  # Remove spaces from app password
        self.from_name = FROM_NAME
        self.frontend_url = FRONTEND_URL
    
    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send an email using Gmail SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.smtp_user}>"
            msg["To"] = to_email
            
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, to_email, msg.as_string())
            
            return True
        except Exception as e:
            print(f"Email send error: {e}")
            return False
    
    def send_verification_email(self, to_email: str, name: Optional[str], token: str) -> bool:
        """Send email verification link."""
        verification_url = f"{self.frontend_url}/verify-email?token={token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f0f23; padding: 40px; margin: 0; }}
                .container {{ max-width: 500px; margin: 0 auto; background: #1a1a2e; border-radius: 16px; padding: 40px; }}
                .header {{ text-align: center; margin-bottom: 30px; background: linear-gradient(135deg, #6366f1, #22d3ee); padding: 20px; border-radius: 12px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: white !important; }}
                h2 {{ color: #ffffff !important; margin-top: 20px; }}
                p {{ color: #e0e0e0 !important; line-height: 1.6; }}
                .btn {{ display: inline-block; background: linear-gradient(135deg, #6366f1, #22d3ee); color: white !important; padding: 14px 32px; border-radius: 12px; text-decoration: none; font-weight: 600; margin: 20px 0; }}
                .footer {{ color: #888888 !important; font-size: 12px; text-align: center; margin-top: 30px; }}
                code {{ color: #22d3ee !important; background: #0f0f23; padding: 4px 8px; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">📚 Mentors Mantra</div>
                </div>
                <h2 style="color: #ffffff;">Verify Your Email</h2>
                <p style="color: #e0e0e0;">Hi {name or 'there'},</p>
                <p style="color: #e0e0e0;">Thanks for signing up! Please verify your email address by clicking the button below:</p>
                <p style="text-align: center;">
                    <a href="{verification_url}" class="btn" style="color: white;">Verify Email</a>
                </p>
                <p style="color: #e0e0e0;">Or copy this link: <br><code style="color: #22d3ee;">{verification_url}</code></p>
                <p style="color: #e0e0e0;">This link expires in 24 hours.</p>
                <div class="footer" style="color: #888888;">
                    If you didn't create an account, you can safely ignore this email.
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(to_email, "Verify your email - Mentors Mantra", html_content)
    
    def send_password_reset_email(self, to_email: str, name: Optional[str], token: str) -> bool:
        """Send password reset link."""
        reset_url = f"{self.frontend_url}/reset-password?token={token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f0f23; color: #e0e0e0; padding: 40px; }}
                .container {{ max-width: 500px; margin: 0 auto; background: #1a1a2e; border-radius: 16px; padding: 40px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 28px; font-weight: bold; background: linear-gradient(135deg, #6366f1, #22d3ee); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
                .btn {{ display: inline-block; background: linear-gradient(135deg, #6366f1, #22d3ee); color: white; padding: 14px 32px; border-radius: 12px; text-decoration: none; font-weight: 600; margin: 20px 0; }}
                .footer {{ color: #888; font-size: 12px; text-align: center; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">📚 Mentors Mantra</div>
                </div>
                <h2>Reset Your Password</h2>
                <p>Hi {name or 'there'},</p>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                <p style="text-align: center;">
                    <a href="{reset_url}" class="btn">Reset Password</a>
                </p>
                <p>Or copy this link: <br><code style="color: #6366f1;">{reset_url}</code></p>
                <p>This link expires in 1 hour.</p>
                <div class="footer">
                    If you didn't request this, you can safely ignore this email.
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(to_email, "Reset your password - Mentors Mantra", html_content)


# Singleton instance
email_service = EmailService()
