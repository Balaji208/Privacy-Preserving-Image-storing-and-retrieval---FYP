"""
fhe/hamming_distance.py (UPDATED - With Galois Keys)
=====================================================

Homomorphic Hamming distance computation using Galois keys for rotations.
"""

import logging
import time
from typing import List, Tuple
import numpy as np
import tenseal as ts

logger = logging.getLogger(__name__)


class HammingDistanceComputer:
    """
    Homomorphic Hamming distance calculator using encrypted operations.
    
    Algorithm:
    1. XOR: encrypted_xor = query ⊕ candidate (using arithmetic)
    2. Popcount: sum all bits using rotations (requires Galois keys)
    
    Security:
    - Uses Galois keys for rotations (safe, no decryption capability)
    - All operations on encrypted data
    - Result remains encrypted until decryption service call
    """
    
    def __init__(self, context: ts.Context):
        """
        Initialize Hamming distance computer.
        
        Args:
            context: TenSEAL BFV context with Galois keys
        
        Raises:
            ValueError: If context is not public
        """
        if not context.is_public():
            raise ValueError(
                "🚨 SECURITY ERROR: Context has secret key! "
                "Must use public context with evaluation keys only."
            )
        
        self.context = context
        logger.info("✓ Hamming distance computer initialized with Galois keys")
    
    def compute_encrypted_xor(
        self,
        query_ct: ts.BFVVector,
        candidate_ct: ts.BFVVector
    ) -> ts.BFVVector:
        """
        Compute homomorphic XOR: query ⊕ candidate
        
        Formula: XOR(a, b) = a + b - 2*a*b
        
        Args:
            query_ct: Encrypted query hash (256-bit)
            candidate_ct: Encrypted candidate hash (256-bit)
        
        Returns:
            Encrypted XOR result
        """
        try:
            # a + b
            sum_ab = query_ct + candidate_ct
            
            # a * b
            product_ab = query_ct * candidate_ct
            
            # 2 * (a * b)
            two_product = product_ab * 2
            
            # XOR = a + b - 2*a*b
            xor_result = sum_ab - two_product
            
            logger.debug("✓ Encrypted XOR computed")
            return xor_result
            
        except Exception as e:
            logger.error(f"XOR computation failed: {e}")
            raise
    
    def compute_encrypted_hamming_distance(
        self,
        encrypted_xor: ts.BFVVector
    ) -> ts.BFVVector:
        """
        Compute Hamming distance as sum of all bits in XOR result.
        
        Uses tree reduction with rotations (requires Galois keys):
        - Rotate vector and add iteratively
        - log2(n) rotations for n elements
        - Result in first slot of ciphertext
        
        Args:
            encrypted_xor: Encrypted XOR result (256 bits)
        
        Returns:
            Encrypted Hamming distance (scalar in first slot)
        
        Algorithm:
            Step 1: Sum adjacent pairs (128 operations)
            Step 2: Sum pairs of pairs (64 operations)
            ...
            Step 8: Final sum in slot 0
        """
        try:
            # Tree reduction using rotations
            # For 256 elements: log2(256) = 8 rotation levels
            
            result = encrypted_xor
            rotation_steps = 8  # log2(256)
            
            for step in range(rotation_steps):
                rotation_amount = 2 ** step
                
                # Rotate and add
                rotated = result.rotate(rotation_amount)
                result = result + rotated
                
                logger.debug(f"  Rotation step {step+1}/{rotation_steps}: shift={rotation_amount}")
            
            # Result is now in first slot (all bits summed)
            logger.debug("✓ Encrypted Hamming distance computed (tree reduction)")
            return result
            
        except Exception as e:
            logger.error(f"Hamming distance computation failed: {e}")
            raise
    
    def compute_distance_full_pipeline(
        self,
        query_ct: ts.BFVVector,
        candidate_ct: ts.BFVVector
    ) -> ts.BFVVector:
        """
        Complete pipeline: XOR + Hamming distance computation.
        
        Args:
            query_ct: Encrypted query hash
            candidate_ct: Encrypted candidate hash
        
        Returns:
            Encrypted Hamming distance (scalar ciphertext)
        """
        # Step 1: XOR
        xor_result = self.compute_encrypted_xor(query_ct, candidate_ct)
        
        # Step 2: Popcount via rotations
        distance = self.compute_encrypted_hamming_distance(xor_result)
        
        return distance
    
    def compute_distances_batch(
        self,
        query_ct: ts.BFVVector,
        candidate_cts: List[ts.BFVVector]
    ) -> List[Tuple[int, ts.BFVVector]]:
        """
        Compute Hamming distances for multiple candidates.
        
        Args:
            query_ct: Encrypted query hash
            candidate_cts: List of encrypted candidate hashes
        
        Returns:
            List of (index, encrypted_distance) tuples
        """
        results = []
        
        logger.info(f"Computing distances for {len(candidate_cts)} candidates...")
        start_time = time.time()
        
        for i, candidate_ct in enumerate(candidate_cts):
            try:
                distance_ct = self.compute_distance_full_pipeline(
                    query_ct,
                    candidate_ct
                )
                results.append((i, distance_ct))
                
                if (i + 1) % 50 == 0:
                    elapsed = time.time() - start_time
                    logger.info(
                        f"  Progress: {i+1}/{len(candidate_cts)} "
                        f"({elapsed:.1f}s)"
                    )
                    
            except Exception as e:
                logger.error(f"Failed for candidate {i}: {e}")
                results.append((i, None))
        
        total_time = time.time() - start_time
        logger.info(
            f"✅ Batch computation complete: "
            f"{len(results)} distances in {total_time:.2f}s"
        )
        
        return results
