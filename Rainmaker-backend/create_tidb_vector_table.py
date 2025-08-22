"""
Create TiDB Serverless table with native VECTOR support for semantic search.
Uses TiDB's built-in vector capabilities for the existing prospect_scraped_data table.
This script will work with your sync table and existing models.
"""

import asyncio
from sqlalchemy import text
from app.db.session import SessionLocal
from app.db.models import ProspectScrapedData

async def create_tidb_vector_table():
    """Create the prospect_scraped_data table with TiDB native VECTOR type"""
    
    print("🚀 Creating TiDB Serverless Vector Table")
    print("=" * 50)
    print("Using TiDB's native VECTOR(3072) type for semantic search")
    print()
    
    try:
        with SessionLocal() as db:
            # Check if table exists and has vector column
            print("🔍 Checking existing table structure...")
            result = db.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'prospect_scraped_data'
                AND COLUMN_NAME = 'content_vector'
            """))
            
            vector_column_exists = result.fetchone()
            
            if vector_column_exists:
                print("✅ Vector column already exists, checking if it needs updates...")
                
                # Check if it's the right type and dimension
                col_name, data_type = vector_column_exists
                if 'VECTOR(3072)' in data_type.upper():
                    print("✅ Vector column is already properly configured")
                    
                    # Check if vector index exists
                    index_result = db.execute(text("""
                        SHOW INDEX FROM prospect_scraped_data 
                        WHERE Key_name = 'idx_content_vector'
                    """))
                    
                    if index_result.fetchone():
                        print("✅ Vector index already exists")
                        return
                    else:
                        print("📊 Adding vector index...")
                        db.execute(text("""
                            ALTER TABLE prospect_scraped_data 
                            ADD VECTOR INDEX idx_content_vector (content_vector) 
                            COMMENT 'Vector index for semantic search'
                        """))
                        db.commit()
                        print("✅ Vector index added successfully")
                        return
                else:
                    print("⚠️  Vector column exists but wrong type, updating...")
                    # Drop and recreate with correct type
                    db.execute(text("ALTER TABLE prospect_scraped_data DROP COLUMN content_vector"))
                    db.execute(text("""
                        ALTER TABLE prospect_scraped_data 
                        ADD COLUMN content_vector VECTOR(3072) 
                        COMMENT 'Native TiDB vector for 3072-dimensional embeddings'
                    """))
                    db.execute(text("""
                        ALTER TABLE prospect_scraped_data 
                        ADD VECTOR INDEX idx_content_vector ((VEC_COSINE_DISTANCE(content_vector))) 
                        ADD_COLUMNAR_REPLICA_ON_DEMAND
                    """))
                    db.commit()
                    print("✅ Vector column updated to VECTOR(3072) with index")
                    return
            
            # Check if table exists at all
            table_result = db.execute(text("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'prospect_scraped_data'
            """))
            
            if table_result.fetchone():
                print("📊 Table exists, adding vector column and index...")
                # Add vector column to existing table
                db.execute(text("""
                    ALTER TABLE prospect_scraped_data 
                    ADD COLUMN content_vector VECTOR(3072) 
                    COMMENT 'Native TiDB vector for 3072-dimensional embeddings'
                """))
                
                # Add vector index with proper TiDB syntax
                db.execute(text("""
                    ALTER TABLE prospect_scraped_data 
                    ADD VECTOR INDEX idx_content_vector ((VEC_COSINE_DISTANCE(content_vector))) 
                    ADD_COLUMNAR_REPLICA_ON_DEMAND
                """))
                
                db.commit()
                print("✅ Vector column and index added to existing table")
            else:
                print("📊 Creating new prospect_scraped_data table with vector support...")
                # Create the complete table (matches your SQLAlchemy model)
                db.execute(text("""
                    CREATE TABLE prospect_scraped_data (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        prospect_id INT,
                        workflow_id VARCHAR(255) NOT NULL,
                        
                        -- Source information
                        source_url VARCHAR(1000) NOT NULL,
                        source_title VARCHAR(500),
                        source_type ENUM('person_search', 'company_search', 'event_search') NOT NULL,
                        search_query VARCHAR(1000) NOT NULL,
                        
                        -- Content storage  
                        content LONGTEXT NOT NULL,
                        content_summary TEXT,
                        
                        -- TiDB native vector for semantic search
                        content_vector VECTOR(3072) COMMENT 'Native TiDB vector for 3072-dimensional embeddings',
                        
                        -- Metadata
                        content_length INT DEFAULT 0,
                        chunk_index INT DEFAULT 0,
                        embedding_model VARCHAR(100) DEFAULT 'text-embedding-004',
                        
                        -- Timestamps
                        scraped_at DATETIME NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        
                        -- Foreign key constraint
                        FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE,
                        
                        -- Indexes for performance
                        INDEX idx_workflow_id (workflow_id),
                        INDEX idx_prospect_id (prospect_id),
                        INDEX idx_source_type (source_type),
                        
                        -- Vector index for fast semantic search
                        VECTOR INDEX idx_content_vector ((VEC_COSINE_DISTANCE(content_vector))) ADD_COLUMNAR_REPLICA_ON_DEMAND
                    ) COMMENT 'Prospect research data with TiDB native vector search'
                """))
                
                db.commit()
                print("✅ New table created with VECTOR(3072) support")
            
            db.commit()
            print("✅ Table created successfully with VECTOR(3072) type")
            
            # Verify the table structure
            print("\n📋 Verifying table structure...")
            result = db.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, COLUMN_COMMENT 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'prospect_scraped_data'
                AND COLUMN_NAME = 'content_vector'
            """))
            
            column_info = result.fetchone()
            if column_info:
                col_name, data_type, comment = column_info
                print(f"✅ Vector column: {col_name}")
                print(f"✅ Data type: {data_type}")
                print(f"✅ Comment: {comment}")
            
            # Check indexes
            print("\n📊 Verifying vector index...")
            result = db.execute(text("""
                SHOW INDEX FROM prospect_scraped_data 
                WHERE Key_name = 'idx_content_vector'
            """))
            
            indexes = result.fetchall()
            if indexes:
                print(f"✅ Vector index created: {len(indexes)} index entries")
            else:
                print("⚠️  Vector index not found")
                
    except Exception as e:
        print(f"❌ Error creating TiDB vector table: {str(e)}")
        raise

async def test_vector_operations():
    """Test TiDB vector operations"""
    print("\n🧪 Testing TiDB Vector Operations")
    print("=" * 40)
    
    try:
        with SessionLocal() as db:
            # Test vector insertion
            print("📝 Testing vector insertion...")
            test_vector = "[" + ",".join([str(i * 0.001) for i in range(3072)]) + "]"
            
            db.execute(text("""
                INSERT INTO prospect_scraped_data 
                (prospect_id, workflow_id, source_url, source_title, source_type, 
                 search_query, content, content_vector, content_length, scraped_at)
                VALUES 
                (:prospect_id, :workflow_id, :source_url, :source_title, :source_type,
                 :search_query, :content, :content_vector, :content_length, NOW())
            """), {
                'prospect_id': 999,
                'workflow_id': 'test_vector_workflow',
                'source_url': 'https://test.example.com',
                'source_title': 'Test Vector Document',
                'source_type': 'person_search',
                'search_query': 'test query for vector operations',
                'content': 'This is test content for vector operations in TiDB.',
                'content_vector': test_vector,
                'content_length': 50
            })
            
            db.commit()
            print("✅ Vector insertion successful")
            
            # Test vector search
            print("🔍 Testing vector similarity search...")
            query_vector = "[" + ",".join([str(i * 0.0011) for i in range(3072)]) + "]"
            
            result = db.execute(text("""
                SELECT 
                    id, 
                    source_title,
                    (1 - COSINE_DISTANCE(content_vector, :query_vector)) as similarity
                FROM prospect_scraped_data 
                WHERE prospect_id = 999
                ORDER BY similarity DESC
                LIMIT 1
            """), {'query_vector': query_vector})
            
            search_results = result.fetchall()
            if search_results:
                row = search_results[0]
                print(f"✅ Vector search successful!")
                print(f"   Document: {row.source_title}")
                print(f"   Similarity: {row.similarity:.4f}")
            
            # Clean up test data
            db.execute(text("DELETE FROM prospect_scraped_data WHERE prospect_id = 999"))
            db.commit()
            print("✅ Test cleanup complete")
            
    except Exception as e:
        print(f"❌ Vector operations test failed: {str(e)}")
        raise

if __name__ == "__main__":
    print("🔥 TIDB SERVERLESS VECTOR SETUP")
    print("Using TiDB's native vector search capabilities")
    print("Vector dimensions: 3072 (Gemini embeddings)")
    print()
    
    # Create the table
    asyncio.run(create_tidb_vector_table())
    
    # Test vector operations
    asyncio.run(test_vector_operations())
    
    print("\n🎉 TIDB VECTOR SETUP COMPLETE!")
    print("✅ Native VECTOR(3072) column created")
    print("✅ Vector index for fast semantic search")  
    print("✅ Ready for production vector embeddings")
    print("🚀 Your enrichment agent can now use TiDB's built-in vector search!")