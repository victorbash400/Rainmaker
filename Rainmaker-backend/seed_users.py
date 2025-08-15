#!/usr/bin/env python3
"""
Seed initial users for development
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.models import User
from app.core.security import get_password_hash


async def create_initial_users():
    """Create initial users for development"""
    async with AsyncSessionLocal() as db:
        # Check if admin user exists
        result = await db.execute(select(User).where(User.email == "admin@rainmaker.com"))
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            # Create admin user
            admin_user = User(
                email="admin@rainmaker.com",
                name="Admin User",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            print("✅ Created admin user: admin@rainmaker.com / admin123")
        else:
            print("ℹ️  Admin user already exists")
        
        # Check if test user exists
        result = await db.execute(select(User).where(User.email == "victorbash400@outlook.com"))
        test_user = result.scalar_one_or_none()
        
        if not test_user:
            # Create test user
            test_user = User(
                email="victorbash400@outlook.com",
                name="Victor Test",
                hashed_password=get_password_hash("password123"),
                role="sales_rep",
                is_active=True
            )
            db.add(test_user)
            print("✅ Created test user: victorbash400@outlook.com / password123")
        else:
            print("ℹ️  Test user already exists")
        
        await db.commit()
        print("🎉 User seeding complete!")


if __name__ == "__main__":
    asyncio.run(create_initial_users())