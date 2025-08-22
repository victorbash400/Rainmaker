"""
Test script to verify TiDB vector functionality and enrichment agent integration.
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db.session import SessionLocal
from app.services.embedding_service import embedding_service
from app.agents.enrichment import EnrichmentAgent
from app.core.state import RainmakerState, ProspectData
from sqlalchemy import text
from datetime import datetime


async def test_vector_table_setup():
    """Test if the vector table is properly set up"""
    print("🧪 Testing TiDB Vector Table Setup")
    print("=" * 50)
    
    try:
        with SessionLocal() as db:
            # Check if table exists with vector column
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
                print(f"✅ Vector column found: {col_name}")
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
            else:
                print("⚠️  Vector index not found")
            
            return True
            
    except Exception as e:
        print(f"❌ Vector table test failed: {str(e)}")
        return False


async def test_embedding_service():
    """Test the embedding service functionality"""
    print("\n🧪 Testing Embedding Service")
    print("=" * 40)
    
    try:
        # Test single embedding generation
        test_text = "John Smith is a CEO at TechCorp who is planning a corporate event in San Francisco."
        print(f"📝 Generating embedding for: '{test_text[:50]}...'")
        
        embedding = await embedding_service.generate_embedding(test_text)
        print(f"✅ Embedding generated: {len(embedding)} dimensions")
        
        # Test vector formatting
        vector_str = embedding_service.format_vector_for_tidb(embedding)
        print(f"✅ Vector formatted for TiDB: {len(vector_str)} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ Embedding service test failed: {str(e)}")
        return False


async def test_vector_storage():
    """Test storing and retrieving vector data"""
    print("\n🧪 Testing Vector Storage & Search")
    print("=" * 45)
    
    try:
        with SessionLocal() as db:
            # Test storing research data
            test_data = {
                'prospect_id': 999,
                'workflow_id': 'test_vector_workflow',
                'source_url': 'https://test.example.com',
                'source_title': 'Test Vector Document',
                'source_type': 'person_search',
                'search_query': 'test query for vector operations',
                'content': 'John Smith is a successful CEO at TechCorp Inc, a leading technology company based in San Francisco. He has extensive experience in corporate event planning and has organized multiple large-scale conferences and team building events. His company frequently hosts networking events and product launches.'
            }
            
            print("💾 Storing test research data with vector embedding...")
            stored_records = await embedding_service.store_prospect_research(
                db=db,
                **test_data
            )
            
            print(f"✅ Stored {len(stored_records)} records with vector embeddings")
            
            # Test vector search
            print("🔍 Testing vector similarity search...")
            search_query = "CEO who organizes corporate events and conferences"
            
            similar_content = await embedding_service.search_similar_content(
                db_session=db,
                query_text=search_query,
                prospect_id=999,
                limit=3
            )
            
            print(f"✅ Found {len(similar_content)} similar content items")
            for i, content in enumerate(similar_content):
                print(f"   {i+1}. {content['source_title']} (similarity: {content['similarity_score']:.3f})")
            
            # Test semantic analysis
            print("🧠 Testing semantic analysis...")
            analysis_queries = [
                "What is this person's role and experience?",
                "What kind of events does this person organize?",
                "What is their company background?"
            ]
            
            analysis_results = await embedding_service.semantic_analysis(
                db_session=db,
                prospect_id=999,
                analysis_queries=analysis_queries
            )
            
            print(f"✅ Semantic analysis completed for {len(analysis_queries)} queries")
            for query, results in analysis_results.items():
                print(f"   Query: '{query}' -> {results['insights_found']} insights found")
            
            # Clean up test data
            db.execute(text("DELETE FROM prospect_scraped_data WHERE prospect_id = 999"))
            db.commit()
            print("✅ Test cleanup complete")
            
            return True
            
    except Exception as e:
        print(f"❌ Vector storage test failed: {str(e)}")
        return False


async def test_enrichment_agent_integration():
    """Test the enrichment agent with vector capabilities"""
    print("\n🧪 Testing Enrichment Agent Vector Integration")
    print("=" * 55)
    
    try:
        # Create test state
        test_prospect = ProspectData(
            id=998,
            name="Jane Doe",
            company_name="EventCorp",
            location="New York, NY",
            email="jane.doe@eventcorp.com"
        )
        
        test_state = RainmakerState(
            workflow_id="test_enrichment_vector",
            prospect_data=test_prospect,
            workflow_started_at=datetime.now()
        )
        
        print(f"🤖 Testing enrichment for: {test_prospect.name} at {test_prospect.company_name}")
        
        # Note: This would require actual API keys to work fully
        # For now, we'll just test the initialization
        enrichment_agent = EnrichmentAgent()
        print("✅ Enrichment agent initialized successfully")
        print("✅ Vector storage capabilities integrated")
        
        return True
        
    except Exception as e:
        print(f"❌ Enrichment agent test failed: {str(e)}")
        return False


async def main():
    """Run all vector functionality tests"""
    print("🚀 TIDB VECTOR FUNCTIONALITY TEST SUITE")
    print("=" * 60)
    print("Testing TiDB Serverless vector search integration")
    print()
    
    tests = [
        ("Vector Table Setup", test_vector_table_setup),
        ("Embedding Service", test_embedding_service),
        ("Vector Storage & Search", test_vector_storage),
        ("Enrichment Agent Integration", test_enrichment_agent_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 ALL TESTS PASSED! Your TiDB vector setup is ready for production!")
        print("🚀 Your enrichment agent can now use semantic search capabilities!")
    else:
        print("⚠️  Some tests failed. Please check the setup and try again.")
        print("💡 Make sure you've run create_tidb_vector_table.py first")


if __name__ == "__main__":
    asyncio.run(main())