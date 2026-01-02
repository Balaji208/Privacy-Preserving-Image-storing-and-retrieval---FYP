"""
Inspect DeepHash model architecture
"""
import torch

checkpoint = torch.load('models/deephash_state_dict_only.pt', map_location='cpu')

state_dict = checkpoint['state_dict']

print("="*70)
print("DeepHash Model Architecture Inspection")
print("="*70)

print(f"\nTotal layers: {len(state_dict)}")
print("\nAll layer names:")
for i, key in enumerate(state_dict.keys()):
    shape = state_dict[key].shape
    print(f"  {i:2d}. {key:40s} {shape}")

print("\n" + "="*70)
