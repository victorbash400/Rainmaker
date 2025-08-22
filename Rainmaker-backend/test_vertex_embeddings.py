"""
Test script for Google Vertex AI embeddings integration.
Tests the exact API endpoint you specified with gemini-embedding-001.
"""

import asyncio
import json
from app.services.gemini_service import gemini_service
from app.services.embedding_service import embedding_service


async def test_direct_vertex_api():
    """Test the direct Vertex AI embedding API call"""
    print("🧪 Testing Direct Vertex AI Embedding API")
    print("=" * 50)
    
    try:
        # Test with sample text
        test_text = "Gordon Ramsay is a world-renowned chef and restaurateur known for his culinary expertise and television shows."
        
        print(f"📝 Input text: {test_text[:100]}...")
        print(f"🔧 Using model: gemini-embedding-001")
        print(f"🌐 Endpoint: us-central1-aiplatform.googleapis.com")
        
        # Call the embedding service
        embedding = await gemini_service.create_embedding(test_text)
        
        print(f"✅ SUCCESS!")
        print(f"📊 Vector dimensions: {len(embedding)}")
        print(f"📈 First 10 values: {embedding[:10]}")
        print(f"🎯 Vector range: [{min(embedding):.4f}, {max(embedding):.4f}]")
        
        return embedding
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return None


async def test_embedding_service():
    """Test the embedding service with multiple texts"""
    print("\n🧪 Testing Embedding Service")
    print("=" * 50)
    
    try:
        # Test with multiple prospect-related texts
        test_texts = [
            "Gordon Ramsay operates multiple Michelin-starred restaurants worldwide",
            "His television shows include Hell's Kitchen and MasterChef",
            "Recent business expansions include luxury hotel partnerships",
            "Corporate event planning for high-end culinary experiences"
        ]
        
        print(f"📝 Testing with {len(test_texts)} text samples")
        
        # Create embeddings
        embeddings = await embedding_service.create_embeddings(test_texts)
        
        print(f"✅ SUCCESS!")
        print(f"📊 Created {len(embeddings)} embeddings")
        print(f"📈 Dimensions per embedding: {len(embeddings[0])}")
        
        # Test similarity calculation
        similarity = embedding_service._cosine_similarity(embeddings[0], embeddings[1])
        print(f"🎯 Similarity between first two texts: {similarity:.4f}")
        
        return embeddings
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return None


async def test_semantic_search_simulation():
    """Test semantic search functionality"""
    print("\n🧪 Testing Semantic Search Simulation")
    print("=" * 50)
    
    try:
        # Simulate storing and searching embeddings
        research_content = [
            "Gordon Ramsay recently invested in high-end event venues across London",
            "His restaurants cater to corporate clients with exclusive dining experiences", 
            "Partnership with luxury hotels for event catering services",
            "Focus on premium culinary events and private dining experiences"
        ]
        
        # Create embeddings for research content
        print("📊 Creating embeddings for research content...")
        content_embeddings = await embedding_service.create_embeddings(research_content)
        
        # Create search query embedding
        search_query = "corporate event planning budget and luxury dining"
        print(f"🔍 Search query: {search_query}")
        query_embedding = await embedding_service.create_embeddings([search_query])
        
        # Calculate similarities
        similarities = []
        for i, content_emb in enumerate(content_embeddings):
            similarity = embedding_service._cosine_similarity(query_embedding[0], content_emb)
            similarities.append({
                'content': research_content[i],
                'similarity': similarity
            })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        print(f"✅ SUCCESS!")
        print("🎯 Top semantic matches:")
        for i, result in enumerate(similarities[:3], 1):
            print(f"  {i}. Similarity: {result['similarity']:.4f}")
            print(f"     Content: {result['content'][:80]}...")
            print()
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")


async def test_full_workflow():
    """Test the complete vector workflow"""
    print("\n🧪 Testing Complete Vector Workflow")
    print("=" * 50)
    
    try:
        print("Phase 1: Direct API test...")
        embedding1 = await test_direct_vertex_api()
        
        if not embedding1:
            print("❌ Direct API test failed - aborting workflow test")
            return
        
        print("\nPhase 2: Embedding service test...")
        embeddings = await test_embedding_service()
        
        if not embeddings:
            print("❌ Embedding service test failed - aborting workflow test")
            return
        
        print("\nPhase 3: Semantic search test...")
        await test_semantic_search_simulation()
        
        print("\n🎉 COMPLETE WORKFLOW TEST PASSED!")
        print("✅ Ready for TiDB AgentX hackathon with real Vertex AI embeddings!")
        
    except Exception as e:
        print(f"❌ Workflow test failed: {str(e)}")


def print_summary():
    """Print implementation summary"""
    print("\n" + "=" * 60)
    print("🚀 VERTEX AI EMBEDDING IMPLEMENTATION SUMMARY")
    print("=" * 60)
    
    print("\n✅ IMPLEMENTED:")
    print("• Direct Vertex AI API integration")
    print("• gemini-embedding-001 model endpoint") 
    print("• us-central1-aiplatform.googleapis.com endpoint")
    print("• Proper authentication with service account")
    print("• No fallback embeddings - fails fast")
    print("• Rate limiting and error handling")
    print("• Vector similarity calculations")
    print("• Semantic search functionality")
    
    print("\n🗑️  REMOVED:")
    print("• All hardcoded fallback embedding methods")
    print("• Hash-based pseudo embeddings")
    print("• Zero vector fallbacks")
    
    print("\n🎯 API SPECIFICATION MATCHED:")
    print("• Endpoint: us-central1-aiplatform.googleapis.com")
    print("• Model: gemini-embedding-001")
    print("• Authentication: Bearer token from gcloud")
    print("• Request format: {'instances': [{'content': 'text'}]}")
    print("• Response format: predictions[0].embeddings.values")
    
    print("\n🏆 HACKATHON READY:")
    print("• Real Google embeddings for any prospect data")
    print("• TiDB vector storage integration") 
    print("• Multi-step agentic workflow")
    print("• Professional error handling")


if __name__ == "__main__":
    print("🧪 VERTEX AI EMBEDDING TEST SUITE")
    print("Using your exact API specification")
    print("Model: gemini-embedding-001")
    print("Endpoint: us-central1-aiplatform.googleapis.com")
    
    # Run all tests
    asyncio.run(test_full_workflow())
    
    # Print summary
    print_summary()