"""
Pinecone-based Conversation Memory for Proposal Agent
Stores and retrieves conversation history with semantic search
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any
import hashlib

try:
    from pinecone import Pinecone, ServerlessSpec
except ImportError:
    raise ImportError("Please install pinecone-client: pip install pinecone-client")


class PineconeMemory:
    """
    Manages conversation memory using Pinecone vector database.
    Stores conversation turns, proposal states, and retrieves context for new messages.
    """
    
    def __init__(self):
        """Initialize Pinecone connection"""
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "proposal-agent")
        self.environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
        self.namespace = os.getenv("PINECONE_NAMESPACE", "default")
        
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY not set in environment")
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=self.api_key)
        
        # Get or create index
        self._ensure_index()
        self.index = self.pc.Index(self.index_name)
    
    def _ensure_index(self):
        """Create index if it doesn't exist"""
        try:
            # Check if index exists
            indexes = self.pc.list_indexes()
            index_names = [idx.get("name") for idx in indexes.get("indexes", [])]
            
            if self.index_name not in index_names:
                print(f"Creating Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=1536,  # OpenAI embedding dimension
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.environment.split("-")[0] + "-" + self.environment.split("-")[1]
                    )
                )
        except Exception as e:
            print(f"Error ensuring index: {e}")
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        Get embeddings for text using Groq/OpenAI.
        Using mock embeddings for now (replace with actual embeddings in production).
        """
        # TODO: Replace with actual embedding function
        # For now, using a simple hash-based approach
        hash_obj = hashlib.md5(text.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        
        # Generate deterministic embeddings based on hash
        import random
        random.seed(hash_int)
        embedding = [random.random() for _ in range(1536)]
        return embedding
    
    def store_conversation_turn(
        self,
        session_id: str,
        turn_number: int,
        user_message: str,
        assistant_response: str,
        proposal_params: Dict[str, Any],
        proposal_state: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a conversation turn in Pinecone.
        
        Args:
            session_id: Unique session identifier
            turn_number: Conversation turn number
            user_message: User's input
            assistant_response: Bot's response
            proposal_params: Extracted/modified parameters
            proposal_state: Full proposal state
        
        Returns:
            Vector ID stored in Pinecone
        """
        vector_id = f"{session_id}_turn_{turn_number}_{uuid.uuid4().hex[:8]}"
        
        # Combine text for embedding
        combined_text = f"{user_message} {assistant_response}"
        embedding = self._get_embedding(combined_text)
        
        # Prepare metadata
        metadata = {
            "session_id": session_id,
            "turn_number": str(turn_number),
            "timestamp": datetime.utcnow().isoformat(),
            "user_message": user_message[:1000],  # Truncate for storage
            "assistant_response": assistant_response[:1000],
            "proposal_params": json.dumps(proposal_params),
            "proposal_state": json.dumps(proposal_state or {}),
            "type": "conversation_turn"
        }
        
        # Store in Pinecone
        self.index.upsert(
            vectors=[(vector_id, embedding, metadata)],
            namespace=self.namespace
        )
        
        return vector_id
    
    def retrieve_conversation_context(
        self,
        session_id: str,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant conversation context for a query.
        
        Args:
            session_id: Session to search within
            query: User's current message
            top_k: Number of top results to return
        
        Returns:
            List of relevant conversation turns
        """
        # Get embedding for query
        embedding = self._get_embedding(query)
        
        # Search Pinecone
        results = self.index.query(
            vector=embedding,
            top_k=top_k,
            namespace=self.namespace,
            filter={"session_id": {"$eq": session_id}},
            include_metadata=True
        )
        
        # Parse results
        context = []
        for match in results.get("matches", []):
            metadata = match.get("metadata", {})
            context.append({
                "turn_number": int(metadata.get("turn_number", 0)),
                "user_message": metadata.get("user_message"),
                "assistant_response": metadata.get("assistant_response"),
                "proposal_params": json.loads(metadata.get("proposal_params", "{}")),
                "proposal_state": json.loads(metadata.get("proposal_state", "{}")),
                "timestamp": metadata.get("timestamp"),
                "similarity": match.get("score", 0)
            })
        
        return context
    
    def get_session_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get full conversation history for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of turns to retrieve
        
        Returns:
            Ordered list of conversation turns
        """
        # Query for all turns in session
        results = self.index.query(
            vector=[0] * 1536,  # Dummy vector (won't be used with filter)
            top_k=limit,
            namespace=self.namespace,
            filter={"session_id": {"$eq": session_id}},
            include_metadata=True
        )
        
        # Parse and sort by turn number
        history = []
        for match in results.get("matches", []):
            metadata = match.get("metadata", {})
            history.append({
                "turn_number": int(metadata.get("turn_number", 0)),
                "user_message": metadata.get("user_message"),
                "assistant_response": metadata.get("assistant_response"),
                "timestamp": metadata.get("timestamp")
            })
        
        # Sort by turn number
        history.sort(key=lambda x: x.get("turn_number", 0))
        return history
    
    def get_latest_proposal_state(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest proposal state for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Latest proposal parameters and state
        """
        history = self.get_session_history(session_id, limit=1)
        
        if not history:
            return None
        
        latest_turn = history[-1]
        return {
            "params": history[-1].get("proposal_params", {}),
            "state": history[-1].get("proposal_state", {}),
            "turn_number": latest_turn.get("turn_number", 0)
        }
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear all conversation data for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Success status
        """
        try:
            # Delete all vectors for this session
            self.index.delete(
                filter={"session_id": {"$eq": session_id}},
                namespace=self.namespace
            )
            return True
        except Exception as e:
            print(f"Error clearing session: {e}")
            return False


# Global instance
_memory = None


def get_memory() -> PineconeMemory:
    """Get or create Pinecone memory instance"""
    global _memory
    if _memory is None:
        _memory = PineconeMemory()
    return _memory
