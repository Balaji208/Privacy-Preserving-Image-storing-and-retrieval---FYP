"""
LSH Key Setup Module
====================
Integrated key setup for LSH tokenization with image tracking.

This module handles:
    - HMAC key initialization in SoftHSM
    - Image-based hash_id generation
    - Metadata management
    - Complete LSH indexer setup
"""

import hashlib
import numpy as np
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class LSHKeySetup:
    """
    Setup and manage LSH HMAC keys in SoftHSM.
    
    This class provides one-time setup functionality for initializing
    the LSH tokenization system with proper key management.
    """
    
    @staticmethod
    def initialize_hmac_key(overwrite: bool = False) -> bytes:
        """
        Initialize HMAC key in SoftHSM.
        
        Args:
            overwrite: Force generate new key even if exists
            
        Returns:
            32-byte HMAC key
            
        Raises:
            RuntimeError: If HSM not available or setup fails
            
        Example:
            >>> from lsh_tokenization.setup import LSHKeySetup
            >>> key = LSHKeySetup.initialize_hmac_key()
            >>> print(f"HMAC key initialized: {key.hex()[:16]}...")
        """
        from ..utils.security import SecurityUtils
        from ..utils.hsm_key_manager import HSMKeyManager
        
        try:
            # Initialize HSM manager
            hsm_manager = HSMKeyManager()
            
            # Check if key already exists
            if not overwrite and hsm_manager.key_exists():
                logger.info("HMAC key already exists in HSM, retrieving...")
                return hsm_manager.retrieve_hmac_key()
            
            # Generate new key
            logger.info("Generating new HMAC key...")
            new_key = SecurityUtils.generate_hmac_key()
            
            # Store in HSM
            success = hsm_manager.store_hmac_key(new_key, overwrite=overwrite)
            
            if not success:
                raise RuntimeError("Failed to store HMAC key in HSM")
            
            logger.info(
                f"✓ HMAC key initialized in HSM: {new_key.hex()[:16]}..."
            )
            
            return new_key
            
        except Exception as e:
            logger.error(f"Failed to initialize HMAC key: {e}")
            raise RuntimeError(f"HMAC key initialization failed: {e}") from e
    
    @staticmethod
    def verify_setup() -> Dict[str, bool]:
        """
        Verify LSH setup is complete.
        
        Returns:
            Dictionary with setup status
            
        Example:
            >>> status = LSHKeySetup.verify_setup()
            >>> if all(status.values()):
            ...     print("✓ LSH setup complete")
        """
        from ..utils.hsm_key_manager import HSMKeyManager
        
        status = {
            'hsm_available': False,
            'hmac_key_exists': False,
            'key_valid': False
        }
        
        try:
            # Check HSM
            hsm_manager = HSMKeyManager()
            status['hsm_available'] = True
            
            # Check key exists
            if hsm_manager.key_exists():
                status['hmac_key_exists'] = True
                
                # Validate key
                key = hsm_manager.retrieve_hmac_key()
                if len(key) == 32:
                    status['key_valid'] = True
        
        except Exception as e:
            logger.error(f"Setup verification failed: {e}")
        
        return status
    
    @staticmethod
    def print_setup_status():
        """
        Print human-readable setup status.
        
        Example:
            >>> LSHKeySetup.print_setup_status()
            ✓ HSM available
            ✓ HMAC key exists
            ✓ Key valid
        """
        status = LSHKeySetup.verify_setup()
        
        print("\n" + "=" * 70)
        print("LSH Setup Status")
        print("=" * 70)
        
        symbols = {True: '✓', False: '✗'}
        
        print(f"\n  {symbols[status['hsm_available']]} HSM available")
        print(f"  {symbols[status['hmac_key_exists']]} HMAC key exists")
        print(f"  {symbols[status['key_valid']]} Key valid")
        
        if all(status.values()):
            print("\n✅ LSH setup is complete and ready!")
        else:
            print("\n⚠ LSH setup incomplete. Run initialize_hmac_key().")
        
        print("=" * 70 + "\n")


class ImageHashID:
    """
    Generate and manage image-based hash identifiers.
    
    Combines image_id and timestamp to create unique hash_ids
    for tracking images in the LSH index.
    """
    
    @staticmethod
    def generate(
        image_id: str,
        timestamp: Optional[datetime] = None,
        use_short_format: bool = True
    ) -> str:
        """
        Generate unique hash_id from image_id and timestamp.
        
        Args:
            image_id: Image identifier (filename, UUID, database ID)
            timestamp: Timestamp (default: current time)
            use_short_format: Use 16-char hash (True) or full 64-char (False)
            
        Returns:
            Unique hash_id string
            
        Example:
            >>> from datetime import datetime
            >>> hash_id = ImageHashID.generate("IMG_001", datetime.now())
            >>> print(hash_id)
            'a3f5b2c1d8e9f012'
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Combine image_id and timestamp
        combined = f"{image_id}_{timestamp.isoformat()}"
        
        # Generate SHA256 hash
        hash_obj = hashlib.sha256(combined.encode('utf-8'))
        full_hash = hash_obj.hexdigest()
        
        # Return short or full hash
        if use_short_format:
            return full_hash[:16]  # 16 hex chars = 64 bits
        else:
            return full_hash  # 64 hex chars = 256 bits
    
    @staticmethod
    def generate_from_path(
        image_path: Path,
        timestamp: Optional[datetime] = None
    ) -> Tuple[str, str]:
        """
        Generate hash_id from image file path.
        
        Args:
            image_path: Path to image file
            timestamp: Optional timestamp
            
        Returns:
            Tuple of (image_id, hash_id)
            
        Example:
            >>> from pathlib import Path
            >>> image_id, hash_id = ImageHashID.generate_from_path(
            ...     Path("./images/patient_001.jpg")
            ... )
            >>> print(f"Image: {image_id}, Hash: {hash_id}")
        """
        # Use filename without extension as image_id
        image_id = Path(image_path).stem
        hash_id = ImageHashID.generate(image_id, timestamp)
        
        return image_id, hash_id
    
    @staticmethod
    def validate(hash_id: str) -> bool:
        """
        Validate hash_id format.
        
        Args:
            hash_id: Hash ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check length (16 or 64 hex chars)
        if len(hash_id) not in [16, 64]:
            return False
        
        # Check if valid hex string
        try:
            int(hash_id, 16)
            return True
        except ValueError:
            return False


class ImageHashMetadata:
    """
    Store and retrieve metadata for indexed images.
    
    Metadata includes:
        - Original image_id
        - Timestamp
        - Hash_id
        - Tenant_id
        - Binary hash checksum
        - Additional custom fields
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize metadata manager.
        
        Args:
            storage_path: Path to JSON metadata file
        """
        self.storage_path = storage_path or Path("lsh_image_metadata.json")
        self.metadata: Dict[str, Dict] = {}
        
        # Load existing metadata
        if self.storage_path.exists():
            self._load()
        
        logger.info(f"Metadata manager initialized: {self.storage_path}")
    
    def add(
        self,
        hash_id: str,
        image_id: str,
        tenant_id: str,
        timestamp: Optional[datetime] = None,
        binary_hash: Optional[np.ndarray] = None,
        **kwargs
    ) -> None:
        """
        Add metadata for image hash.
        
        Args:
            hash_id: Generated hash_id
            image_id: Original image identifier
            tenant_id: Tenant identifier
            timestamp: Indexing timestamp
            binary_hash: Binary hash (optional, for verification)
            **kwargs: Additional custom fields
            
        Example:
            >>> metadata.add(
            ...     hash_id="a3f5b2c1d8e9f012",
            ...     image_id="IMG_001",
            ...     tenant_id="hospital_A",
            ...     patient_id="P12345",
            ...     modality="CT"
            ... )
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        entry = {
            'hash_id': hash_id,
            'image_id': image_id,
            'tenant_id': tenant_id,
            'timestamp': timestamp.isoformat(),
            'added_at': datetime.now().isoformat(),
        }
        
        # Add binary hash checksum if provided
        if binary_hash is not None:
            entry['binary_hash_sha256'] = hashlib.sha256(
                binary_hash.tobytes()
            ).hexdigest()[:16]
        
        # Add custom fields
        entry.update(kwargs)
        
        self.metadata[hash_id] = entry
        
        logger.debug(f"Added metadata for hash_id: {hash_id}")
    
    def get(self, hash_id: str) -> Optional[Dict]:
        """Get metadata for hash_id."""
        return self.metadata.get(hash_id)
    
    def search_by_image_id(self, image_id: str) -> List[Dict]:
        """Find all hash_ids for given image_id."""
        results = []
        for entry in self.metadata.values():
            if entry.get('image_id') == image_id:
                results.append(entry)
        return results
    
    def search_by_tenant(self, tenant_id: str) -> List[Dict]:
        """Find all hash_ids for given tenant."""
        results = []
        for entry in self.metadata.values():
            if entry.get('tenant_id') == tenant_id:
                results.append(entry)
        return results
    
    def save(self) -> None:
        """Save metadata to disk."""
        with open(self.storage_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        
        logger.info(f"Saved {len(self.metadata)} entries to {self.storage_path}")
    
    def _load(self) -> None:
        """Load metadata from disk."""
        try:
            with open(self.storage_path, 'r') as f:
                self.metadata = json.load(f)
            
            logger.info(
                f"Loaded {len(self.metadata)} entries from {self.storage_path}"
            )
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            self.metadata = {}
    
    def clear(self) -> None:
        """Clear all metadata."""
        self.metadata = {}
        if self.storage_path.exists():
            self.storage_path.unlink()
        
        logger.info("Cleared all metadata")
    
    def stats(self) -> Dict:
        """Get metadata statistics."""
        tenants = set(e.get('tenant_id') for e in self.metadata.values())
        image_ids = set(e.get('image_id') for e in self.metadata.values())
        
        return {
            'total_entries': len(self.metadata),
            'unique_tenants': len(tenants),
            'unique_image_ids': len(image_ids),
            'storage_path': str(self.storage_path)
        }


class LSHImageIndexer:
    """
    High-level interface for indexing images with LSH.
    
    Combines:
        - ImageHashID generation
        - LSH indexing
        - Metadata management
    
    Example:
        >>> from lsh_tokenization.setup import LSHImageIndexer
        >>> 
        >>> indexer = LSHImageIndexer(lsh_indexer)
        >>> 
        >>> success, hash_id = indexer.add_image(
        ...     binary_hash=hash_256bit,
        ...     image_id="IMG_001",
        ...     tenant_id="hospital_A"
        ... )
    """
    
    def __init__(
        self,
        lsh_indexer,
        metadata_manager: Optional[ImageHashMetadata] = None
    ):
        """
        Initialize image indexer.
        
        Args:
            lsh_indexer: LSHIndexer instance
            metadata_manager: Optional metadata manager
        """
        self.lsh_indexer = lsh_indexer
        self.metadata = metadata_manager or ImageHashMetadata()
        
        logger.info("Initialized LSH image indexer")
    
    def add_image(
        self,
        binary_hash: np.ndarray,
        image_id: str,
        tenant_id: str,
        timestamp: Optional[datetime] = None,
        **metadata_fields
    ) -> Tuple[bool, str]:
        """
        Add image hash to LSH index with metadata.
        
        Args:
            binary_hash: Binary hash (256-bit)
            image_id: Image identifier
            tenant_id: Tenant identifier
            timestamp: Optional timestamp
            **metadata_fields: Additional metadata
            
        Returns:
            Tuple of (success, hash_id)
            
        Example:
            >>> success, hash_id = indexer.add_image(
            ...     binary_hash=hash_256bit,
            ...     image_id="IMG_001",
            ...     tenant_id="hospital_A",
            ...     patient_id="P12345",
            ...     modality="CT"
            ... )
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Generate hash_id
        hash_id = ImageHashID.generate(image_id, timestamp)
        
        # Add to LSH index
        success = self.lsh_indexer.add(
            binary_hash=binary_hash,
            tenant_id=tenant_id,
            hash_id=hash_id
        )
        
        if success:
            # Add metadata
            self.metadata.add(
                hash_id=hash_id,
                image_id=image_id,
                tenant_id=tenant_id,
                timestamp=timestamp,
                binary_hash=binary_hash,
                **metadata_fields
            )
            
            logger.info(
                f"Indexed image: image_id={image_id}, hash_id={hash_id}"
            )
        else:
            logger.error(f"Failed to index image: {image_id}")
        
        return success, hash_id
    
    def add_image_from_path(
        self,
        binary_hash: np.ndarray,
        image_path: Path,
        tenant_id: str,
        **metadata_fields
    ) -> Tuple[bool, str, str]:
        """
        Add image from file path.
        
        Args:
            binary_hash: Binary hash
            image_path: Path to image file
            tenant_id: Tenant identifier
            **metadata_fields: Additional metadata
            
        Returns:
            Tuple of (success, image_id, hash_id)
        """
        # Generate image_id and hash_id from path
        image_id, hash_id = ImageHashID.generate_from_path(image_path)
        
        # Add to LSH
        success = self.lsh_indexer.add(
            binary_hash=binary_hash,
            tenant_id=tenant_id,
            hash_id=hash_id
        )
        
        if success:
            # FIX: Don't pass timestamp as a positional arg, let metadata.add handle it
            # Remove 'timestamp' from metadata_fields if it exists to avoid duplicate
            timestamp_arg = metadata_fields.pop('timestamp', None)
            
            # Add metadata with file path
            self.metadata.add(
                hash_id=hash_id,
                image_id=image_id,
                tenant_id=tenant_id,
                timestamp=timestamp_arg,  # Pass as keyword arg
                binary_hash=binary_hash,
                file_path=str(image_path),
                **metadata_fields
            )
        
        return success, image_id, hash_id

    def query_image(
        self,
        binary_hash: np.ndarray,
        tenant_id: str,
        return_metadata: bool = True
    ) -> List[Dict]:
        """
        Query for similar images.
        
        Args:
            binary_hash: Query binary hash
            tenant_id: Tenant identifier
            return_metadata: Include full metadata
            
        Returns:
            List of results with metadata
            
        Example:
            >>> results = indexer.query_image(query_hash, "hospital_A")
            >>> for result in results:
            ...     print(f"Image: {result['image_id']}")
        """
        # Query LSH index
        candidate_hash_ids = self.lsh_indexer.query(
            binary_hash=binary_hash,
            tenant_id=tenant_id
        )
        
        logger.info(
            f"Query returned {len(candidate_hash_ids)} candidates"
        )
        
        # Enrich with metadata
        if return_metadata:
            results = []
            for hash_id in candidate_hash_ids:
                metadata = self.metadata.get(hash_id)
                if metadata:
                    results.append(metadata)
                else:
                    # Hash ID without metadata
                    results.append({'hash_id': hash_id})
            return results
        else:
            return [{'hash_id': hid} for hid in candidate_hash_ids]
    
    def get_image_info(self, image_id: str) -> List[Dict]:
        """Get all indexed versions of an image."""
        return self.metadata.search_by_image_id(image_id)
    
    def save_metadata(self) -> None:
        """Save metadata to disk."""
        self.metadata.save()
    
    def get_stats(self) -> Dict:
        """Get comprehensive statistics."""
        lsh_stats = self.lsh_indexer.get_stats()
        metadata_stats = self.metadata.stats()
        
        return {
            'lsh': lsh_stats,
            'metadata': metadata_stats
        }


def quick_setup(redis_client, overwrite_key: bool = False):
    """
    Quick setup for LSH tokenization.
    
    Args:
        redis_client: Connected Redis client
        overwrite_key: Force regenerate HMAC key
        
    Returns:
        Tuple of (LSHIndexer, LSHImageIndexer)
        
    Example:
        >>> import redis
        >>> from lsh_tokenization.setup import quick_setup
        >>> 
        >>> redis_client = redis.Redis(host='localhost', port=6379, db=0)
        >>> lsh_indexer, image_indexer = quick_setup(redis_client)
        >>> 
        >>> # Ready to use!
        >>> success, hash_id = image_indexer.add_image(...)
    """
    from ..pipeline.index_builder import LSHIndexer
    from ..config.lsh_config import LSHConfig
    
    # Initialize HMAC key
    hmac_key = LSHKeySetup.initialize_hmac_key(overwrite=overwrite_key)
    
    # Initialize LSH indexer
    config = LSHConfig(
        hash_length=256,
        num_tables=6,
        bits_per_table=12,
        random_seed=42
    )
    
    lsh_indexer = LSHIndexer(redis_client, hmac_key, config)
    
    # Initialize image indexer
    image_indexer = LSHImageIndexer(lsh_indexer)
    
    logger.info("✓ LSH quick setup complete")
    
    return lsh_indexer, image_indexer
