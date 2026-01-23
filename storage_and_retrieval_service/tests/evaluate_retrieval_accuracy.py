"""
Retrieval Accuracy Evaluator
=============================
Evaluates the accuracy of similarity search by comparing query class 
with retrieved image classes.

Handles multi-word class names with spaces (e.g., "Normal cases", "Mild Impairment")

Usage:
    python tests/evaluate_retrieval_accuracy.py
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
import re
from typing import Dict, List, Tuple
from collections import defaultdict
import numpy as np


class RetrievalEvaluator:
    """Evaluate similarity search retrieval accuracy."""
    
    # ✅ UPDATED: Your actual 9 classes (multi-word with spaces)
    KNOWN_CLASSES = [
        'Mild Impairment',
        'Moderate Impairment', 
        'No Impairment',
        'Very Mild Impairment',
        'NORMAL',
        'PNEUMONIA',
        'Bengin cases',
        'Malignant cases',
        'Normal cases'
    ]
    
    def __init__(self, results_dir: str = "retrieved_images"):
        self.results_dir = Path(results_dir)
        
        if not self.results_dir.exists():
            raise FileNotFoundError(f"Results directory not found: {self.results_dir}")
        
        print("=" * 80)
        print("RETRIEVAL ACCURACY EVALUATOR")
        print("=" * 80)
        print(f"Results directory: {self.results_dir}")
        print(f"Known classes ({len(self.KNOWN_CLASSES)}):")
        for cls in self.KNOWN_CLASSES:
            print(f"  - {cls}")
        print("=" * 80)
    
    def extract_class_from_filename(self, filename: str) -> str:
        """
        Extract class name from image filename.
        
        Handles multi-word class names with spaces.
        
        Args:
            filename: Image filename (e.g., "Mild Impairment_53.jpg", "Normal cases_90.jpg")
        
        Returns:
            Class name or "unknown"
        """
        # Remove common prefixes
        filename = filename.replace('QUERY_', '')
        
        # Remove extension
        filename_no_ext = re.sub(r'\.(jpg|jpeg|png|bmp)$', '', filename, flags=re.IGNORECASE)
        
        # ✅ NEW: Try exact match with known classes first (handles multi-word classes)
        # Pattern: <class_name>_<number>_<timestamp> or <class_name>_<number>
        for class_name in self.KNOWN_CLASSES:
            # Check if filename starts with class name followed by underscore
            pattern = rf'^{re.escape(class_name)}_\d+'
            if re.match(pattern, filename_no_ext):
                return class_name
        
        # ✅ Fallback: Try to extract longest matching class substring
        # This handles cases where timestamp is appended
        for class_name in sorted(self.KNOWN_CLASSES, key=len, reverse=True):
            if class_name.lower() in filename_no_ext.lower():
                return class_name
        
        print(f"[WARNING] Could not extract class from: {filename}")
        return "unknown"
    
    def evaluate_single_query(
        self,
        query_session_dir: Path
    ) -> Dict:
        """
        Evaluate accuracy for a single query session.
        
        Args:
            query_session_dir: Directory containing query and retrieved images
        
        Returns:
            Dict with evaluation metrics
        """
        # Find query image (support multiple extensions)
        query_images = []
        for ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            query_images.extend(query_session_dir.glob(f"QUERY_*{ext}"))
            query_images.extend(query_session_dir.glob(f"QUERY_*{ext.upper()}"))
        
        if not query_images:
            print(f"[ERROR] No query image found in {query_session_dir}")
            return None
        
        query_image = query_images[0]
        query_class = self.extract_class_from_filename(query_image.name)
        
        # Load retrieval summary to get rank info
        summary_path = query_session_dir / "retrieval_summary.json"
        if not summary_path.exists():
            print(f"[ERROR] No retrieval_summary.json in {query_session_dir}")
            return None
        
        with open(summary_path, 'r') as f:
            summary = json.load(f)
        
        # Build rank -> image_id mapping from summary
        rank_to_image = {}
        for file_info in summary.get('files', []):
            rank = file_info['rank']
            image_id = file_info['image_id']
            rank_to_image[rank] = image_id
        
        # Sort by rank
        sorted_ranks = sorted(rank_to_image.keys())
        
        # Extract classes for each rank
        retrieved_classes = []
        for rank in sorted_ranks:
            image_id = rank_to_image[rank]
            img_class = self.extract_class_from_filename(image_id)
            retrieved_classes.append(img_class)
        
        num_results = len(retrieved_classes)
        if num_results == 0:
            print(f"[ERROR] No ranked results found in {query_session_dir}")
            return None
        
        # Calculate metrics
        correct_at_k = [1 if cls == query_class else 0 for cls in retrieved_classes]
        
        # Precision@K
        precision_at_k = {}
        for k in [1, 3, 5, 10]:
            if k <= num_results:
                precision_at_k[f'P@{k}'] = sum(correct_at_k[:k]) / k
        
        # Overall precision
        precision = sum(correct_at_k) / num_results if num_results > 0 else 0
        
        # Rank of first correct result
        first_correct_rank = None
        for i, correct in enumerate(correct_at_k, 1):
            if correct:
                first_correct_rank = i
                break
        
        # Mean Reciprocal Rank (MRR)
        mrr = 1.0 / first_correct_rank if first_correct_rank else 0.0
        
        result = {
            'query_session': query_session_dir.name,
            'query_image': query_image.name,
            'query_class': query_class,
            'num_results': num_results,
            'retrieved_classes': retrieved_classes,
            'correct_at_each_rank': correct_at_k,
            'num_correct': sum(correct_at_k),
            'precision': precision,
            'precision_at_k': precision_at_k,
            'first_correct_rank': first_correct_rank,
            'mrr': mrr
        }
        
        return result
    
    def evaluate_all_queries(self) -> Dict:
        """
        Evaluate all query sessions in results directory.
        
        Returns:
            Dict with aggregate metrics across all queries
        """
        # Find all query session directories
        session_dirs = [d for d in self.results_dir.iterdir() 
                       if d.is_dir() and not d.name.startswith('.')]
        
        if not session_dirs:
            print("[ERROR] No query sessions found")
            return {}
        
        print(f"\n📊 Found {len(session_dirs)} query sessions")
        print("=" * 80)
        
        all_results = []
        
        for session_dir in sorted(session_dirs):
            print(f"\n[Evaluating] {session_dir.name}...")
            result = self.evaluate_single_query(session_dir)
            
            if result:
                all_results.append(result)
                
                # Print summary
                query_class = result['query_class']
                num_correct = result['num_correct']
                num_total = result['num_results']
                precision = result['precision']
                
                print(f"  Query class: '{query_class}'")
                print(f"  Correct: {num_correct}/{num_total} ({precision*100:.1f}%)")
                
                if result['first_correct_rank']:
                    print(f"  First correct at rank: {result['first_correct_rank']}")
                else:
                    print(f"  ❌ No correct results found!")
                
                # Show retrieved classes (first 3)
                retrieved_preview = ', '.join(f"'{c}'" for c in result['retrieved_classes'][:3])
                if len(result['retrieved_classes']) > 3:
                    retrieved_preview += '...'
                print(f"  Retrieved: {retrieved_preview}")
        
        if not all_results:
            print("[ERROR] No valid results to evaluate")
            return {}
        
        # Calculate aggregate metrics
        aggregate = self._calculate_aggregate_metrics(all_results)
        
        # Print summary
        self._print_summary(aggregate, all_results)
        
        # Save detailed report
        self._save_report(aggregate, all_results)
        
        return aggregate
    
    def _calculate_aggregate_metrics(self, all_results: List[Dict]) -> Dict:
        """Calculate aggregate metrics across all queries."""
        total_queries = len(all_results)
        
        # Average precision
        avg_precision = np.mean([r['precision'] for r in all_results])
        
        # Average P@K
        avg_p_at_k = {}
        for k in [1, 3, 5, 10]:
            key = f'P@{k}'
            values = [r['precision_at_k'].get(key, 0) for r in all_results 
                     if key in r['precision_at_k']]
            if values:
                avg_p_at_k[key] = np.mean(values)
        
        # Mean Reciprocal Rank (MRR)
        mrr = np.mean([r['mrr'] for r in all_results])
        
        # Per-class breakdown
        class_metrics = defaultdict(lambda: {'total': 0, 'correct': 0, 'precision': []})
        
        for result in all_results:
            query_class = result['query_class']
            if query_class != 'unknown':
                class_metrics[query_class]['total'] += 1
                class_metrics[query_class]['correct'] += result['num_correct']
                class_metrics[query_class]['precision'].append(result['precision'])
        
        # Calculate per-class averages
        per_class = {}
        for class_name, metrics in class_metrics.items():
            per_class[class_name] = {
                'num_queries': metrics['total'],
                'total_correct': metrics['correct'],
                'avg_precision': np.mean(metrics['precision'])
            }
        
        # Count queries with perfect results
        perfect_queries = sum(1 for r in all_results if r['precision'] == 1.0)
        zero_queries = sum(1 for r in all_results if r['num_correct'] == 0)
        
        return {
            'total_queries': total_queries,
            'avg_precision': avg_precision,
            'avg_precision_at_k': avg_p_at_k,
            'mrr': mrr,
            'perfect_queries': perfect_queries,
            'zero_queries': zero_queries,
            'per_class': per_class
        }
    
    def _print_summary(self, aggregate: Dict, all_results: List[Dict]):
        """Print evaluation summary."""
        print("\n" + "=" * 80)
        print("EVALUATION SUMMARY")
        print("=" * 80)
        
        print(f"\n📊 Overall Metrics:")
        print(f"  Total queries: {aggregate['total_queries']}")
        print(f"  Average Precision: {aggregate['avg_precision']*100:.2f}%")
        print(f"  Mean Reciprocal Rank (MRR): {aggregate['mrr']:.4f}")
        
        print(f"\n📈 Precision@K:")
        for k, v in sorted(aggregate['avg_precision_at_k'].items()):
            print(f"  {k}: {v*100:.2f}%")
        
        print(f"\n✅ Query Performance:")
        print(f"  Perfect results (100%): {aggregate['perfect_queries']}/{aggregate['total_queries']}")
        print(f"  Zero results (0%): {aggregate['zero_queries']}/{aggregate['total_queries']}")
        
        print(f"\n🏷️ Per-Class Performance:")
        if aggregate['per_class']:
            for class_name, metrics in sorted(aggregate['per_class'].items()):
                print(f"  {class_name:25s}: "
                      f"{metrics['num_queries']:2d} queries, "
                      f"avg precision = {metrics['avg_precision']*100:.1f}%")
        else:
            print("  No per-class metrics available (all classes were 'unknown')")
        
        print("\n" + "=" * 80)
        
        # Provide interpretation
        avg_p = aggregate['avg_precision']
        p_at_1 = aggregate['avg_precision_at_k'].get('P@1', 0)
        
        print("\n💡 Interpretation:")
        if avg_p >= 0.9:
            print("🎉 Excellent retrieval accuracy!")
        elif avg_p >= 0.7:
            print("✅ Good retrieval accuracy")
        elif avg_p >= 0.5:
            print("⚠️ Moderate retrieval accuracy - consider model improvements")
        else:
            print("❌ Low retrieval accuracy - model needs significant improvement")
        
        if p_at_1 >= 0.8:
            print(f"🎯 Top-1 accuracy is strong ({p_at_1*100:.1f}%)")
        else:
            print(f"⚠️ Top-1 accuracy needs improvement ({p_at_1*100:.1f}%)")
    
    def _save_report(self, aggregate: Dict, all_results: List[Dict]):
        """Save detailed evaluation report."""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.results_dir / f"evaluation_report_{timestamp}.json"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'aggregate_metrics': aggregate,
            'individual_results': all_results
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed report saved: {report_path}")


def main():
    """Run evaluation on all retrieved results."""
    evaluator = RetrievalEvaluator(results_dir="retrieved_images")
    
    aggregate = evaluator.evaluate_all_queries()
    
    if not aggregate:
        print("\n❌ Evaluation failed - no valid results")
        return
    
    print("\n✅ Evaluation complete!")


if __name__ == "__main__":
    main()
