"""
Document RAG (Retrieval-Augmented Generation) System
Interactive document querying using vector search and LLM
"""

from typing import List, Dict, Optional
import json
import structlog
import boto3
from dataclasses import dataclass

logger = structlog.get_logger(__name__)


@dataclass
class DocumentChunk:
    """A chunk of document text with metadata"""
    text: str
    chunk_id: int
    page_number: Optional[int] = None
    section: Optional[str] = None
    metadata: Optional[Dict] = None


class DocumentRAG:
    """
    RAG system for interactive document querying
    Supports chunking, retrieval, and question answering
    """
    
    def __init__(
        self,
        model_id: str = "amazon.titan-embed-text-v2:0",
        aws_region: str = "us-east-1",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Initialize RAG system
        
        Args:
            model_id: Bedrock model ID for generation
            aws_region: AWS region
            chunk_size: Size of text chunks in characters
            chunk_overlap: Overlap between chunks
        """
        self.model_id = model_id
        self.aws_region = aws_region
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize Bedrock clients
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=aws_region)
        
        # Storage for document chunks
        self.chunks: List[DocumentChunk] = []
        self.document_metadata: Dict = {}
        
        logger.info("rag_initialized", chunk_size=chunk_size, overlap=chunk_overlap)
    
    def index_document(self, document_text: str, metadata: Optional[Dict] = None):
        """
        Index a document for RAG querying
        
        Args:
            document_text: Full document text
            metadata: Optional document metadata
        """
        logger.info("indexing_document", text_length=len(document_text))
        
        # Store metadata
        self.document_metadata = metadata or {}
        
        # Split into chunks
        self.chunks = self._chunk_text(document_text)
        
        logger.info("document_indexed", chunks=len(self.chunks))
    
    def _chunk_text(self, text: str) -> List[DocumentChunk]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Full document text
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start:
                    end = sentence_end + 1
            
            # Extract chunk
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append(DocumentChunk(
                    text=chunk_text,
                    chunk_id=chunk_id,
                    metadata={"start": start, "end": end}
                ))
                chunk_id += 1
            
            # Move to next chunk with overlap
            start = end - self.chunk_overlap
        
        return chunks
    
    async def query(self, question: str, top_k: int = 3) -> Dict:
        """
        Query the document with a question
        
        Args:
            question: User's question
            top_k: Number of relevant chunks to retrieve
            
        Returns:
            Dict with answer and sources
        """
        logger.info("querying_document", question=question)
        
        if not self.chunks:
            return {
                "answer": "No document has been indexed yet. Please upload a document first.",
                "sources": [],
                "confidence": 0.0
            }
        
        # Retrieve relevant chunks
        relevant_chunks = self._retrieve_chunks(question, top_k)
        
        # Generate answer using LLM
        answer = await self._generate_answer(question, relevant_chunks)
        
        return {
            "answer": answer,
            "sources": [
                {
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                    "metadata": chunk.metadata
                }
                for chunk in relevant_chunks
            ],
            "confidence": 0.85  # Placeholder, could implement actual confidence scoring
        }
    
    def _retrieve_chunks(self, question: str, top_k: int) -> List[DocumentChunk]:
        """
        Retrieve most relevant chunks for a question
        Uses simple keyword matching (can be enhanced with embeddings)
        
        Args:
            question: User's question
            top_k: Number of chunks to retrieve
            
        Returns:
            List of relevant DocumentChunk objects
        """
        # Simple keyword-based retrieval
        # In production, use embeddings and vector search
        
        question_lower = question.lower()
        keywords = set(question_lower.split())
        
        # Score each chunk
        scored_chunks = []
        for chunk in self.chunks:
            chunk_lower = chunk.text.lower()
            
            # Count keyword matches
            score = sum(1 for keyword in keywords if keyword in chunk_lower)
            
            # Bonus for exact phrase match
            if question_lower in chunk_lower:
                score += 10
            
            scored_chunks.append((score, chunk))
        
        # Sort by score and return top_k
        scored_chunks.sort(reverse=True, key=lambda x: x[0])
        
        # Return at least 1 chunk, even if score is 0
        if not scored_chunks or scored_chunks[0][0] == 0:
            return self.chunks[:top_k]
        
        return [chunk for score, chunk in scored_chunks[:top_k]]
    
    async def _generate_answer(self, question: str, chunks: List[DocumentChunk]) -> str:
        """
        Generate answer using LLM with retrieved chunks
        
        Args:
            question: User's question
            chunks: Retrieved document chunks
            
        Returns:
            Generated answer
        """
        # Combine chunks into context
        context = "\n\n".join([
            f"[Chunk {chunk.chunk_id}]\n{chunk.text}"
            for chunk in chunks
        ])
        
        # Create prompt
        prompt = f"""Based on the following document excerpts, answer the user's question.
If the answer is not in the provided context, say "I cannot find this information in the document."

Document Context:
{context}

Question: {question}

Answer (be specific and cite chunk numbers when possible):"""
        
        # Call Bedrock
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": 0.3,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            answer = response_body['content'][0]['text']
            
            return answer
            
        except Exception as e:
            logger.error("answer_generation_failed", error=str(e))
            return f"Error generating answer: {str(e)}"
    
    async def chat(self, message: str, conversation_history: List[Dict] = None) -> Dict:
        """
        Chat interface with conversation history
        
        Args:
            message: User's message
            conversation_history: Previous messages
            
        Returns:
            Dict with response and updated history
        """
        if conversation_history is None:
            conversation_history = []
        
        # Add user message to history
        conversation_history.append({
            "role": "user",
            "content": message
        })
        
        # Query document
        result = await self.query(message)
        
        # Add assistant response to history
        conversation_history.append({
            "role": "assistant",
            "content": result["answer"]
        })
        
        return {
            "response": result["answer"],
            "sources": result["sources"],
            "history": conversation_history
        }
    
    def get_document_summary(self) -> Dict:
        """
        Get summary of indexed document
        
        Returns:
            Dict with document statistics
        """
        if not self.chunks:
            return {
                "indexed": False,
                "chunks": 0,
                "total_characters": 0
            }
        
        total_chars = sum(len(chunk.text) for chunk in self.chunks)
        
        return {
            "indexed": True,
            "chunks": len(self.chunks),
            "total_characters": total_chars,
            "metadata": self.document_metadata
        }


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test():
        rag = DocumentRAG()
        
        # Sample document
        document = """
        System Requirements for E-commerce Platform
        
        The system must handle 10,000 concurrent users with 99.9% uptime.
        Performance requirements include response time under 200ms for API calls.
        Security requirements mandate encryption at rest and in transit.
        The database must support ACID transactions.
        Integration with payment gateway is required.
        """
        
        # Index document
        rag.index_document(document)
        
        # Query
        result = await rag.query("What are the performance requirements?")
        print(f"Answer: {result['answer']}")
        print(f"Sources: {len(result['sources'])} chunks")
        
        # Chat
        chat_result = await rag.chat("What about security?")
        print(f"Chat response: {chat_result['response']}")
    
    asyncio.run(test())

