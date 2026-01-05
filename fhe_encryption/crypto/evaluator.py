"""
BFV Evaluator
=============
Performs homomorphic operations on BFV ciphertexts.

Supported Operations:
    - Addition (ciphertext + ciphertext)
    - Subtraction (ciphertext - ciphertext)
    - Multiplication (ciphertext × ciphertext) [requires relin key]
    - Rotation (shift slots) [requires Galois keys]
    - Scalar multiplication (ciphertext × plaintext)

Core Feature:
    Encrypted Hamming Distance computation via:
        1. Slot-wise XOR (addition mod 2)
        2. Binary-tree summation using rotations
"""

from Pyfhel import PyCtxt
import numpy as np
import logging

from ..context.bfv_context import BFVContext

logger = logging.getLogger(__name__)


class BFVEvaluator:
    """
    BFV homomorphic evaluation operations.
    
    Provides encrypted arithmetic and Hamming distance computation.
    
    Attributes:
        context: BFV context with evaluation keys
    """
    
    def __init__(self, context: BFVContext):
        """
        Initialize evaluator.
        
        Args:
            context: Initialized BFV context with evaluation keys
        """
        if not context.is_initialized:
            raise RuntimeError("BFV context not initialized")
        
        self.context = context
        
        logger.info("Initialized BFV evaluator")
    
    def add(self, ctxt1: PyCtxt, ctxt2: PyCtxt) -> PyCtxt:
        """
        Homomorphic addition.
        
        Args:
            ctxt1: First ciphertext
            ctxt2: Second ciphertext
            
        Returns:
            Encrypted sum
            
        Theory:
            Enc(a) + Enc(b) = Enc(a + b)
            Noise grows additively (~1 bit per addition)
        """
        result = ctxt1 + ctxt2
        
        logger.debug("Performed homomorphic addition")
        
        return result
    
    def subtract(self, ctxt1: PyCtxt, ctxt2: PyCtxt) -> PyCtxt:
        """
        Homomorphic subtraction.
        
        Args:
            ctxt1: First ciphertext
            ctxt2: Second ciphertext
            
        Returns:
            Encrypted difference
        """
        result = ctxt1 - ctxt2
        
        logger.debug("Performed homomorphic subtraction")
        
        return result
    
    def multiply(self, ctxt1: PyCtxt, ctxt2: PyCtxt) -> PyCtxt:
        """
        Homomorphic multiplication (requires relinearization key).
        
        Args:
            ctxt1: First ciphertext
            ctxt2: Second ciphertext
            
        Returns:
            Encrypted product
            
        Theory:
            Enc(a) × Enc(b) = Enc(a × b)
            Noise grows multiplicatively (~30-50 bits per multiplication)
            Relinearization key reduces ciphertext size after multiplication
        """
        result = ctxt1 * ctxt2
        
        # Relinearize to reduce size
        result = self.context.pyfhel.relinearize(result)
        
        logger.debug("Performed homomorphic multiplication with relinearization")
        
        return result
    
    def rotate(self, ctxt: PyCtxt, steps: int) -> PyCtxt:
        """
        Rotate ciphertext slots (requires Galois keys).
        
        Args:
            ctxt: Ciphertext to rotate
            steps: Number of positions to rotate
                  Positive: rotate right
                  Negative: rotate left
                  
        Returns:
            Rotated ciphertext
            
        Theory:
            Rotation permutes polynomial coefficients cyclically.
            Galois keys enable this automorphism homomorphically.
            Required for tree-based summation in Hamming distance.
            
        Example:
            [a, b, c, d] --rotate(1)--> [d, a, b, c]
            [a, b, c, d] --rotate(-1)--> [b, c, d, a]
        """
        result = self.context.pyfhel.rotate(ctxt, steps)
        
        logger.debug(f"Rotated ciphertext by {steps} positions")
        
        return result
    
    def multiply_plain(self, ctxt: PyCtxt, ptxt_value: int) -> PyCtxt:
        """
        Multiply ciphertext by plaintext scalar.
        
        Args:
            ctxt: Ciphertext
            ptxt_value: Plaintext integer
            
        Returns:
            Scaled ciphertext
            
        Theory:
            Enc(a) × b = Enc(a × b)
            More efficient than ciphertext-ciphertext multiplication
        """
        ptxt = self.context.encode(np.array([ptxt_value]))
        result = ctxt * ptxt
        
        logger.debug(f"Multiplied ciphertext by plaintext {ptxt_value}")
        
        return result
    
    def xor_binary(self, ctxt1: PyCtxt, ctxt2: PyCtxt) -> PyCtxt:
        """
        Encrypted XOR for binary ciphertexts.
        
        Args:
            ctxt1: First binary ciphertext Enc({0,1}^n)
            ctxt2: Second binary ciphertext Enc({0,1}^n)
            
        Returns:
            Encrypted XOR result
            
        Theory:
            XOR(a, b) = (a + b) mod 2
            Since plaintexts are in {0, 1}:
                0 XOR 0 = 0
                0 XOR 1 = 1
                1 XOR 0 = 1
                1 XOR 1 = 0
            This is equivalent to addition modulo 2.
            
        Implementation:
            We compute (ctxt1 + ctxt2) and rely on plaintext modulus
            to handle mod 2 during decryption.
        """
        xor_result = self.add(ctxt1, ctxt2)
        
        logger.debug("Performed encrypted XOR (binary addition)")
        
        return xor_result
    
    def hamming_distance(
        self,
        ctxt_query: PyCtxt,
        ctxt_candidate: PyCtxt,
        hash_length: int
    ) -> PyCtxt:
        """
        Compute encrypted Hamming distance.
        
        Args:
            ctxt_query: Encrypted query hash Enc(q)
            ctxt_candidate: Encrypted candidate hash Enc(c)
            hash_length: Length of binary hashes
            
        Returns:
            Encrypted Hamming distance Enc(HD(q, c))
            
        Theory:
            Hamming distance counts differing bits:
                HD(q, c) = Σ(qi ⊕ ci) for i=0..n-1
            
        Algorithm:
            1. Compute XOR: xor_i = qi ⊕ ci for each slot
            2. Sum all slots using binary-tree reduction:
                - Rotate and add log2(n) times
                - Final result in first slot
                
        Why Galois Keys?:
            Rotation operations require Galois automorphism keys.
            Without them, we cannot shift slots to perform summation.
            
        Example (simplified):
            q = [1, 0, 1, 0]
            c = [1, 1, 0, 0]
            xor = [0, 1, 1, 0]  (XOR result)
            
            Tree reduction:
            [0, 1, 1, 0]
            +
            [1, 0, 0, 1] (rotated by 2)
            =
            [1, 1, 1, 1]
            
            Continue until first slot contains sum = 2
            
        Complexity:
            - XOR: 1 addition
            - Summation: log2(hash_length) rotations + additions
            - Total: O(log n) operations
        """
        # Step 1: Compute XOR
        xor_ctxt = self.xor_binary(ctxt_query, ctxt_candidate)
        
        logger.debug(f"Computing Hamming distance for hash_length={hash_length}")
        
        # Step 2: Binary tree summation
        # We need to sum first hash_length slots
        
        # Start with XOR result
        sum_ctxt = xor_ctxt
        
        # Binary tree reduction
        step = 1
        while step < hash_length:
            # Rotate by 'step' positions
            rotated = self.rotate(xor_ctxt, step)
            
            # Add to accumulator
            sum_ctxt = self.add(sum_ctxt, rotated)
            
            # Double step size
            step *= 2
            
            logger.debug(f"  Summation step: rotated by {step//2}, accumulated")
        
        # Result is now in first slot
        logger.info(
            f"Computed encrypted Hamming distance "
            f"(steps={int(np.log2(hash_length))+1})"
        )
        
        return sum_ctxt
    
    def negate(self, ctxt: PyCtxt) -> PyCtxt:
        """
        Negate ciphertext.
        
        Args:
            ctxt: Ciphertext
            
        Returns:
            Enc(-a) from Enc(a)
        """
        result = -ctxt
        
        logger.debug("Negated ciphertext")
        
        return result
