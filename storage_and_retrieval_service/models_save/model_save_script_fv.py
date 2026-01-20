"""
Extract ONLY weights (no class definition) from model
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import timm

print("="*70)
print("Extract Weights Only - Final Fix")
print("="*70)

# Step 1: Define the class (needed to load)
class ConvNeXtV2FeatureExtractor(nn.Module):
    def __init__(self, model_size='tiny', num_classes=9, feature_dim=512, pretrained=False):
        super().__init__()
        self.model_size = model_size
        self.num_classes = num_classes
        self.feature_dim = feature_dim
        
        model_name = f'convnextv2_{model_size}.fcmae_ft_in22k_in1k'
        self.backbone = timm.create_model(model_name, pretrained=pretrained, num_classes=0)
        
        with torch.no_grad():
            dummy_input = torch.randn(1, 3, 224, 224)
            backbone_dim = self.backbone(dummy_input).shape[1]
        
        self.projection = nn.Sequential(
            nn.Linear(backbone_dim, feature_dim),
            nn.LayerNorm(feature_dim),
            nn.GELU()
        )
        
        self.classifier = nn.Linear(feature_dim, num_classes)
    
    def forward(self, x, return_features=False):
        x = self.backbone(x)
        features = self.projection(x)
        features = F.normalize(features, p=2, dim=1)
        if return_features:
            return features
        logits = self.classifier(features)
        return logits

# Step 2: Load the model
input_model = 'models/convnextv2_multi_512d.pt'
output_model = 'models/convnext_state_dict_only.pt'

print(f"\nLoading: {input_model}")
checkpoint = torch.load(input_model, map_location='cpu', weights_only=False)

print("✓ Loaded!")
print(f"Keys: {list(checkpoint.keys())}")

# Step 3: Extract model and state dict
model = checkpoint['model']
state_dict = checkpoint['model_state_dict']

print(f"✓ Model type: {type(model)}")
print(f"✓ State dict has {len(state_dict)} layers")
print(f"✓ Val accuracy: {checkpoint['best_val_acc']:.4f}")

# Step 4: Save ONLY the state dict (NO class definition)
clean_save = {
    'state_dict': state_dict,  # ONLY weights
    'epoch': checkpoint.get('epoch', 0),
    'best_val_acc': checkpoint['best_val_acc'],
    'config': {
        'model_size': 'tiny',
        'num_classes': checkpoint.get('num_classes', 9),
        'feature_dim': checkpoint.get('feature_dim', 512)
    },
    'class_mapping': checkpoint.get('class_mapping', {}),
    'id_to_class': checkpoint.get('id_to_class', {})
}

# Save without the model object
torch.save(clean_save, output_model)
print(f"\n✓ Saved state dict to: {output_model}")

# Step 5: Verify it loads without the class
print("\nVerifying...")
test = torch.load(output_model, map_location='cpu', weights_only=False)
print(f"✓ Loads without class definition!")
print(f"  Keys: {list(test.keys())}")
print(f"  State dict layers: {len(test['state_dict'])}")

print("\n" + "="*70)
print("✅ SUCCESS!")
print(f"Use this model: {output_model}")
print("="*70)
