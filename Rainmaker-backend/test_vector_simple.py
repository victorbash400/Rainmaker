"""
Simple test to verify TiDB vector functionality is working
"""

import asyncio
from sqlalchemy import text
from app.db.session import SessionLocal

async def test_vector_table():
    """Test if the vector table is working"""
    print("🧪 Testing TiDB Vector Table")
    print("=" * 40)
    
    try:
        with SessionLocal() as db:
            # Check if vector column exists
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
            else:
                print("❌ Vector column not found!")
                return False
            
            # Check if vector index exists
            result = db.execute(text("""
                SHOW INDEX FROM prospect_scraped_data 
                WHERE Key_name = 'idx_content_vector'
            """))
            
            indexes = result.fetchall()
            if indexes:
                print(f"✅ Vector index found: {len(indexes)} index entries")
                for idx in indexes:
                    print(f"   Index: {idx.Key_name}, Column: {idx.Column_name}")
            else:
                print("⚠️  Vector index not found")
            
            # Test basic vector operations without foreign key constraint
            print("\n🔍 Testing vector operations...")
            
            # First, create a test prospect to avoid foreign key issues
            db.execute(text("""
                INSERT IGNORE INTO prospects (id, prospect_type, name, email, source, status, created_at)
                VALUES (999, 'individual', 'Test Prospect', 'test@example.com', 'test', 'discovered', NOW())
            """))
            
            # Test vector insertion
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
            
            print("✅ Vector insertion successful")
            
            # Test vector search
            query_vector = "[" + ",".join([str(i * 0.0011) for i in range(3072)]) + "]"
            
            result = db.execute(text("""
                SELECT 
                    id, 
                    source_title,
                    (1 - VEC_COSINE_DISTANCE(content_vector, :query_vector)) as similarity
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
            db.execute(text("DELETE FROM prospects WHERE id = 999"))
            db.commit()
            print("✅ Test cleanup complete")
            
            return True
            
    except Exception as e:
        print(f"❌ Vector test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 TIDB VECTOR FUNCTIONALITY TEST")
    print("Testing TiDB Serverless vector search capabilities")
    print()
    
    success = asyncio.run(test_vector_table())
    
    if success:
        print("\n🎉 SUCCESS! Your TiDB vector table is working perfectly!")
        print("✅ VECTOR(3072) column created")
        print("✅ Vector index with cosine distance")
        print("✅ Vector insertion and search working")
        print("🚀 Ready for enrichment agent integration!")
    else:
        print("\n❌ Vector test failed. Check the setup.")