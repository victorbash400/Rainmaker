"""
Embedding Service for TiDB Vector Search

Provides text embedding capabilities using Google's text-embedding-004 model
for semantic search in TiDB Serverless vector columns.
"""

import asyncio
import json
import os
from typing import List, Dict, Any, Optional
import structlog
import google.generativeai as genai
from app.core.config import settings

logger = structlog.get_logger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings using Google's embedding models.
    Optimized for TiDB vector search with 3072-dimensional embeddings.
    """
    
    def __init__(self):
        """Initialize the embedding service with Google AI using service account"""
        # Set up Google Cloud credentials with proper path handling
        import platform
        
        # Use absolute path based on platform  
        if platform.system() == "Windows":
            service_account_path = r"C:\Users\Victo\Desktop\Rainmaker\Rainmaker-backend\ascendant-woods-462020-n0-78d818c9658e.json"
        else:
            service_account_path = "/mnt/c/Users/Victo/Desktop/Rainmaker/Rainmaker-backend/ascendant-woods-462020-n0-78d818c9658e.json"
        
        # Verify the file exists
        if not os.path.exists(service_account_path):
            # Try alternative path
            alt_path = os.path.join(os.getcwd(), "ascendant-woods-462020-n0-78d818c9658e.json")
            if os.path.exists(alt_path):
                service_account_path = alt_path
            else:
                raise FileNotFoundError(f"Google service account file not found. Tried:\n1. {service_account_path}\n2. {alt_path}")
        
        # Set the credentials environment variable
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_path
        logger.info("Using Google service account file for embedding service", path=service_account_path)

        # Configure the Google AI client
        try:
            genai.configure()
        except Exception as e:
            logger.error("Failed to configure Google AI. Check credentials.", error=str(e))
            raise e
        
        # Use Google's latest embedding model
        self.model_name = "models/text-embedding-004"
        self.embedding_dimensions = 768  # text-embedding-004 produces 768-dimensional embeddings
        
        logger.info("EmbeddingService initialized with Google service account", model=self.model_name, dimensions=self.embedding_dimensions)
    
    async def generate_embedding(self, text: str, task_type: str = "SEMANTIC_SIMILARITY") -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            task_type: Task type for the embedding (SEMANTIC_SIMILARITY, CLASSIFICATION, etc.)
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            # Clean and truncate text if needed
            cleaned_text = self._clean_text(text)
            
            # Generate embedding using Google AI
            result = genai.embed_content(
                model=self.model_name,
                content=cleaned_text,
                task_type=task_type
            )
            
            embedding = result['embedding']
            
            # Pad or truncate to match TiDB vector dimensions (3072)
            # Since text-embedding-004 produces 768 dimensions, we'll pad with zeros
            if len(embedding) < 3072:
                embedding.extend([0.0] * (3072 - len(embedding)))
            elif len(embedding) > 3072:
                embedding = embedding[:3072]
            
            logger.debug("Generated embedding", text_length=len(text), embedding_length=len(embedding))
            return embedding
            
        except Exception as e:
            logger.error("Failed to generate embedding", error=str(e), text_length=len(text))
            raise Exception(f"Embedding generation failed: {str(e)}")
    
    async def generate_embeddings_batch(self, texts: List[str], task_type: str = "SEMANTIC_SIMILARITY") -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of texts to embed
            task_type: Task type for the embeddings
            
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = []
            
            # Process in batches to avoid rate limits
            batch_size = 10
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                # Generate embeddings for this batch
                batch_embeddings = []
                for text in batch:
                    embedding = await self.generate_embedding(text, task_type)
                    batch_embeddings.append(embedding)
                
                embeddings.extend(batch_embeddings)
                
                # Small delay between batches
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)
            
            logger.info("Generated batch embeddings", count=len(embeddings))
            return embeddings
            
        except Exception as e:
            logger.error("Failed to generate batch embeddings", error=str(e), count=len(texts))
            raise Exception(f"Batch embedding generation failed: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """Clean and prepare text for embedding"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        cleaned = " ".join(text.split())
        
        # Truncate if too long (Google AI has token limits)
        max_chars = 30000  # Conservative limit
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars] + "..."
        
        return cleaned
    
    def format_vector_for_tidb(self, embedding: List[float]) -> str:
        """
        Format embedding vector for TiDB VECTOR column insertion.
        
        Args:
            embedding: List of float values
            
        Returns:
            String representation suitable for TiDB VECTOR column
        """
        # Ensure we have exactly 3072 dimensions
        if len(embedding) != 3072:
            if len(embedding) < 3072:
                embedding.extend([0.0] * (3072 - len(embedding)))
            else:
                embedding = embedding[:3072]
        
        # Format as JSON array string for TiDB
        return json.dumps(embedding)
    
    async def store_prospect_research(self, db, prospect_id: int, workflow_id: str,
                                    source_url: str, source_title: str, source_type: str,
                                    search_query: str, content: str,
                                    progress_callback=None) -> List[Dict[str, Any]]:
        """
        Store prospect research data with vector embeddings in TiDB.
        
        Args:
            db: Database session
            prospect_id: ID of the prospect
            workflow_id: Workflow identifier
            source_url: URL of the source
            source_title: Title of the source
            source_type: Type of search (person_search, company_search, event_search)
            search_query: Original search query
            content: Text content to store and embed
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of stored record dictionaries
        """
        try:
            from app.db.models import ProspectScrapedData
            from datetime import datetime
            
            if progress_callback:
                progress_callback(f"🧠 Generating embeddings: '{source_title[:40]}...' | Content: {len(content)} chars")
            
            # Generate embedding for the content
            embedding = await self.generate_embedding(content, "SEMANTIC_SIMILARITY")
            vector_str = self.format_vector_for_tidb(embedding)
            
            # Small delay to ensure frontend can display the embedding process
            await asyncio.sleep(0.3)
            
            if progress_callback:
                progress_callback(f"💾 Storing {len(embedding)}D vector embedding in TiDB | Source: {source_type}")
            
            # Use raw SQL to insert with vector data (SQLAlchemy doesn't handle VECTOR type properly)
            from sqlalchemy import text
            
            result = db.execute(text("""
                INSERT INTO prospect_scraped_data 
                (prospect_id, workflow_id, source_url, source_title, source_type, 
                 search_query, content, content_vector, content_length, chunk_index, 
                 embedding_model, scraped_at, created_at)
                VALUES 
                (:prospect_id, :workflow_id, :source_url, :source_title, :source_type,
                 :search_query, :content, :content_vector, :content_length, :chunk_index,
                 :embedding_model, :scraped_at, NOW())
            """), {
                'prospect_id': prospect_id,
                'workflow_id': workflow_id,
                'source_url': source_url,
                'source_title': source_title,
                'source_type': source_type,
                'search_query': search_query,
                'content': content,
                'content_vector': vector_str,
                'content_length': len(content),
                'chunk_index': 0,
                'embedding_model': "text-embedding-004",
                'scraped_at': datetime.now()
            })
            
            # Get the inserted record ID
            record_id = result.lastrowid
            db.commit()
            
            if progress_callback:
                progress_callback(f"✅ Vector embedding stored successfully | ID: {record_id} | Ready for semantic search")
            
            logger.info("Stored prospect research with vector", 
                       record_id=record_id,
                       content_length=len(content),
                       vector_dimensions=len(embedding))
            
            return [{
                'id': record_id,
                'prospect_id': prospect_id,
                'workflow_id': workflow_id,
                'source_url': source_url,
                'source_title': source_title,
                'source_type': source_type,
                'content_length': len(content)
            }]
            
        except Exception as e:
            logger.error("Failed to store prospect research", error=str(e))
            if progress_callback:
                progress_callback(f"❌ Failed to store research: {str(e)}")
            raise Exception(f"Failed to store prospect research: {str(e)}")

    async def search_similar_content(self, db_session, query_text: str, 
                                   prospect_id: Optional[int] = None, 
                                   source_type: Optional[str] = None,
                                   limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar content using vector similarity in TiDB.
        
        Args:
            db_session: Database session
            query_text: Text to search for
            prospect_id: Optional prospect ID to filter by
            source_type: Optional source type to filter by
            limit: Maximum number of results
            
        Returns:
            List of similar content with similarity scores
        """
        try:
            # Generate embedding for query
            query_embedding = await self.generate_embedding(query_text)
            query_vector = self.format_vector_for_tidb(query_embedding)
            
            # Build SQL query with optional filters
            where_conditions = []
            params = {'query_vector': query_vector, 'limit': limit}
            
            if prospect_id:
                where_conditions.append("prospect_id = :prospect_id")
                params['prospect_id'] = prospect_id
            
            if source_type:
                where_conditions.append("source_type = :source_type")
                params['source_type'] = source_type
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Execute vector similarity search
            from sqlalchemy import text
            sql = f"""
                SELECT 
                    id,
                    prospect_id,
                    workflow_id,
                    source_url,
                    source_title,
                    source_type,
                    content,
                    content_summary,
                    (1 - VEC_COSINE_DISTANCE(content_vector, :query_vector)) as similarity_score
                FROM prospect_scraped_data 
                {where_clause}
                ORDER BY similarity_score DESC
                LIMIT :limit
            """
            
            result = db_session.execute(text(sql), params)
            rows = result.fetchall()
            
            # Convert to list of dictionaries
            similar_content = []
            for row in rows:
                similar_content.append({
                    'id': row.id,
                    'prospect_id': row.prospect_id,
                    'workflow_id': row.workflow_id,
                    'source_url': row.source_url,
                    'source_title': row.source_title,
                    'source_type': row.source_type,
                    'content': row.content,
                    'content_summary': row.content_summary,
                    'similarity_score': float(row.similarity_score)
                })
            
            logger.info("Vector search completed", 
                       query_length=len(query_text), 
                       results_count=len(similar_content))
            
            return similar_content
            
        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            raise Exception(f"Vector search failed: {str(e)}")
    
    async def semantic_analysis(self, db_session, prospect_id: int, 
                              analysis_queries: List[str]) -> Dict[str, Any]:
        """
        Perform semantic analysis on stored prospect data using vector search.
        
        Args:
            db_session: Database session
            prospect_id: Prospect ID to analyze
            analysis_queries: List of analysis questions/queries
            
        Returns:
            Dictionary with analysis results
        """
        try:
            analysis_results = {}
            
            for query in analysis_queries:
                # Search for relevant content
                similar_content = await self.search_similar_content(
                    db_session=db_session,
                    query_text=query,
                    prospect_id=prospect_id,
                    limit=3
                )
                
                # Extract insights from similar content
                insights = []
                for content in similar_content:
                    if content['similarity_score'] > 0.7:  # High similarity threshold
                        insights.append({
                            'source': content['source_title'],
                            'url': content['source_url'],
                            'content_preview': content['content'][:200] + "...",
                            'similarity': content['similarity_score'],
                            'source_type': content['source_type']
                        })
                
                analysis_results[query] = {
                    'insights_found': len(insights),
                    'insights': insights,
                    'total_sources_searched': len(similar_content)
                }
            
            logger.info("Semantic analysis completed", 
                       prospect_id=prospect_id,
                       queries_analyzed=len(analysis_queries),
                       total_insights=sum(len(r['insights']) for r in analysis_results.values()))
            
            return analysis_results
            
        except Exception as e:
            logger.error("Semantic analysis failed", error=str(e))
            raise Exception(f"Semantic analysis failed: {str(e)}")


# Global instance
embedding_service = EmbeddingService()