#!/usr/bin/env python3
"""
Fix user role issue
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.db.session import AsyncSessionLocal
from app.db.models import User
from app.core.security import get_password_hash


async def fix_user_roles():
    """Fix user roles"""
    async with AsyncSessionLocal() as db:
        # Delete the user with wrong role
        await db.execute(delete(User).where(User.email == "victorbash400@outlook.com"))
        
        # Create test user with correct role
        test_user = User(
            email="victorbash400@outlook.com",
            name="Victor Test",
            hashed_password=get_password_hash("password123"),
            role="sales_rep",
            is_active=True
        )
        db.add(test_user)
        
        await db.commit()
        print("✅ Fixed user role for victorbash400@outlook.com")
        print("🎉 Users ready!")
        print("\nLogin credentials:")
        print("Admin: admin@rainmaker.com / admin123")
        print("User: victorbash400@outlook.com / password123")


if __name__ == "__main__":
    asyncio.run(fix_user_roles())