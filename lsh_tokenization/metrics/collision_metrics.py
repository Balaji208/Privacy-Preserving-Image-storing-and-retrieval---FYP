"""
Collision Metrics
=================
Utilities for measuring LSH performance and collision rates.
"""

import numpy as np
from typing import List, Dict, Tuple
import logging

from ..simhash.simhash_generator import SimHashGenerator
from ..utils.bit_utils import BitUtils

logger = logging.getLogger(__name__)


class CollisionMetrics:
    """
    Metrics for evaluating LSH performance.
    
    Measures:
        - Collision rates between similar/dissimilar hashes
        - Candidate reduction ratio
        - Average bucket sizes
        - False positive/negative rates
    """
    
    def __init__(self, simhash_generator: SimHashGenerator):
        """
        Initialize metrics calculator.
        
        Args:
            simhash_generator: SimHash generator instance
        """
        self.generator = simhash_generator
        self.config = simhash_generator.config
    
    def compute_collision_rate(
        self,
        hash_pairs: List[Tuple[np.ndarray, np.ndarray]]
    ) -> Dict[str, float]:
        """
        Compute collision rate for hash pairs.
        
        Args:
            hash_pairs: List of (hash1, hash2) tuples
            
        Returns:
            Dictionary with collision statistics
        """
        total_pairs = len(hash_pairs)
        
        if total_pairs == 0:
            return {
                'collision_rate': 0.0,
                'avg_tables_matched': 0.0,
                'total_pairs': 0
            }
        
        total_collisions = 0
        total_tables_matched = 0
        
        for hash1, hash2 in hash_pairs:
            # Generate bucket IDs for both
            buckets1 = self.generator.generate_bucket_ids(hash1)
            buckets2 = self.generator.generate_bucket_ids(hash2)
            
            # Count matching buckets
            matches = sum(b1 == b2 for b1, b2 in zip(buckets1, buckets2))
            total_tables_matched += matches
            
            # Collision if at least one table matches
            if matches > 0:
                total_collisions += 1
        
        return {
            'collision_rate': total_collisions / total_pairs,
            'avg_tables_matched': total_tables_matched / total_pairs,
            'total_pairs': total_pairs,
            'total_collisions': total_collisions
        }
    
    def compute_collision_by_distance(
        self,
        hash_pairs_with_distance: List[Tuple[np.ndarray, np.ndarray, int]]
    ) -> Dict[int, Dict[str, float]]:
        """
        Compute collision rates binned by Hamming distance.
        
        Args:
            hash_pairs_with_distance: List of (hash1, hash2, hamming_dist) tuples
            
        Returns:
            Dictionary mapping distance → collision stats
        """
        from collections import defaultdict
        
        # Group by distance
        distance_groups = defaultdict(list)
        for hash1, hash2, distance in hash_pairs_with_distance:
            distance_groups[distance].append((hash1, hash2))
        
        # Compute metrics for each distance
        results = {}
        for distance, pairs in distance_groups.items():
            metrics = self.compute_collision_rate(pairs)
            metrics['hamming_distance'] = distance
            results[distance] = metrics
        
        return results
    
    def estimate_candidate_reduction(
        self,
        num_database_items: int,
        avg_bucket_size: float
    ) -> Dict[str, float]:
        """
        Estimate candidate reduction ratio.
        
        Args:
            num_database_items: Total items in database
            avg_bucket_size: Average items per bucket
            
        Returns:
            Dictionary with reduction statistics
        """
        # Expected candidates per query = L * avg_bucket_size
        expected_candidates = self.config.num_tables * avg_bucket_size
        
        # Reduction ratio
        reduction_ratio = expected_candidates / num_database_items if num_database_items > 0 else 0.0
        
        # Speedup (inverse of reduction ratio)
        speedup = 1.0 / reduction_ratio if reduction_ratio > 0 else float('inf')
        
        return {
            'num_database_items': num_database_items,
            'avg_bucket_size': avg_bucket_size,
            'expected_candidates': expected_candidates,
            'reduction_ratio': reduction_ratio,
            'speedup': speedup,
            'candidates_percent': reduction_ratio * 100
        }
    
    def compute_bucket_statistics(
        self,
        bucket_sizes: List[int]
    ) -> Dict[str, float]:
        """
        Compute statistics about bucket size distribution.
        
        Args:
            bucket_sizes: List of bucket sizes
            
        Returns:
            Dictionary with distribution statistics
        """
        if not bucket_sizes:
            return {
                'num_buckets': 0,
                'mean': 0.0,
                'std': 0.0,
                'min': 0,
                'max': 0,
                'median': 0.0,
                'total_items': 0
            }
        
        sizes = np.array(bucket_sizes)
        
        return {
            'num_buckets': len(sizes),
            'mean': float(np.mean(sizes)),
            'std': float(np.std(sizes)),
            'min': int(np.min(sizes)),
            'max': int(np.max(sizes)),
            'median': float(np.median(sizes)),
            'p95': float(np.percentile(sizes, 95)),
            'p99': float(np.percentile(sizes, 99)),
            'total_items': int(np.sum(sizes))
        }
    
    def compute_recall_precision(
        self,
        ground_truth_neighbors: List[str],
        retrieved_candidates: List[str]
    ) -> Dict[str, float]:
        """
        Compute recall and precision metrics.
        
        Args:
            ground_truth_neighbors: List of true neighbor IDs
            retrieved_candidates: List of retrieved candidate IDs
            
        Returns:
            Dictionary with recall/precision metrics
        """
        gt_set = set(ground_truth_neighbors)
        retrieved_set = set(retrieved_candidates)
        
        true_positives = len(gt_set.intersection(retrieved_set))
        false_positives = len(retrieved_set - gt_set)
        false_negatives = len(gt_set - retrieved_set)
        
        # Metrics
        recall = true_positives / len(gt_set) if gt_set else 0.0
        precision = true_positives / len(retrieved_set) if retrieved_set else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            'recall': recall,
            'precision': precision,
            'f1_score': f1,
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'num_ground_truth': len(gt_set),
            'num_retrieved': len(retrieved_set)
        }
    
    def benchmark_collision_probability(
        self,
        num_samples: int = 1000
    ) -> Dict[int, float]:
        """
        Benchmark empirical vs theoretical collision probabilities.
        
        Args:
            num_samples: Number of random hash pairs to test
            
        Returns:
            Dictionary mapping Hamming distance → collision rate
        """
        from collections import defaultdict
        
        collision_counts = defaultdict(int)
        distance_counts = defaultdict(int)
        
        # Generate random hash pairs
        for _ in range(num_samples):
            # Random hash
            hash1 = np.random.randint(0, 2, self.config.hash_length, dtype=np.uint8)
            
            # Generate hash2 with controlled Hamming distance
            for target_distance in [0, 32, 64, 96, 128, 160, 192, 224]:
                # Flip target_distance bits
                hash2 = hash1.copy()
                flip_indices = np.random.choice(
                    self.config.hash_length,
                    size=target_distance,
                    replace=False
                )
                hash2[flip_indices] = 1 - hash2[flip_indices]
                
                # Check collision
                buckets1 = self.generator.generate_bucket_ids(hash1)
                buckets2 = self.generator.generate_bucket_ids(hash2)
                
                collided = any(b1 == b2 for b1, b2 in zip(buckets1, buckets2))
                
                distance_counts[target_distance] += 1
                if collided:
                    collision_counts[target_distance] += 1
        
        # Compute rates
        collision_rates = {
            distance: collision_counts[distance] / distance_counts[distance]
            for distance in distance_counts
        }
        
        logger.info(
            f"Benchmarked collision probabilities for {num_samples} samples"
        )
        
        return collision_rates
