"""
BFV Context Manager
===================
Manages BFV encryption context (parameters, keys, evaluator instances).

The context encapsulates:
    - Cryptographic parameters
    - Polynomial arithmetic setup
    - Noise budget management
    - Key material references

Thread Safety:
    Context is immutable after initialization.
    Safe for concurrent encryption/evaluation operations.
"""

from Pyfhel import Pyfhel, PyPtxt, PyCtxt
import numpy as np
from typing import Optional
import logging

from ..config.bfv_params import BFVParams

logger = logging.getLogger(__name__)


class BFVContext:
    """
    BFV encryption context.
    
    Provides the foundation for all FHE operations:
        - Parameter setup
        - Key generation hooks
        - Encoder/decoder instances
        - Noise tracking
    
    Attributes:
        params: BFV parameters
        pyfhel: Pyfhel instance (SEAL backend)
        is_initialized: Context initialization status
    
    Design Note:
        This class does NOT generate keys. Keys are loaded from HSM
        via the KeyLoader module to ensure secure key management.
    """
    
    def __init__(self, params: Optional[BFVParams] = None):
        """
        Initialize BFV context.
        
        Args:
            params: BFV parameters (default: standard_128bit)
        """
        self.params = params or BFVParams.standard_128bit()
        self.pyfhel = Pyfhel()
        self.is_initialized = False
        
        logger.info(
            f"Initialized BFV context with n={self.params.poly_modulus_degree}"
        )
    
    def setup(self) -> None:
        """
        Setup BFV context with parameters.
        
        This initializes the polynomial arithmetic, modulus chain,
        and prepares the context for encryption operations.
        
        Note:
            Keys must be loaded separately via load_keys().
        """
        if self.is_initialized:
            logger.warning("Context already initialized, skipping setup")
            return
        
        try:
            # Create context with BFV scheme
            self.pyfhel.contextGen(
                scheme='bfv',
                n=self.params.poly_modulus_degree,
                t_bits=self.params.plain_modulus.bit_length(),
                sec=128  # Security level
            )
            
            # Set plaintext modulus
            self.pyfhel.set_plain_modulus(self.params.plain_modulus)
            
            self.is_initialized = True
            
            logger.info(
                f"✓ BFV context setup complete: "
                f"n={self.params.poly_modulus_degree}, "
                f"t={self.params.plain_modulus}, "
                f"slots={self.params.num_slots}"
            )
            
        except Exception as e:
            logger.error(f"Failed to setup BFV context: {e}")
            raise
    
    def load_keys(
        self,
        public_key: bytes,
        secret_key: Optional[bytes] = None,
        relin_key: Optional[bytes] = None,
        galois_keys: Optional[bytes] = None
    ) -> None:
        """
        Load cryptographic keys into context.
        
        Args:
            public_key: Serialized public key (required)
            secret_key: Serialized secret key (for decryption)
            relin_key: Relinearization key (for multiplication)
            galois_keys: Galois keys (for rotations)
        
        Key Usage:
            - Public key: Encryption only
            - Secret key: Decryption (should be loaded only when needed)
            - Relin key: Required for ciphertext multiplication
            - Galois keys: Required for rotations (Hamming distance)
        
        Security Note:
            Secret key should be loaded only in trusted environments.
            Public key can be freely distributed.
        """
        if not self.is_initialized:
            raise RuntimeError("Context not initialized. Call setup() first.")
        
        try:
            # Load public key (always required)
            self.pyfhel.from_bytes_public_key(public_key)
            logger.info("✓ Loaded public key")
            
            # Load secret key (optional, for decryption)
            if secret_key is not None:
                self.pyfhel.from_bytes_secret_key(secret_key)
                logger.info("✓ Loaded secret key")
            
            # Load relinearization key (for multiplication)
            if relin_key is not None:
                self.pyfhel.from_bytes_relin_key(relin_key)
                logger.info("✓ Loaded relinearization key")
            
            # Load Galois keys (for rotations)
            if galois_keys is not None:
                self.pyfhel.from_bytes_rotate_key(galois_keys)
                logger.info("✓ Loaded Galois keys")
            
        except Exception as e:
            logger.error(f"Failed to load keys: {e}")
            raise
    
    def get_noise_budget(self, ciphertext: PyCtxt) -> int:
        """
        Get remaining noise budget in ciphertext.
        
        Args:
            ciphertext: Encrypted ciphertext
            
        Returns:
            Noise budget in bits
            
        Theory:
            BFV ciphertexts carry inherent noise. Each operation increases noise.
            When noise exceeds plaintext modulus, decryption fails.
            Noise budget indicates remaining operations before overflow.
        """
        try:
            budget = self.pyfhel.noise_level(ciphertext)
            return budget
        except Exception:
            return -1
    
    def encode(self, values: np.ndarray) -> PyPtxt:
        """
        Encode numpy array into BFV plaintext.
        
        Args:
            values: Integer array (length ≤ num_slots)
            
        Returns:
            BFV plaintext
            
        Batching:
            Multiple values are packed into polynomial slots.
            Slot-wise operations enable SIMD-style computation.
        """
        if not self.is_initialized:
            raise RuntimeError("Context not initialized")
        
        # Ensure values fit in plaintext modulus
        values = np.array(values, dtype=np.int64)
        values = values % self.params.plain_modulus
        
        # Encode into plaintext
        ptxt = PyPtxt(values.tolist(), self.pyfhel)
        return ptxt
    
    def decode(self, plaintext: PyPtxt) -> np.ndarray:
        """
        Decode BFV plaintext to numpy array.
        
        Args:
            plaintext: BFV plaintext
            
        Returns:
            Decoded integer array
        """
        if not self.is_initialized:
            raise RuntimeError("Context not initialized")
        
        decoded = self.pyfhel.decode(plaintext)
        return np.array(decoded, dtype=np.int64)
    
    def get_info(self) -> dict:
        """Get context information."""
        return {
            'initialized': self.is_initialized,
            'params': self.params.to_dict(),
            'has_public_key': hasattr(self.pyfhel, '_public_key'),
            'has_secret_key': hasattr(self.pyfhel, '_secret_key'),
            'scheme': 'BFV'
        }
