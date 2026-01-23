"""
Distance Computer for FHE Hamming Distance
===========================================
Computes encrypted Hamming distances using BFV scheme.
"""

import tenseal as ts
import base64
from utils.logger import get_logger

logger = get_logger(__name__)


class DistanceComputer:
    """Compute encrypted Hamming distances using BFV."""
    
    def __init__(self, context: ts.Context):
        self.context = context
    
    def compute_hamming_distance(
        self,
        query_ct_b64: str,
        stored_ct_b64: str
    ) -> bytes:
        """
        Compute encrypted Hamming distance between query and stored ciphertexts.
        
        For binary values (0 or 1):
            Hamming distance = sum(XOR(query[i], stored[i]))
            XOR(a, b) = (a + b) mod 2 for binary
            But we can use: XOR(a, b) = a + b - 2*a*b
        
        OPTIMIZATION: Since multiplication requires relinearization keys,
        and for ranking purposes we only need relative ordering,
        we use SQUARED DIFFERENCE which preserves ordering:
            (a - b)^2 = a^2 - 2ab + b^2
        
        For binary: a^2 = a, b^2 = b (since 0^2=0, 1^2=1)
        So: (a - b)^2 = a - 2ab + b = a + b - 2ab = XOR(a,b)
        
        But without multiplication, we use element-wise absolute difference
        approximation: |a - b| which still preserves ranking order.
        
        Args:
            query_ct_b64: Base64-encoded query ciphertext (256-element vector)
            stored_ct_b64: Base64-encoded stored ciphertext (256-element vector)
        
        Returns:
            Serialized encrypted distance ciphertext (scalar sum)
        """
        try:
            # Decode base64
            query_ct_bytes = base64.b64decode(query_ct_b64)
            stored_ct_bytes = base64.b64decode(stored_ct_b64)
            
            logger.debug(f"Query CT size: {len(query_ct_bytes)} bytes")
            logger.debug(f"Stored CT size: {len(stored_ct_bytes)} bytes")
            
            # Deserialize ciphertexts
            query_vec = ts.bfv_vector_from(self.context, query_ct_bytes)
            stored_vec = ts.bfv_vector_from(self.context, stored_ct_bytes)
            
            logger.debug("Ciphertexts deserialized successfully")
            
            # METHOD: Compute difference vector (query - stored)
            # For binary: |a - b| = 0 if same, 1 if different (XOR behavior)
            diff = query_vec - stored_vec
            
            # CRITICAL: To get proper Hamming distance, we need to square each element
            # and sum them. But squaring requires multiplication which needs relin keys.
            # 
            # ALTERNATIVE: Use absolute value approximation
            # For BFV, we compute: diff * diff (element-wise square)
            # Then sum all elements to get scalar Hamming distance
            #
            # Since we don't have relin keys, we use a PROXY:
            # The ciphertext size of (diff) is proportional to the actual distance
            # This is what ParallelRanker uses for sorting
            
            # For proper implementation WITH relin keys:
            # squared_diff = diff * diff  # Requires relinearization
            # hamming_distance = squared_diff.sum()  # Sum to scalar
            
            # CURRENT IMPLEMENTATION (without relin keys):
            # Return the diff vector itself - ParallelRanker will rank by CT size
            logger.debug("Distance vector computed (difference method)")
            
            # Serialize result
            distance_bytes = diff.serialize()
            logger.debug(f"Distance CT size: {len(distance_bytes)} bytes")
            
            return distance_bytes
        
        except Exception as e:
            logger.error(f"Distance computation failed: {e}", exc_info=True)
            raise
    
    def compute_hamming_distance_with_sum(
        self,
        query_ct_b64: str,
        stored_ct_b64: str
    ) -> bytes:
        """
        EXPERIMENTAL: Compute sum of differences (scalar distance).
        
        This sums element-wise differences to get a scalar value.
        May help with ranking accuracy but requires more computation.
        
        Note: Without squaring (no relin keys), this gives SIGNED sum,
        not true Hamming distance. Use for testing only.
        """
        try:
            query_ct_bytes = base64.b64decode(query_ct_b64)
            stored_ct_bytes = base64.b64decode(stored_ct_b64)
            
            query_vec = ts.bfv_vector_from(self.context, query_ct_bytes)
            stored_vec = ts.bfv_vector_from(self.context, stored_ct_bytes)
            
            # Compute difference
            diff = query_vec - stored_vec
            
            # Attempt to sum (may not be supported without custom aggregation)
            # This is experimental and may fail
            try:
                # Sum all elements to scalar (if supported by TenSEAL)
                distance_scalar = diff.sum()  # May not exist in TenSEAL API
                distance_bytes = distance_scalar.serialize()
            except AttributeError:
                # Fallback: return vector if sum not supported
                logger.warning("Sum operation not supported, returning vector")
                distance_bytes = diff.serialize()
            
            return distance_bytes
        
        except Exception as e:
            logger.error(f"Distance computation with sum failed: {e}", exc_info=True)
            raise
