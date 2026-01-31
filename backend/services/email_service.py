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
FROM_NAME = os.getenv("FROM_NAME", "INFINITEST")

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
                body {{ font-family: 'Inter', 'Segoe UI', Arial, sans-serif; background-color: #f3f4f6; color: #374151; padding: 40px 0; margin: 0; }}
                .container {{ max-width: 500px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; padding: 40px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); }}
                .header {{ text-align: center; margin-bottom: 32px; }}
                .logo {{ font-size: 24px; font-weight: 700; color: #111827; letter-spacing: -0.025em; }}
                .logo span {{ color: #4f46e5; }}
                h2 {{ color: #111827; font-size: 20px; font-weight: 600; margin-top: 0; margin-bottom: 16px; }}
                p {{ color: #4b5563; font-size: 16px; line-height: 24px; margin-bottom: 24px; }}
                .btn {{ display: inline-block; background-color: #4f46e5; color: #ffffff; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 500; font-size: 16px; text-align: center; transition: background-color 0.2s; }}
                .btn:hover {{ background-color: #4338ca; }}
                .footer {{ color: #9ca3af; font-size: 14px; text-align: center; margin-top: 32px; border-top: 1px solid #e5e7eb; padding-top: 24px; }}
                .link-text {{ color: #4f46e5; word-break: break-all; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo"><span>🎯</span> INFINITEST</div>
                    <div style="color: #6b7280; font-size: 12px; margin-top: 4px;">A Mentors Mantra Product</div>
                </div>
                <h2>Verify Your Email</h2>
                <p>Hi {name or 'there'},</p>
                <p>Thanks for signing up! Please verify your email address by clicking the button below:</p>
                <p style="text-align: center;">
                    <a href="{verification_url}" class="btn" style="background-color: #4f46e5; color: #ffffff !important; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 500; font-size: 16px; display: inline-block;"><span style="color: #ffffff">Verify Email</span></a>
                </p>
                <p>Or copy this link to your browser:</p>
                <p><a href="{verification_url}" class="link-text">{verification_url}</a></p>
                <p>This link expires in 24 hours.</p>
                <div class="footer">
                    If you didn't create an account, you can safely ignore this email.
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(to_email, "Verify your email - INFINITEST", html_content)
    
    def send_password_reset_email(self, to_email: str, name: Optional[str], token: str) -> bool:
        """Send password reset link."""
        reset_url = f"{self.frontend_url}/reset-password?token={token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', 'Segoe UI', Arial, sans-serif; background-color: #f3f4f6; color: #374151; padding: 40px 0; margin: 0; }}
                .container {{ max-width: 500px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; padding: 40px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); }}
                .header {{ text-align: center; margin-bottom: 32px; }}
                .logo {{ font-size: 24px; font-weight: 700; color: #111827; letter-spacing: -0.025em; }}
                .logo span {{ color: #4f46e5; }}
                h2 {{ color: #111827; font-size: 20px; font-weight: 600; margin-top: 0; margin-bottom: 16px; }}
                p {{ color: #4b5563; font-size: 16px; line-height: 24px; margin-bottom: 24px; }}
                .btn {{ display: inline-block; background-color: #4f46e5; color: #ffffff; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 500; font-size: 16px; text-align: center; transition: background-color 0.2s; }}
                .btn:hover {{ background-color: #4338ca; }}
                .footer {{ color: #9ca3af; font-size: 14px; text-align: center; margin-top: 32px; border-top: 1px solid #e5e7eb; padding-top: 24px; }}
                .link-text {{ color: #4f46e5; word-break: break-all; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo"><span>🎯</span> INFINITEST</div>
                    <div style="color: #6b7280; font-size: 12px; margin-top: 4px;">A Mentors Mantra Product</div>
                </div>
                <h2>Reset Your Password</h2>
                <p>Hi {name or 'there'},</p>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                <p style="text-align: center;">
                    <a href="{reset_url}" class="btn" style="background-color: #4f46e5; color: #ffffff !important; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 500; font-size: 16px; display: inline-block;"><span style="color: #ffffff">Reset Password</span></a>
                </p>
                <p>Or copy this link to your browser:</p>
                <p><a href="{reset_url}" class="link-text">{reset_url}</a></p>
                <p>This link expires in 1 hour.</p>
                <div class="footer">
                    If you didn't request this, you can safely ignore this email.
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(to_email, "Reset your password - INFINITEST", html_content)


# Singleton instance
email_service = EmailService()
