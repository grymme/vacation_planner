"""Configuration settings for the Vacation Planner application."""
import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql+asyncpg://vacation_user:vacation_password@db:5432/vacation_planner"
    database_echo: bool = False
    
    # JWT Authentication
    jwt_secret: str = "your-super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    # Argon2id Password Hashing (Pi 5 optimized)
    argon2_time_cost: int = 2
    argon2_memory_cost: int = 65536
    argon2_parallelism: int = 4
    
    # Admin User (seed data)
    admin_email: str = "admin@example.com"
    admin_password: str = "changeme-in-production!"
    admin_first_name: str = "Admin"
    admin_last_name: str = "User"
    
    # Caddy / HTTPS
    domain: str = "vacation.local"
    email: str = "admin@example.com"
    https_mode: str = "lan"
    caddy_data_path: str = "./caddy_data"
    
    # Mail Settings
    mail_mode: str = "dev"
    mail_smtp_host: str = ""
    mail_smtp_port: int = 587
    mail_smtp_user: str = ""
    mail_smtp_password: str = ""
    mail_from: str = "noreply@example.com"
    
    # CORS
    cors_origins: List[str] = ["http://vacation.local"]
    
    # Environment
    environment: str = "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
