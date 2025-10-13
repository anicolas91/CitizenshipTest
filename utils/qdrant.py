from typing import List, Dict, Any
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance,PointStruct

def create_qdrant_collection(
    client: QdrantClient,
    collection_name: str = "usa_civics_guide",
    dimension_size: int = 1536,
    distance_metric: Distance = Distance.COSINE,
    recreate: bool = False
) -> bool:
    """
    Create a Qdrant collection for storing embeddings, or skip if it already exists.
    
    Args:
        client: QdrantClient instance
        collection_name: Name of the collection to create (default: "usa_civics_guide")
        dimension_size: Vector dimension size (default: 1536 for text-embedding-3-small)
        distance_metric: Distance metric to use (default: COSINE)
        recreate: If True, delete existing collection and create new one (default: False)
        
    Returns:
        bool: True if collection was created, False if it already existed
        
    Example:
        >>> from qdrant_client import QdrantClient
        >>> client = QdrantClient(url="http://localhost:6333")
        >>> created = create_qdrant_collection(client, collection_name="my_collection")
        >>> print(f"Collection created: {created}")
        
    Note:
        Default dimension size (1536) is optimized for OpenAI's text-embedding-3-small model.
    """
    # Check if collection already exists
    try:
        client.get_collection(collection_name=collection_name)
        
        if recreate:
            print(f"Collection '{collection_name}' exists. Deleting and recreating...")
            client.delete_collection(collection_name=collection_name)
            # Continue to create new collection
        else:
            print(f"Collection '{collection_name}' already exists. Skipping creation.")
            return False
            
    except Exception:
        # Collection doesn't exist, will create it
        pass
    
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
    openai_client: OpenAI,
    model: str = "text-embedding-3-small"
) -> List[PointStruct]:
    """
    Create embedded points from datapoints for Qdrant vector storage.
    
    Takes a list of datapoints with text content, generates embeddings using OpenAI's
    API, and creates PointStruct objects ready for insertion into Qdrant.
    
    Args:
        datapoints: List of dictionaries, each containing:
            - "uuid" (str or UUID): Unique identifier
            - "text" (str): Text content to embed
            - "page_no" (int): Page number reference
        openai_client: OpenAI client instance for generating embeddings
        model: OpenAI embedding model to use (default: "text-embedding-3-small")
        
    Returns:
        List[PointStruct]: List of Qdrant points ready for insertion
        
    Example:
        >>> from openai import OpenAI
        >>> client = OpenAI()
        >>> datapoints = [{"uuid": "123", "text": "Sample", "page_no": 1}]
        >>> points = create_embedded_points(datapoints, client)
        
    Raises:
        KeyError: If required keys are missing from datapoints
        Exception: If OpenAI API call fails
    """
    points = []
    
    for datapoint in datapoints:
        try:
            # Get main bits
            page_number = datapoint['page_no']
            id = str(datapoint["uuid"])
            page_text = datapoint['text']

            if page_text.strip():
                # Get embedding from OpenAI
                response = openai_client.embeddings.create(
                    model=model,
                    input=page_text
                )
                embedding = response.data[0].embedding
                
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