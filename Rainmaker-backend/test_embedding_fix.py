"""
Test the embedding service fix
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.embedding_service import embedding_service
from app.db.session import SessionLocal
from sqlalchemy import text

async def test_embedding_storage():
    """Test the fixed embedding service storage"""
    print("🧪 Testing Fixed Embedding Service Storage")
    print("=" * 50)
    
    try:
        with SessionLocal() as db:
            # Create test prospect
            db.execute(text("""
                INSERT IGNORE INTO prospects (id, prospect_type, name, email, source, status, created_at)
                VALUES (997, 'individual', 'Test Embedding', 'test@embedding.com', 'test', 'discovered', NOW())
            """))
            db.commit()
            
            # Test storing research with vector embedding
            print("💾 Testing vector storage with embedding service...")
            
            test_content = "Gordon Ramsay is a world-renowned chef and restaurateur who specializes in high-end event planning and culinary experiences for corporate events and private celebrations."
            
            stored_records = await embedding_service.store_prospect_research(
                db=db,
                prospect_id=997,
                workflow_id="test_embedding_fix",
                source_url="https://test.example.com/gordon-ramsay",
                source_title="Gordon Ramsay Event Planning Services",
                source_type="person_search",
                search_query="Gordon Ramsay event planning services",
                content=test_content
            )
            
            print(f"✅ Stored {len(stored_records)} records with vector embeddings")
            
            # Test semantic search
            print("🔍 Testing semantic search...")
            similar_content = await embedding_service.search_similar_content(
                db_session=db,
                query_text="celebrity chef event planning",
                prospect_id=997,
                limit=3
            )
            
            print(f"✅ Found {len(similar_content)} similar content items")
            for i, content in enumerate(similar_content):
                print(f"   {i+1}. {content['source_title']} (similarity: {content['similarity_score']:.3f})")
            
            # Clean up
            db.execute(text("DELETE FROM prospect_scraped_data WHERE prospect_id = 997"))
            db.execute(text("DELETE FROM prospects WHERE id = 997"))
            db.commit()
            print("✅ Test cleanup complete")
            
            return True
            
    except Exception as e:
        print(f"❌ Embedding storage test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 EMBEDDING SERVICE FIX TEST")
    print("Testing the fixed embedding service with TiDB vector storage")
    print()
    
    success = asyncio.run(test_embedding_storage())
    
    if success:
        print("\n🎉 SUCCESS! Embedding service is working with vector storage!")
        print("✅ Vector embeddings generated")
        print("✅ Data stored in TiDB with vectors")
        print("✅ Semantic search working")
        print("🚀 Ready for enrichment agent!")
    else:
        print("\n❌ Embedding service test failed.")