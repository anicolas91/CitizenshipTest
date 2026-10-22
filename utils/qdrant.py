from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance,PointStruct
from utils.rag import embed

def create_qdrant_collection(
    client: QdrantClient,
    collection_name: str = "usa_civics_guide",
    dimension_size: int = 384,
    distance_metric: Distance = Distance.COSINE,
    recreate: bool = True  # Changed default to True
) -> bool:
    """
    Create a Qdrant collection for storing embeddings, deleting it first if it already exists.
    
    Args:
        client: QdrantClient instance
        collection_name: Name of the collection to create (default: "usa_civics_guide")
        dimension_size: Vector dimension size (default: 384 for BAAI/bge-small-en-v1.5)
        distance_metric: Distance metric to use (default: COSINE)
        recreate: If True, delete existing collection and create new one (default: True)
        
    Returns:
        bool: True if collection was created, False if skipped (when recreate=False and exists)
        
    Example:
        >>> from qdrant_client import QdrantClient
        >>> client = QdrantClient(url="http://localhost:6333")
        >>> # Always recreate (delete if exists, then create)
        >>> created = create_qdrant_collection(client, collection_name="my_collection")
        >>> print(f"Collection created: {created}")
        
    Note:
        Default dimension size (384) matches the BAAI/bge-small-en-v1.5 fastembed model.
        By default, this will delete and recreate the collection to avoid duplicates.
    """
    # Check if collection already exists
    collection_exists = False
    try:
        client.get_collection(collection_name=collection_name)
        collection_exists = True
    except Exception:
        # Collection doesn't exist
        pass
    
    # Delete if exists and recreate is True
    if collection_exists:
        if recreate:
            print(f"Collection '{collection_name}' exists. Deleting...")
            client.delete_collection(collection_name=collection_name)
            print(f"✓ Collection '{collection_name}' deleted successfully!")
        else:
            print(f"Collection '{collection_name}' already exists. Skipping creation.")
            return False
    
    # Create the collection
    print(f"Creating collection '{collection_name}'...")
    print(f"  - Dimension size: {dimension_size}")
    print(f"  - Distance metric: {distance_metric}")
    
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=dimension_size, distance=distance_metric),
    )
    
    print(f"✓ Collection '{collection_name}' created successfully!")
    return True

def create_embedded_points(
    datapoints: List[Dict[str, Any]],
    model: str = "BAAI/bge-small-en-v1.5"
) -> List[PointStruct]:
    """
    Create embedded points from datapoints for Qdrant vector storage.
    
    Takes a list of datapoints with text content, generates embeddings locally
    with fastembed, and creates PointStruct objects ready for insertion into Qdrant.
    
    Args:
        datapoints: List of dictionaries, each containing:
            - "uuid" (str or UUID): Unique identifier
            - "text" (str): Text content to embed
            - "page_no" (int): Page number reference
        model: fastembed embedding model to use (default: "BAAI/bge-small-en-v1.5")
        
    Returns:
        List[PointStruct]: List of Qdrant points ready for insertion
        
    Example:
        >>> datapoints = [{"uuid": "123", "text": "Sample", "page_no": 1}]
        >>> points = create_embedded_points(datapoints)
        
    Raises:
        KeyError: If required keys are missing from datapoints
        Exception: If embedding fails
    """
    points = []
    
    for datapoint in datapoints:
        try:
            # Get main bits
            page_number = datapoint['page_no']
            id = str(datapoint["uuid"])
            page_text = datapoint['text']

            if page_text.strip():
                # Get embedding locally
                embedding = embed([page_text], model=model)[0]
                
                points.append(PointStruct(
                    id=id,
                    vector=embedding,
                    payload={
                        "page_number": page_number,
                        "text": page_text,
                        "source": "USCIS Civics Textbook"
                    }
                ))
                
        except KeyError as e:
            print(f"✗ Error: Missing required key {e} in datapoint, skipping...")
            continue
            
        except Exception as e:
            print(f"✗ Error: Could not create embedding - {str(e)}")
            raise

    print(f"✓ Created {len(points)} embedded points")
    return points