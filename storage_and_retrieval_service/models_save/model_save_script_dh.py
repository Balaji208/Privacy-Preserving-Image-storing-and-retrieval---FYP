"""
Fix DeepHash model by extracting weights only
"""
import torch
import torch.nn as nn

print("="*70)
print("DeepHash Model Fixer")
print("="*70)

# Step 1: Define the original DeepHash architecture
class DeepHashingHead(nn.Module):
    """
    DeepHashing architecture for generating binary hash codes
    """
    def __init__(
        self,
        input_dim: int = 512,
        hash_dim: int = 256,
        hidden_dims: list = None
    ):
        super().__init__()
        
        self.input_dim = input_dim
        self.hash_dim = hash_dim
        
        if hidden_dims is None:
            hidden_dims = [512, 512]
        
        # Build network layers
        layers = []
        prev_dim = input_dim
        
        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(inplace=True),
                nn.Dropout(0.3)
            ])
            prev_dim = hidden_dim
        
        # Hash layer (no activation - raw logits)
        layers.append(nn.Linear(prev_dim, hash_dim))
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        """Forward pass through network"""
        return self.network(x)
    
    def generate_hash(self, x):
        """Generate binary hash codes"""
        with torch.no_grad():
            logits = self.forward(x)
            hash_codes = torch.sign(logits)
            hash_codes = (hash_codes + 1) / 2  # Convert from {-1, 1} to {0, 1}
            return hash_codes.int()


# Step 2: Load the original model
input_model = 'models/deephash_production.pt'
output_model = 'models/deephash_state_dict_only.pt'

print(f"\nLoading: {input_model}")

try:
    checkpoint = torch.load(input_model, map_location='cpu', weights_only=False)
    
    print("✓ Loaded!")
    print(f"Type: {type(checkpoint)}")
    
    if isinstance(checkpoint, dict):
        print(f"Keys: {list(checkpoint.keys())}")
        
        # Extract model and state dict
        # ✅ Handle different key names
        if 'hash_model' in checkpoint:
            model = checkpoint['hash_model']
            state_dict = checkpoint.get('hash_model_state_dict', model.state_dict())
            print(f"✓ Found hash_model")
        elif 'model' in checkpoint:
            model = checkpoint['model']
            state_dict = checkpoint.get('model_state_dict', model.state_dict())
            print(f"✓ Found model")
        elif 'hash_model_state_dict' in checkpoint:
            state_dict = checkpoint['hash_model_state_dict']
            print(f"✓ Found hash_model_state_dict")
        elif 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
            print(f"✓ Found model_state_dict")
        else:
            raise ValueError(f"Cannot find model or state_dict. Available keys: {list(checkpoint.keys())}")
        
        # Get configuration
        config = checkpoint.get('config', {})
        metrics = checkpoint.get('metrics', {})
        
        # Get dimensions from checkpoint if not in config
        input_dim = config.get('input_dim', checkpoint.get('input_dim', 512))
        hash_dim = config.get('hash_dim', checkpoint.get('hash_bits', 256))
        hidden_dims = config.get('hidden_dims', [512, 512])
        
        # Update config with extracted values
        config = {
            'input_dim': input_dim,
            'hash_dim': hash_dim,
            'hidden_dims': hidden_dims
        }
        
        print(f"\nModel configuration:")
        print(f"  Input dim: {input_dim}")
        print(f"  Hash dim: {hash_dim}")
        print(f"  Hidden dims: {hidden_dims}")
        
        print(f"\nMetrics:")
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                print(f"  {key}: {value}")
        
        print(f"\nState dict info:")
        print(f"  Number of layers: {len(state_dict)}")
        print(f"  First few keys: {list(state_dict.keys())[:3]}")
        
        # Step 3: Save ONLY state dict (no class definition)
        clean_save = {
            'state_dict': state_dict,
            'config': config,
            'metrics': metrics,
            'training_history': checkpoint.get('training_history', {}),
            'feature_extractor_path': checkpoint.get('feature_extractor_path', ''),
            'model_type': 'DeepHashing'
        }
        
        torch.save(clean_save, output_model)
        print(f"\n✓ Saved to: {output_model}")
        
        # Verify
        test = torch.load(output_model, map_location='cpu', weights_only=False)
        print(f"✓ Verified! Keys: {list(test.keys())}")
        print(f"  State dict layers: {len(test['state_dict'])}")
        
        print("\n" + "="*70)
        print("✅ SUCCESS!")
        print(f"Use this model: {output_model}")
        print("="*70)
        
    else:
        print("Checkpoint is not a dictionary, trying to extract state_dict...")
        state_dict = checkpoint.state_dict()
        
        clean_save = {
            'state_dict': state_dict,
            'config': {
                'input_dim': 512,
                'hash_dim': 256,
                'hidden_dims': [512, 512]
            },
            'metrics': {},
            'model_type': 'DeepHashing'
        }
        
        torch.save(clean_save, output_model)
        print(f"✓ Saved to: {output_model}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
