"""
Confusion Matrix Generator
==========================
Visualizes which classes are being confused with each other.

Usage:
    python tests/generate_confusion_matrix.py
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict


def load_evaluation_report(results_dir: str = "retrieved_images"):
    """Load latest evaluation report."""
    results_path = Path(results_dir)
    
    # Find latest report
    reports = sorted(results_path.glob("evaluation_report_*.json"))
    if not reports:
        print(f"[ERROR] No evaluation reports found in {results_dir}")
        return None
    
    latest_report = reports[-1]
    print(f"📄 Loading: {latest_report.name}")
    
    with open(latest_report, 'r') as f:
        return json.load(f)


def generate_confusion_matrix(report: dict, top_k: int = 1):
    """
    Generate confusion matrix from evaluation report.
    
    Args:
        report: Evaluation report dict
        top_k: Consider only top-K retrieved results (1=top-1 accuracy)
    
    Returns:
        confusion matrix (numpy array), class names (list)
    """
    individual_results = report['individual_results']
    
    # Get all unique classes
    all_classes = set()
    for result in individual_results:
        all_classes.add(result['query_class'])
        all_classes.update(result['retrieved_classes'][:top_k])
    
    # Remove 'unknown'
    all_classes.discard('unknown')
    all_classes = sorted(all_classes)
    
    if not all_classes:
        print("[ERROR] No valid classes found")
        return None, None
    
    # Create confusion matrix
    n_classes = len(all_classes)
    confusion = np.zeros((n_classes, n_classes), dtype=int)
    
    class_to_idx = {cls: i for i, cls in enumerate(all_classes)}
    
    # Fill confusion matrix (top-k predictions)
    for result in individual_results:
        query_class = result['query_class']
        if query_class == 'unknown':
            continue
        
        query_idx = class_to_idx[query_class]
        
        # Count retrieved classes (top-k)
        for retrieved_class in result['retrieved_classes'][:top_k]:
            if retrieved_class == 'unknown':
                continue
            retrieved_idx = class_to_idx[retrieved_class]
            confusion[query_idx, retrieved_idx] += 1
    
    return confusion, all_classes


def plot_confusion_matrix(
    confusion: np.ndarray, 
    class_names: list,
    save_path: str = "retrieved_images/confusion_matrix.png"
):
    """Plot and save confusion matrix."""
    
    # Normalize by row (query class)
    confusion_normalized = confusion.astype('float')
    row_sums = confusion.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1  # Avoid division by zero
    confusion_normalized = confusion_normalized / row_sums
    
    # Create figure
    plt.figure(figsize=(14, 12))
    
    # Plot heatmap with both normalized colors and raw counts
    sns.heatmap(
        confusion_normalized,
        annot=confusion,  # Show raw counts
        fmt='d',
        cmap='RdYlGn',  # Red (bad) to Green (good)
        xticklabels=class_names,
        yticklabels=class_names,
        cbar_kws={'label': 'Normalized Frequency'},
        vmin=0,
        vmax=1,
        linewidths=0.5,
        linecolor='gray'
    )
    
    plt.title('Confusion Matrix: Query Class vs Retrieved Class (Top-1)', 
              fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Retrieved Class', fontsize=13)
    plt.ylabel('Query Class', fontsize=13)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.yticks(rotation=0, fontsize=10)
    plt.tight_layout()
    
    # Save
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\n📊 Confusion matrix saved: {save_path}")
    
    # Show
    plt.show()


def print_confusion_analysis(confusion: np.ndarray, class_names: list):
    """Print detailed confusion analysis."""
    print("\n" + "=" * 80)
    print("CONFUSION ANALYSIS")
    print("=" * 80)
    
    # Find most confused pairs
    n_classes = len(class_names)
    confusions = []
    
    for i in range(n_classes):
        for j in range(n_classes):
            if i != j and confusion[i, j] > 0:
                total_queries = confusion[i].sum()
                pct = confusion[i, j] / total_queries if total_queries > 0 else 0
                confusions.append((
                    class_names[i],
                    class_names[j],
                    confusion[i, j],
                    pct
                ))
    
    # Sort by frequency
    confusions.sort(key=lambda x: x[2], reverse=True)
    
    print("\n🔴 Most Common Confusions (Query → Retrieved):")
    for query_class, retrieved_class, count, pct in confusions[:10]:
        print(f"  {query_class:30s} → {retrieved_class:30s}: "
              f"{count:3d} times ({pct*100:5.1f}%)")
    
    # Per-class accuracy
    print("\n🎯 Per-Class Top-1 Accuracy:")
    accuracies = []
    for i, class_name in enumerate(class_names):
        total = confusion[i].sum()
        if total > 0:
            accuracy = confusion[i, i] / total
            accuracies.append((class_name, accuracy, total))
            
            # Color code
            if accuracy >= 0.8:
                status = "🟢"
            elif accuracy >= 0.5:
                status = "🟡"
            else:
                status = "🔴"
            
            print(f"  {status} {class_name:30s}: {accuracy*100:5.1f}% ({confusion[i,i]}/{total})")
    
    # Overall statistics
    print("\n📊 Overall Statistics:")
    accuracies_only = [acc for _, acc, _ in accuracies]
    if accuracies_only:
        print(f"  Mean accuracy: {np.mean(accuracies_only)*100:.2f}%")
        print(f"  Median accuracy: {np.median(accuracies_only)*100:.2f}%")
        print(f"  Best class: {max(accuracies, key=lambda x: x[1])[0]} ({max(accuracies, key=lambda x: x[1])[1]*100:.1f}%)")
        print(f"  Worst class: {min(accuracies, key=lambda x: x[1])[0]} ({min(accuracies, key=lambda x: x[1])[1]*100:.1f}%)")


def analyze_cross_domain_confusion(confusion: np.ndarray, class_names: list):
    """Analyze cross-domain confusion (e.g., Brain MRI vs Chest X-ray)."""
    
    print("\n" + "=" * 80)
    print("CROSS-DOMAIN CONFUSION ANALYSIS")
    print("=" * 80)
    
    # Define domain mapping
    domain_map = {
        'Mild Impairment': 'Alzheimer (Brain MRI)',
        'Moderate Impairment': 'Alzheimer (Brain MRI)',
        'No Impairment': 'Alzheimer (Brain MRI)',
        'Very Mild Impairment': 'Alzheimer (Brain MRI)',
        'NORMAL': 'Chest (X-ray)',
        'PNEUMONIA': 'Chest (X-ray)',
        'Bengin cases': 'Lung (CT)',
        'Malignant cases': 'Lung (CT)',
        'Normal cases': 'Lung (CT)'
    }
    
    # Count cross-domain confusions
    cross_domain_count = 0
    within_domain_count = 0
    cross_domain_examples = []
    
    n_classes = len(class_names)
    for i in range(n_classes):
        for j in range(n_classes):
            if i != j and confusion[i, j] > 0:
                query_domain = domain_map.get(class_names[i], 'Unknown')
                retrieved_domain = domain_map.get(class_names[j], 'Unknown')
                
                if query_domain != retrieved_domain:
                    cross_domain_count += confusion[i, j]
                    cross_domain_examples.append((
                        class_names[i],
                        class_names[j],
                        confusion[i, j],
                        query_domain,
                        retrieved_domain
                    ))
                else:
                    within_domain_count += confusion[i, j]
    
    total_errors = cross_domain_count + within_domain_count
    
    print(f"\n📊 Error Distribution:")
    print(f"  Within-domain errors: {within_domain_count} ({within_domain_count/total_errors*100:.1f}%)")
    print(f"  Cross-domain errors: {cross_domain_count} ({cross_domain_count/total_errors*100:.1f}%)")
    
    if cross_domain_examples:
        # Sort by count
        cross_domain_examples.sort(key=lambda x: x[2], reverse=True)
        
        print(f"\n🔴 Top Cross-Domain Confusions:")
        for query, retrieved, count, q_domain, r_domain in cross_domain_examples[:5]:
            print(f"  {query:25s} ({q_domain})")
            print(f"    → {retrieved:25s} ({r_domain})")
            print(f"    {count} times\n")


def main():
    """Generate confusion matrix from evaluation report."""
    
    # Load report
    report = load_evaluation_report("retrieved_images")
    if not report:
        return
    
    # Generate confusion matrix (top-1)
    print("\n📊 Generating confusion matrix (Top-1)...")
    confusion, class_names = generate_confusion_matrix(report, top_k=1)
    
    if confusion is None:
        return
    
    # Print analysis
    print_confusion_analysis(confusion, class_names)
    
    # Cross-domain analysis
    analyze_cross_domain_confusion(confusion, class_names)
    
    # Plot
    print("\n📊 Plotting confusion matrix...")
    plot_confusion_matrix(confusion, class_names)
    
    print("\n✅ Confusion matrix analysis complete!")


if __name__ == "__main__":
    main()
