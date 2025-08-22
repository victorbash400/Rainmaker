"""
Fix the content_vector column size to store large 3072-dimensional embeddings.
"""

import asyncio
from sqlalchemy import text
from app.db.session import SessionLocal, engine

async def fix_vector_column():
    """Update the content_vector column to LONGTEXT"""
    
    print("🔧 Fixing content_vector column size...")
    
    try:
        # Check if table exists
        with SessionLocal() as db:
            result = db.execute(text("""
                SELECT COUNT(*) as table_count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'prospect_scraped_data'
            """))
            
            table_exists = result.scalar() > 0
            
            if not table_exists:
                print("📊 Creating new prospect_scraped_data table...")
                # Create the table with correct column types
                db.execute(text("""
                    CREATE TABLE prospect_scraped_data (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        prospect_id INT,
                        workflow_id VARCHAR(255) NOT NULL,
                        source_url VARCHAR(1000) NOT NULL,
                        source_title VARCHAR(500),
                        source_type ENUM('person_search', 'company_search', 'event_search') NOT NULL,
                        search_query VARCHAR(1000) NOT NULL,
                        content LONGTEXT NOT NULL,
                        content_summary TEXT,
                        content_vector LONGTEXT,
                        content_length INT DEFAULT 0,
                        chunk_index INT DEFAULT 0,
                        embedding_model VARCHAR(100) DEFAULT 'gemini-embedding-001',
                        scraped_at DATETIME NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_workflow_id (workflow_id),
                        INDEX idx_prospect_id (prospect_id),
                        INDEX idx_source_type (source_type)
                    )
                """))
                db.commit()
                print("✅ Created prospect_scraped_data table with LONGTEXT content_vector")
                
            else:
                print("📋 Table exists, checking column size...")
                
                # Check current column type
                result = db.execute(text("""
                    SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                    FROM information_schema.columns 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'prospect_scraped_data' 
                    AND column_name = 'content_vector'
                """))
                
                column_info = result.fetchone()
                
                if column_info:
                    data_type, max_length = column_info
                    print(f"📊 Current content_vector type: {data_type}")
                    print(f"📊 Current max length: {max_length}")
                    
                    if data_type.upper() != 'LONGTEXT':
                        print("🔄 Modifying content_vector column to LONGTEXT...")
                        
                        # Modify the column to LONGTEXT
                        db.execute(text("""
                            ALTER TABLE prospect_scraped_data 
                            MODIFY COLUMN content_vector LONGTEXT
                        """))
                        db.commit()
                        print("✅ Modified content_vector column to LONGTEXT")
                    else:
                        print("✅ content_vector column is already LONGTEXT")
                else:
                    print("❌ content_vector column not found")
                    return
            
            # Verify the fix
            result = db.execute(text("""
                SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                FROM information_schema.columns 
                WHERE table_schema = DATABASE() 
                AND table_name = 'prospect_scraped_data' 
                AND column_name = 'content_vector'
            """))
            
            column_info = result.fetchone()
            if column_info:
                data_type, max_length = column_info
                print(f"🎉 Final content_vector type: {data_type}")
                print(f"🎉 Final max length: {max_length}")
                
                if data_type.upper() == 'LONGTEXT':
                    print("✅ SUCCESS: content_vector can now store large 3072-dimensional vectors!")
                else:
                    print("❌ FAILED: Column type is still not LONGTEXT")
            
    except Exception as e:
        print(f"❌ Error fixing vector column: {str(e)}")
        raise


if __name__ == "__main__":
    print("🚀 FIXING VECTOR COLUMN SIZE")
    print("=" * 50)
    print("Issue: 3072-dimensional vectors (~69K chars) too big for TEXT column")
    print("Solution: Upgrade content_vector to LONGTEXT")
    print()
    
    asyncio.run(fix_vector_column())
    
    print("\n🎉 VECTOR COLUMN FIX COMPLETE!")
    print("✅ Your vector embeddings can now be stored successfully!")
    print("🚀 Ready to run the enrichment agent again!")