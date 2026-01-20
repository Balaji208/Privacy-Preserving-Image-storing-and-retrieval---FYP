"""
TenSEAL Pipeline with SoftHSM Integration
==========================================

Production-ready BFV pipeline using TenSEAL keys from HSM.

All keys loaded from SoftHSM (no .env dependency).

Usage:
    # Server-side (with decryption)
    pipeline = TenSEALHSMPipeline(load_secret_key=True)
    
    # Client-side (encryption only) 
    pipeline = TenSEALHSMPipeline(load_secret_key=False)
"""

import tenseal as ts
import numpy as np
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

# Try to import HSM manager
try:
    from hsm.hsm_manager import get_hsm_manager
    HSM_AVAILABLE = True
except ImportError:
    HSM_AVAILABLE = False
    logger.warning("HSM not available")


class TenSEALHSMPipeline:
    """
    Production-ready TenSEAL BFV pipeline with HSM key management.
    
    Architecture:
    - Full context (with secret) stored in HSM as TENSEAL_BFV_CONTEXT
    - Public context can be derived by making context public
    - All keys loaded from SoftHSM
    """
    
    def __init__(
        self,
        load_secret_key: bool = False,
        auto_initialize: bool = True
    ):
        """
        Initialize TenSEAL pipeline.
        
        Args:
            load_secret_key: Whether to load secret key from HSM
            auto_initialize: Auto-load context on init
        """
        self.load_secret_key = load_secret_key
        self.context = None
        self.hsm = None
        
        if auto_initialize:
            self.setup(load_secret_key=load_secret_key)
            logger.info("✓ TenSEAL HSM Pipeline initialized")
    
    def setup(self, load_secret_key: bool = False) -> None:
        """
        Setup TenSEAL context by loading from HSM.
        
        Args:
            load_secret_key: If True, load full context with secret key
                           If False, load and make context public
        """
        self.load_secret_key = load_secret_key
        
        # Always load from HSM
        self._load_context_from_hsm(load_secret_key=load_secret_key)
        
        logger.info(
            f"✓ TenSEAL context loaded "
            f"(mode: {'server' if load_secret_key else 'client'})"
        )
    
    def _load_context_from_hsm(self, load_secret_key: bool = False) -> None:
        """
        Load TenSEAL context from HSM.
        
        For client mode: Load context and make it public (remove secret key)
        For server mode: Load full context with secret key
        """
        if not HSM_AVAILABLE:
            raise RuntimeError("HSM not available for loading keys")
        
        logger.info("Loading TenSEAL context from HSM...")
        
        try:
            self.hsm = get_hsm_manager()
            
            # Try to load TENSEAL_BFV_CONTEXT (full context with secret)
            try:
                context_bytes = self.hsm.retrieve_secret("TENSEAL_BFV_CONTEXT")
                logger.info(f"✓ Loaded TENSEAL_BFV_CONTEXT from HSM ({len(context_bytes):,} bytes)")
            except Exception as e:
                # Fallback to TENSEAL_PUBLIC_CONTEXT if available
                try:
                    context_bytes = self.hsm.retrieve_secret("TENSEAL_PUBLIC_CONTEXT")
                    logger.info(f"✓ Loaded TENSEAL_PUBLIC_CONTEXT from HSM ({len(context_bytes):,} bytes)")
                except Exception:
                    raise RuntimeError(
                        f"No TenSEAL context found in HSM. "
                        f"Run initialize_system_keys.py first."
                    )
            
            # Deserialize TenSEAL context
            self.context = ts.context_from(context_bytes)
            
            # If client mode, make context public (remove secret key)
            if not load_secret_key:
                logger.info("Making context public (removing secret key)...")
                self.context.make_context_public()
                logger.info("✓ Context is now public (client mode)")
            else:
                logger.info("✓ Context loaded with secret key (server mode)")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load context from HSM: {e}")
    
    # ========================================================================
    # ENCRYPTION API (accepts DeepHash output)
    # ========================================================================
    
    def encrypt(self, binary_hash: np.ndarray):
        """
        Encrypt binary hash (DeepHash output).
        
        Args:
            binary_hash: Binary vector {0,1}^256 from DeepHash
        
        Returns:
            TenSEAL BFV ciphertext
        
        Example:
            >>> deephash_output = deephash_model.generate(image)  # 256-bit
            >>> ciphertext = pipeline.encrypt(deephash_output)
        """
        if not isinstance(binary_hash, np.ndarray):
            binary_hash = np.array(binary_hash)
        
        # Validate input
        if binary_hash.dtype != np.uint8 and binary_hash.dtype != np.int64:
            binary_hash = binary_hash.astype(np.uint8)
        
        # Convert to list of integers for TenSEAL
        plaintext = binary_hash.astype(int).tolist()
        
        # Encrypt using BFV
        ciphertext = ts.bfv_vector(self.context, plaintext)
        
        logger.debug(f"Encrypted binary hash of length {len(binary_hash)}")
        return ciphertext
    
    def encrypt_batch(self, binary_hashes: List[np.ndarray]) -> List:
        """
        Encrypt multiple binary hashes.
        
        Args:
            binary_hashes: List of binary vectors from DeepHash
        
        Returns:
            List of encrypted ciphertexts
        """
        return [self.encrypt(h) for h in binary_hashes]
    
    # ========================================================================
    # HOMOMORPHIC OPERATIONS API
    # ========================================================================
    
    def hamming_distance(
        self,
        ctxt_query,
        ctxt_candidate,
        hash_length: int = 256
    ):
        """
        Compute encrypted Hamming distance.
        
        Args:
            ctxt_query: Encrypted query hash
            ctxt_candidate: Encrypted candidate hash
            hash_length: Length of binary hashes (default: 256)
        
        Returns:
            Encrypted XOR result (for Hamming distance computation)
        """
        # XOR in binary field: (a + b) mod 2
        xor_result = ctxt_query + ctxt_candidate
        
        logger.debug("Computed encrypted Hamming distance")
        return xor_result
    
    def add(self, ctxt1, ctxt2):
        """Homomorphic addition."""
        return ctxt1 + ctxt2
    
    def multiply(self, ctxt1, ctxt2):
        """Homomorphic multiplication."""
        return ctxt1 * ctxt2
    
    def xor(self, ctxt1, ctxt2):
        """
        Encrypted XOR for binary ciphertexts.
        
        For binary values: XOR(a,b) = (a + b) mod 2
        """
        return ctxt1 + ctxt2
    
    # ========================================================================
    # DECRYPTION API (server-side only)
    # ========================================================================

    def decrypt(self, ciphertext, hash_length: int = 256) -> np.ndarray:
        """
        Decrypt ciphertext to binary hash.
        
        Args:
            ciphertext: Encrypted ciphertext
            hash_length: Original hash length (default: 256)
        
        Returns:
            Binary hash {0,1}^hash_length
        
        Raises:
            RuntimeError: If secret key not loaded
        """
        if not self.load_secret_key:
            raise RuntimeError(
                "Secret key not available. Initialize with load_secret_key=True"
            )
        
        # Link ciphertext to this context (server context with secret key)
        ciphertext.link_context(self.context)
        
        # Decrypt using TenSEAL
        decrypted = ciphertext.decrypt()
        
        # Convert to binary (mod 2 for XOR results)
        binary_hash = np.array(decrypted[:hash_length], dtype=int)
        binary_hash = binary_hash % 2
        
        logger.debug(f"Decrypted to binary hash of length {hash_length}")
        return binary_hash.astype(np.uint8)

    def decrypt_to_int(self, ciphertext) -> int:
        """
        Decrypt ciphertext to single integer.
        
        Args:
            ciphertext: Encrypted integer
        
        Returns:
            Decrypted integer value
        
        Use case: Decrypting Hamming distance results
        """
        if not self.load_secret_key:
            raise RuntimeError("Secret key not available")
        
        # Link ciphertext to this context (server context with secret key)
        ciphertext.link_context(self.context)
        
        # Decrypt
        decrypted = ciphertext.decrypt()
        
        # For Hamming distance: count the number of 1s (differences)
        # After XOR, we need to sum and take mod 2 to count actual differences
        binary_result = np.array(decrypted, dtype=int) % 2
        result = int(np.sum(binary_result))
        
        logger.debug(f"Decrypted to integer: {result}")
        return result

    def decrypt_batch(
        self,
        ciphertexts: List,
        hash_length: int = 256
    ) -> List[np.ndarray]:
        """Decrypt multiple ciphertexts."""
        return [self.decrypt(ct, hash_length) for ct in ciphertexts]

    
    # ========================================================================
    # SERIALIZATION API (for storage/transmission)
    # ========================================================================
    
    def serialize(self, ciphertext, format: str = 'bytes') -> bytes:
        """
        Serialize ciphertext for storage or transmission.
        
        Args:
            ciphertext: Ciphertext to serialize
            format: Output format ('bytes' only)
        
        Returns:
            Serialized ciphertext bytes
        """
        if format != 'bytes':
            raise ValueError(f"Only 'bytes' format supported, got '{format}'")
        
        return ciphertext.serialize()
    
    def deserialize(self, data: bytes, format: str = 'bytes'):
        """
        Deserialize ciphertext.
        
        Args:
            data: Serialized ciphertext
            format: Input format ('bytes' only)
        
        Returns:
            Reconstructed ciphertext
        """
        if format != 'bytes':
            raise ValueError(f"Only 'bytes' format supported")
        
        # Deserialize with this context
        ciphertext = ts.bfv_vector_from(self.context, data)
        return ciphertext

    # ========================================================================
    # UTILITY API
    # ========================================================================
    
    def get_ciphertext_size(self, ciphertext) -> dict:
        """
        Get ciphertext size information.
        
        Args:
            ciphertext: Ciphertext to analyze
        
        Returns:
            Size information dictionary
        """
        serialized = ciphertext.serialize()
        return {
            'total_bytes': len(serialized),
            'scheme': 'BFV',
            'backend': 'TenSEAL + SoftHSM'
        }
    
    def get_info(self) -> dict:
        """Get pipeline information."""
        return {
            'context_initialized': self.context is not None,
            'encryptor_ready': True,
            'decryptor_ready': self.load_secret_key,
            'evaluator_ready': True,
            'hsm_enabled': True,
            'backend': 'TenSEAL',
            'scheme': 'BFV',
            'key_storage': 'SoftHSM',
            'mode': 'server' if self.load_secret_key else 'client'
        }


# Alias for compatibility
BFVPipeline = TenSEALHSMPipeline

__all__ = ['TenSEALHSMPipeline', 'BFVPipeline']
