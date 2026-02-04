#!/usr/bin/env python
"""Seed script to create initial admin user from environment variables."""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.database import async_session, init_db
from app.models import User, UserRole, Company
from app.auth import hash_password


async def seed_admin():
    """Create initial admin user if it doesn't exist."""
    # Initialize database (creates tables if they don't exist)
    await init_db()
    
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "changeme-in-production!")
    admin_first_name = os.getenv("ADMIN_FIRST_NAME", "Admin")
    admin_last_name = os.getenv("ADMIN_LAST_NAME", "User")
    company_name = os.getenv("COMPANY_NAME", "Default Company")
    
    async with async_session() as db:
        # Check if admin already exists
        result = await db.execute(select(User).where(User.email == admin_email))
        if result.scalar_one_or_none():
            print(f"Admin user {admin_email} already exists. Skipping.")
            return
        
        # Create default company
        company = Company(name=company_name)
        db.add(company)
        await db.flush()
        
        # Create admin user
        admin = User(
            email=admin_email,
            hashed_password=hash_password(admin_password),
            first_name=admin_first_name,
            last_name=admin_last_name,
            role=UserRole.ADMIN,
            company_id=company.id,
            is_active=True
        )
        db.add(admin)
        await db.commit()
        
        print(f"Admin user {admin_email} created successfully!")
        print(f"Company: {company_name}")
        print(f"Default password: {admin_password}")
        print("IMPORTANT: Change the password after first login!")


if __name__ == "__main__":
    asyncio.run(seed_admin())
