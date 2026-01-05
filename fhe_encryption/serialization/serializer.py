"""
BFV Ciphertext Serialization
=============================
Serializes BFV ciphertexts for storage and transmission.

Formats:
    - Raw bytes (compact)
    - Base64 (text-safe)
    - Hex (human-readable)
"""

from Pyfhel import PyCtxt
import base64
import logging

logger = logging.getLogger(__name__)


class BFVSerializer:
    """
    Serializes and deserializes BFV ciphertexts.
    
    Use Cases:
        - Store ciphertexts in database
        - Transmit ciphertexts over network
        - Save encrypted hashes to disk
    """
    
    @staticmethod
    def serialize_to_bytes(ciphertext: PyCtxt) -> bytes:
        """
        Serialize ciphertext to raw bytes.
        
        Args:
            ciphertext: Ciphertext to serialize
            
        Returns:
            Serialized bytes
            
        Note:
            Most compact format. Use for storage.
        """
        ctxt_bytes = ciphertext.to_bytes()
        
        logger.debug(f"Serialized ciphertext to {len(ctxt_bytes)} bytes")
        
        return ctxt_bytes
    
    @staticmethod
    def deserialize_from_bytes(ctxt_bytes: bytes, pyfhel_instance) -> PyCtxt:
        """
        Deserialize ciphertext from bytes.
        
        Args:
            ctxt_bytes: Serialized ciphertext
            pyfhel_instance: Pyfhel context instance
            
        Returns:
            Reconstructed ciphertext
        """
        ctxt = PyCtxt(pyfhel=pyfhel_instance)
        ctxt.from_bytes(ctxt_bytes)
        
        logger.debug(f"Deserialized ciphertext from {len(ctxt_bytes)} bytes")
        
        return ctxt
    
    @staticmethod
    def serialize_to_base64(ciphertext: PyCtxt) -> str:
        """
        Serialize ciphertext to Base64 string.
        
        Args:
            ciphertext: Ciphertext to serialize
            
        Returns:
            Base64-encoded string
            
        Use Case:
            For JSON APIs, text protocols
        """
        ctxt_bytes = BFVSerializer.serialize_to_bytes(ciphertext)
        b64_str = base64.b64encode(ctxt_bytes).decode('utf-8')
        
        logger.debug(f"Serialized ciphertext to Base64 ({len(b64_str)} chars)")
        
        return b64_str
    
    @staticmethod
    def deserialize_from_base64(b64_str: str, pyfhel_instance) -> PyCtxt:
        """
        Deserialize ciphertext from Base64 string.
        
        Args:
            b64_str: Base64-encoded ciphertext
            pyfhel_instance: Pyfhel context instance
            
        Returns:
            Reconstructed ciphertext
        """
        ctxt_bytes = base64.b64decode(b64_str)
        return BFVSerializer.deserialize_from_bytes(ctxt_bytes, pyfhel_instance)
    
    @staticmethod
    def serialize_to_hex(ciphertext: PyCtxt) -> str:
        """
        Serialize ciphertext to hex string.
        
        Args:
            ciphertext: Ciphertext to serialize
            
        Returns:
            Hex-encoded string
            
        Use Case:
            For debugging, logging
        """
        ctxt_bytes = BFVSerializer.serialize_to_bytes(ciphertext)
        hex_str = ctxt_bytes.hex()
        
        logger.debug(f"Serialized ciphertext to hex ({len(hex_str)} chars)")
        
        return hex_str
    
    @staticmethod
    def deserialize_from_hex(hex_str: str, pyfhel_instance) -> PyCtxt:
        """
        Deserialize ciphertext from hex string.
        
        Args:
            hex_str: Hex-encoded ciphertext
            pyfhel_instance: Pyfhel context instance
            
        Returns:
            Reconstructed ciphertext
        """
        ctxt_bytes = bytes.fromhex(hex_str)
        return BFVSerializer.deserialize_from_bytes(ctxt_bytes, pyfhel_instance)
    
    @staticmethod
    def get_size_info(ciphertext: PyCtxt) -> dict:
        """
        Get size information for ciphertext.
        
        Args:
            ciphertext: Ciphertext to analyze
            
        Returns:
            Dictionary with size metrics
        """
        ctxt_bytes = BFVSerializer.serialize_to_bytes(ciphertext)
        
        return {
            'bytes': len(ctxt_bytes),
            'kilobytes': len(ctxt_bytes) / 1024,
            'base64_chars': len(base64.b64encode(ctxt_bytes)),
            'hex_chars': len(ctxt_bytes.hex())
        }
