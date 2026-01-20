# fhe_encryption/config/bfv_params.py

"""
BFV Parameter Configuration
============================
Cryptographic parameters for BFV scheme ensuring ≥128-bit security.

Security Analysis:
    - Polynomial modulus degree n = 8192 or 16384
    - Coefficient modulus ~110-220 bits (depending on n)
    - Plaintext modulus chosen for binary operations
    - RLWE security: ≥128 bits (classical), ≥64 bits (quantum)
    
References:
    - Brakerski-Fan-Vercauteren (2012)
    - Homomorphic Encryption Standard (2018)
    - NIST PQC Round 3 security estimates
"""

from dataclasses import dataclass
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BFVParams:
    """
    Immutable BFV cryptographic parameters.
    
    Attributes:
        poly_modulus_degree: Polynomial ring dimension n
            - 4096: Fast, ~100-bit security
            - 8192: Recommended, ~128-bit security
            - 16384: High security, ~192-bit security
            
        coeff_modulus_bits: Coefficient modulus bit sizes
            - List of prime bit sizes
            - Total must not exceed security bound
            - Example: [60, 40, 40, 60] for n=8192
            
        plain_modulus: Plaintext modulus t
            - For binary ops: use small prime (e.g., 2, 1024)
            - Must be coprime to coeff modulus
            
        scale: Scaling factor for encoding (BFV-specific)
            - Typically 2^40 to 2^60
            - Balances precision vs noise
    
    Security Note:
        These parameters provide post-quantum security via RLWE assumption.
        The polynomial modulus degree n determines security level:
        - n=8192 → ~128-bit classical, ~64-bit quantum
        - n=16384 → ~192-bit classical, ~96-bit quantum
    """
    
    poly_modulus_degree: int
    coeff_modulus_bits: List[int]
    plain_modulus: int
    scale: int = 2 ** 40
    
    # Derived parameters
    num_slots: Optional[int] = None
    security_level: str = "128-bit"
    
    def __post_init__(self):
        """Validate parameters."""
        self._validate()
        
        # Compute num_slots (for batching)
        if self.num_slots is None:
            # In BFV with batching, slots = n / 2
            object.__setattr__(self, 'num_slots', self.poly_modulus_degree // 2)
    
    def _validate(self) -> None:
        """
        Validate parameter security and correctness.
        
        Raises:
            ValueError: If parameters are insecure or invalid
        """
        # Validate poly_modulus_degree
        valid_degrees = [4096, 8192, 16384, 32768]
        if self.poly_modulus_degree not in valid_degrees:
            raise ValueError(
                f"poly_modulus_degree must be in {valid_degrees}, "
                f"got {self.poly_modulus_degree}"
            )
        
        # Validate coeff_modulus_bits
        if not self.coeff_modulus_bits:
            raise ValueError("coeff_modulus_bits cannot be empty")
        
        total_bits = sum(self.coeff_modulus_bits)
        
        # Security bounds from HE Standard
        max_bits_map = {
            4096: 109,
            8192: 218,
            16384: 438,
            32768: 881
        }
        
        max_allowed = max_bits_map.get(self.poly_modulus_degree, 218)
        
        if total_bits > max_allowed:
            logger.warning(
                f"Coefficient modulus ({total_bits} bits) may exceed security bound "
                f"({max_allowed} bits) for n={self.poly_modulus_degree}"
            )
        
        # Validate plain_modulus
        if self.plain_modulus < 2:
            raise ValueError(
                f"plain_modulus must be ≥ 2, got {self.plain_modulus}"
            )
        
        logger.info(
            f"BFV parameters validated: n={self.poly_modulus_degree}, "
            f"coeff_bits={total_bits}, plain_mod={self.plain_modulus}"
        )
    
    @classmethod
    def standard_128bit(cls) -> 'BFVParams':
        """
        Standard parameters for 128-bit classical security.
        
        Suitable for binary hash encryption (256-512 bits).
        
        Returns:
            BFVParams with n=8192
        """
        return cls(
            poly_modulus_degree=8192,
            coeff_modulus_bits=[60, 40, 40, 60],  # Total: 200 bits
            plain_modulus=1032193,  # Prime compatible with Pyfhel
            scale=2 ** 40,
            security_level="128-bit classical / 64-bit quantum"
        )
    
    @classmethod
    def standard_192bit(cls) -> 'BFVParams':
        """
        High security parameters for 192-bit classical security.
        
        Returns:
            BFVParams with n=16384
        """
        return cls(
            poly_modulus_degree=16384,
            coeff_modulus_bits=[60, 50, 50, 50, 50, 60],  # Total: 320 bits
            plain_modulus=1032193,
            scale=2 ** 40,
            security_level="192-bit classical / 96-bit quantum"
        )
    
    @classmethod
    def fast_testing(cls) -> 'BFVParams':
        """
        Fast parameters for testing (NOT production).
        
        Returns:
            BFVParams with n=4096
        """
        return cls(
            poly_modulus_degree=4096,
            coeff_modulus_bits=[40, 30, 40],  # Total: 110 bits
            plain_modulus=40961,  # Smaller prime for testing
            scale=2 ** 30,
            security_level="~100-bit (testing only)"
        )
    
    def to_dict(self) -> dict:
        """Export parameters as dictionary."""
        return {
            'poly_modulus_degree': self.poly_modulus_degree,
            'coeff_modulus_bits': self.coeff_modulus_bits,
            'plain_modulus': self.plain_modulus,
            'scale': self.scale,
            'num_slots': self.num_slots,
            'security_level': self.security_level
        }
