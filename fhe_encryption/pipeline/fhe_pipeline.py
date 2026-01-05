"""
BFV FHE Pipeline
================
High-level API for BFV encryption operations.

This is the main entry point for the module.

Usage:
    >>> from fhe_bfv import BFVPipeline
    >>> import numpy as np
    >>> 
    >>> # Initialize
    >>> pipeline = BFVPipeline()
    >>> 
    >>> # Encrypt
    >>> hash_256 = np.random.randint(0, 2, 256)
    >>> ctxt = pipeline.encrypt(hash_256)
    >>> 
    >>> # Hamming distance
    >>> ctxt_q = pipeline.encrypt(query_hash)
    >>> ctxt_c = pipeline.encrypt(candidate_hash)
    >>> ctxt_hd = pipeline.hamming_distance(ctxt_q, ctxt_c)
    >>> 
    >>> # Decrypt
    >>> hd = pipeline.decrypt_to_int(ctxt_hd)
"""

from Pyfhel import PyCtxt
import numpy as np
from typing import Optional, List, Tuple
import logging

from ..config.bfv_params import BFVParams
from ..context.bfv_context import BFVContext
from ..keys.key_loader import BFVKeyLoader
from ..encoding.binary_encoder import BinaryEncoder
from ..crypto.encryptor import BFVEncryptor
from ..crypto.decryptor import BFVDecryptor
from ..crypto.evaluator import BFVEvaluator
from ..serialization.serializer import BFVSerializer

logger = logging.getLogger(__name__)


class BFVPipeline:
    """
    Complete BFV encryption pipeline.
    
    Provides unified interface for:
        - Encryption
        - Homomorphic operations
        - Decryption
        - Serialization
    
    Key Management:
        All keys loaded from SoftHSM automatically.
        No manual key management required.
    
    Attributes:
        params: BFV parameters
        context: BFV context
        encoder: Binary encoder
        encryptor: Encryptor (optional, requires public key)
        decryptor: Decryptor (optional, requires secret key)
        evaluator: Evaluator
        serializer: Serializer
    """
    
    def __init__(
        self,
        params: Optional[BFVParams] = None,
        load_secret_key: bool = False,
        auto_initialize: bool = True
    ):
        """
        Initialize BFV pipeline.
        
        Args:
            params: BFV parameters (default: standard_128bit)
            load_secret_key: Load secret key for decryption
            auto_initialize: Automatically setup and load keys
            
        Example:
            >>> # For encryption only (server-side)
            >>> pipeline = BFVPipeline(load_secret_key=False)
            >>> 
            >>> # For encryption + decryption (trusted environment)
            >>> pipeline = BFVPipeline(load_secret_key=True)
        """
        # Initialize parameters
        self.params = params or BFVParams.standard_128bit()
        
        # Initialize context
        self.context = BFVContext(self.params)
        
        # Initialize encoder
        self.encoder = BinaryEncoder(
            num_slots=self.params.num_slots,
            plain_modulus=self.params.plain_modulus
        )
        
        # Initialize components (will be set after key loading)
        self.encryptor: Optional[BFVEncryptor] = None
        self.decryptor: Optional[BFVDecryptor] = None
        self.evaluator: Optional[BFVEvaluator] = None
        self.serializer = BFVSerializer()
        
        # Auto-initialize if requested
        if auto_initialize:
            self.setup(load_secret_key=load_secret_key)
        
        logger.info(
            f"Initialized BFV pipeline "
            f"(params={self.params.security_level}, "
            f"secret_key_loaded={load_secret_key})"
        )
    
    def setup(self, load_secret_key: bool = False) -> None:
        """
        Setup pipeline with keys from HSM.
        
        Args:
            load_secret_key: Whether to load secret key
            
        Process:
            1. Setup BFV context
            2. Load keys from SoftHSM
            3. Initialize crypto components
        """
        # Setup context
        self.context.setup()
        
        # Load keys from HSM
        key_loader = BFVKeyLoader()
        
        public_key, secret_key, relin_key, galois_keys = key_loader.load_all_keys(
            include_secret=load_secret_key
        )
        
        # Load into context
        self.context.load_keys(
            public_key=public_key,
            secret_key=secret_key,
            relin_key=relin_key,
            galois_keys=galois_keys
        )
        
        # Initialize components
        self.encryptor = BFVEncryptor(self.context, self.encoder)
        self.evaluator = BFVEvaluator(self.context)
        
        if load_secret_key:
            self.decryptor = BFVDecryptor(self.context, self.encoder)
        
        logger.info("✓ Pipeline setup complete")
    
    # ========================================================================
    # ENCRYPTION API
    # ========================================================================
    
    def encrypt(self, binary_hash: np.ndarray) -> PyCtxt:
        """
        Encrypt binary hash.
        
        Args:
            binary_hash: Binary vector {0,1}^k (e.g., 256-bit)
            
        Returns:
            Encrypted ciphertext
            
        Raises:
            RuntimeError: If encryptor not initialized
            
        Example:
            >>> hash_256 = np.random.randint(0, 2, 256)
            >>> ctxt = pipeline.encrypt(hash_256)
        """
        if self.encryptor is None:
            raise RuntimeError(
                "Encryptor not initialized. Call setup() first."
            )
        
        return self.encryptor.encrypt(binary_hash)
    
    def encrypt_batch(
        self,
        binary_hashes: List[np.ndarray]
    ) -> List[PyCtxt]:
        """
        Encrypt multiple binary hashes.
        
        Args:
            binary_hashes: List of binary vectors
            
        Returns:
            List of ciphertexts
        """
        if self.encryptor is None:
            raise RuntimeError("Encryptor not initialized")
        
        return self.encryptor.encrypt_batch(binary_hashes)
    
    # ========================================================================
    # HOMOMORPHIC OPERATIONS API
    # ========================================================================
    
    def hamming_distance(
        self,
        ctxt_query: PyCtxt,
        ctxt_candidate: PyCtxt,
        hash_length: int = 256
    ) -> PyCtxt:
        """
        Compute encrypted Hamming distance.
        
        Args:
            ctxt_query: Encrypted query hash
            ctxt_candidate: Encrypted candidate hash
            hash_length: Length of binary hashes
            
        Returns:
            Encrypted Hamming distance
            
        Example:
            >>> ctxt_q = pipeline.encrypt(query_hash)
            >>> ctxt_c = pipeline.encrypt(candidate_hash)
            >>> ctxt_hd = pipeline.hamming_distance(ctxt_q, ctxt_c, 256)
            >>> hd = pipeline.decrypt_to_int(ctxt_hd)
            >>> print(f"Hamming distance: {hd}")
        """
        if self.evaluator is None:
            raise RuntimeError("Evaluator not initialized")
        
        return self.evaluator.hamming_distance(
            ctxt_query,
            ctxt_candidate,
            hash_length
        )
    
    def add(self, ctxt1: PyCtxt, ctxt2: PyCtxt) -> PyCtxt:
        """Homomorphic addition."""
        if self.evaluator is None:
            raise RuntimeError("Evaluator not initialized")
        return self.evaluator.add(ctxt1, ctxt2)
    
    def multiply(self, ctxt1: PyCtxt, ctxt2: PyCtxt) -> PyCtxt:
        """Homomorphic multiplication."""
        if self.evaluator is None:
            raise RuntimeError("Evaluator not initialized")
        return self.evaluator.multiply(ctxt1, ctxt2)
    
    def xor(self, ctxt1: PyCtxt, ctxt2: PyCtxt) -> PyCtxt:
        """Encrypted XOR for binary ciphertexts."""
        if self.evaluator is None:
            raise RuntimeError("Evaluator not initialized")
        return self.evaluator.xor_binary(ctxt1, ctxt2)
    
    # ========================================================================
    # DECRYPTION API
    # ========================================================================
    
    def decrypt(
        self,
        ciphertext: PyCtxt,
        hash_length: int = 256
    ) -> np.ndarray:
        """
        Decrypt ciphertext to binary hash.
        
        Args:
            ciphertext: Encrypted ciphertext
            hash_length: Original hash length
            
        Returns:
            Binary hash
            
        Raises:
            RuntimeError: If secret key not loaded
        """
        if self.decryptor is None:
            raise RuntimeError(
                "Decryptor not initialized. "
                "Initialize with load_secret_key=True."
            )
        
        return self.decryptor.decrypt(ciphertext, hash_length)
    
    def decrypt_to_int(self, ciphertext: PyCtxt) -> int:
        """
        Decrypt ciphertext to single integer.
        
        Args:
            ciphertext: Encrypted integer (e.g., Hamming distance)
            
        Returns:
            Decrypted integer value
            
        Example:
            >>> ctxt_hd = pipeline.hamming_distance(ctxt_q, ctxt_c)
            >>> hd = pipeline.decrypt_to_int(ctxt_hd)
        """
        if self.decryptor is None:
            raise RuntimeError("Decryptor not initialized")
        
        return self.decryptor.decrypt_to_int(ciphertext)
    
    def decrypt_batch(
        self,
        ciphertexts: List[PyCtxt],
        hash_length: int = 256
    ) -> List[np.ndarray]:
        """Decrypt multiple ciphertexts."""
        if self.decryptor is None:
            raise RuntimeError("Decryptor not initialized")
        
        return self.decryptor.decrypt_batch(ciphertexts, hash_length)
    
    # ========================================================================
    # SERIALIZATION API
    # ========================================================================
    
    def serialize(self, ciphertext: PyCtxt, format: str = 'bytes') -> any:
        """
        Serialize ciphertext.
        
        Args:
            ciphertext: Ciphertext to serialize
            format: 'bytes', 'base64', or 'hex'
            
        Returns:
            Serialized ciphertext in specified format
        """
        if format == 'bytes':
            return self.serializer.serialize_to_bytes(ciphertext)
        elif format == 'base64':
            return self.serializer.serialize_to_base64(ciphertext)
        elif format == 'hex':
            return self.serializer.serialize_to_hex(ciphertext)
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def deserialize(self, data: any, format: str = 'bytes') -> PyCtxt:
        """
        Deserialize ciphertext.
        
        Args:
            data: Serialized ciphertext
            format: 'bytes', 'base64', or 'hex'
            
        Returns:
            Reconstructed ciphertext
        """
        if format == 'bytes':
            return self.serializer.deserialize_from_bytes(
                data,
                self.context.pyfhel
            )
        elif format == 'base64':
            return self.serializer.deserialize_from_base64(
                data,
                self.context.pyfhel
            )
        elif format == 'hex':
            return self.serializer.deserialize_from_hex(
                data,
                self.context.pyfhel
            )
        else:
            raise ValueError(f"Unknown format: {format}")
    
    # ========================================================================
    # UTILITY API
    # ========================================================================
    
    def get_noise_budget(self, ciphertext: PyCtxt) -> int:
        """
        Get remaining noise budget.
        
        Args:
            ciphertext: Ciphertext to inspect
            
        Returns:
            Noise budget in bits
        """
        return self.context.get_noise_budget(ciphertext)
    
    def get_ciphertext_size(self, ciphertext: PyCtxt) -> dict:
        """
        Get ciphertext size information.
        
        Args:
            ciphertext: Ciphertext to analyze
            
        Returns:
            Size information dictionary
        """
        return self.serializer.get_size_info(ciphertext)
    
    def get_info(self) -> dict:
        """
        Get pipeline information.
        
        Returns:
            Dictionary with pipeline status
        """
        return {
            'params': self.params.to_dict(),
            'context': self.context.get_info(),
            'encryptor_ready': self.encryptor is not None,
            'decryptor_ready': self.decryptor is not None,
            'evaluator_ready': self.evaluator is not None
        }
