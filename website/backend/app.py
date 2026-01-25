"""
Flask Backend API for Encrypted Image Similarity Search
Simplified version with auto-detected model paths
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
import tempfile
import os
import base64
import sys
import traceback
import logging
import torch


# Add storage_and_retrieval_service to path
STORAGE_SERVICE_DIR = Path(__file__).parent.parent.parent / "storage_and_retrieval_service"
sys.path.insert(0, str(STORAGE_SERVICE_DIR))


# Change working directory so relative paths work
os.chdir(str(STORAGE_SERVICE_DIR))


from search_similar_images import SimilaritySearchAPI


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})


# ✅ FIX: Auto-detect device and force CPU if CUDA not available
if torch.cuda.is_available():
    DEVICE = 'cuda'
    logger.info("🎮 CUDA available - using GPU")
else:
    DEVICE = 'cpu'
    logger.warning("⚠️  CUDA not available - using CPU (this will be slower)")


SIMILARITY_SERVICE_URL = os.getenv('SIMILARITY_SERVICE_URL', 'http://localhost:8000/api/v1/search')


# Global API instance
search_api = None



def initialize_search_api():
    """Initialize the search API on startup"""
    global search_api
    
    logger.info("=" * 80)
    logger.info("INITIALIZING SEARCH API")
    logger.info("=" * 80)
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Device: {DEVICE.upper()}")
    
    try:
        search_api = SimilaritySearchAPI(
            similarity_service_url=SIMILARITY_SERVICE_URL,
            output_dir="temp_search_results",
            device=DEVICE
        )
        logger.info("✅ Search API Initialized")
        logger.info("=" * 80)
    except Exception as e:
        logger.error(f"❌ Failed to initialize search API: {e}")
        traceback.print_exc()
        raise



@app.route('/api/search', methods=['POST'])
def search_endpoint():
    """Main endpoint for image similarity search"""
    temp_file_path = None
    
    try:
        logger.info("\n" + "=" * 80)
        logger.info("NEW SEARCH REQUEST")
        logger.info("=" * 80)
        
        # Validate image file
        if 'image' not in request.files:
            return jsonify({'status': 'error', 'error': 'No image file provided'}), 400
        
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'status': 'error', 'error': 'Empty filename'}), 400
        
        # Get k parameter
        try:
            k = int(request.form.get('k', 5))
            if k < 1 or k > 20:
                return jsonify({'status': 'error', 'error': 'k must be between 1 and 20'}), 400
        except ValueError:
            return jsonify({'status': 'error', 'error': 'Invalid k value'}), 400
        
        logger.info(f"Parameters: k={k}, image={image_file.filename}")
        logger.info("")
        
        # Save uploaded image temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg', mode='wb') as tmp_file:
            image_file.save(tmp_file.name)
            temp_file_path = tmp_file.name
        
        # Use the simplified search API
        logger.info("🔍 Starting search...")
        search_result = search_api.search(
            query_image_path=temp_file_path,
            top_k=k,
            save_images=True
        )
        
        if not search_result['success']:
            error_msg = search_result.get('error', 'Search failed')
            logger.error(f"❌ Search failed: {error_msg}")
            return jsonify({'status': 'error', 'error': error_msg}), 500
        
        # ✅ FIX: Convert images to base64 and extract class names from filenames
        formatted_results = []
        
        results_list = search_result.get('results', [])
        logger.info(f"   Retrieved {len(results_list)} results from search")
        
        for result in results_list:
            image_path = result.get('image_path')
            
            if image_path and os.path.exists(image_path):
                try:
                    # Read image and convert to base64
                    with open(image_path, 'rb') as img_file:
                        img_bytes = img_file.read()
                    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                    
                    # ✅ FIX: Extract class name from saved filename
                    # Filename format: PNEUMONIA_1173_1769176654194.jpg
                    filename = Path(image_path).stem  # Remove .jpg extension
                    
                    # Split by underscore and take first part (class name)
                    parts = filename.split('_')
                    class_name = parts[0] if parts else 'UNKNOWN'
                    
                    # Get original image_id (the hash)
                    image_id = result.get('image_id', 'unknown')
                    
                    formatted_results.append({
                        'rank': result['rank'],
                        'image_data': f"data:image/jpeg;base64,{img_base64}",
                        'class_name': class_name,  # ✅ Now extracted from filename
                        'image_id': image_id,
                        'image_name': Path(image_path).name,
                        'similarity': result.get('similarity', 0.0),
                        'hamming_distance': result.get('hamming_distance', 0),
                        'metadata': result.get('metadata', {})
                    })
                    
                    logger.info(f"   ✓ Rank {result['rank']}: {image_id} (similarity: {result.get('similarity', 0):.2%})")
                    
                except Exception as e:
                    logger.warning(f"   ⚠️  Failed to load image {image_path}: {e}")
            else:
                logger.warning(f"   ⚠️  Image path not found: {image_path}")
        
        logger.info(f"\n✅ Formatted {len(formatted_results)} results")
        logger.info("=" * 80)
        
        # Return properly formatted response
        return jsonify({
            'status': 'success',
            'count': len(formatted_results),
            'query_info': {
                'k_requested': k,
                'session_id': search_result.get('session_id'),
                'processing_time_ms': search_result.get('timings', {}).get('total_ms', 0),
                'query_prep_ms': search_result.get('timings', {}).get('query_prep_ms', 0),
                'search_ms': search_result.get('timings', {}).get('search_ms', 0),
                'decryption_ms': search_result.get('timings', {}).get('decryption_ms', 0),
                'device': DEVICE
            },
            'results': formatted_results
        })
        
    except Exception as e:
        logger.error(f"\n❌ Search endpoint error: {e}")
        traceback.print_exc()
        return jsonify({
            'status': 'error', 
            'error': 'Internal server error', 'details': str(e)
        }), 500
        
    finally:
        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.debug(f"   🗑️  Cleaned up temp file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"   ⚠️  Failed to cleanup temp file: {e}")



@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    import requests
    
    try:
        response = requests.get(SIMILARITY_SERVICE_URL.replace('/search', '/health'), timeout=5)
        similarity_ok = response.status_code == 200
    except:
        similarity_ok = False
    
    return jsonify({
        'status': 'healthy' if (search_api and similarity_ok) else 'degraded',
        'search_api': 'loaded' if search_api else 'not_loaded',
        'similarity_service': 'ok' if similarity_ok else 'error',
        'device': DEVICE,
        'cuda_available': torch.cuda.is_available()
    })



@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return jsonify({
        'service': 'Encrypted Image Search Backend',
        'version': '1.0.0',
        'device': DEVICE,
        'cuda_available': torch.cuda.is_available(),
        'endpoints': {
            'search': '/api/search (POST)',
            'health': '/api/health (GET)'
        }
    })



# Initialize on startup
with app.app_context():
    initialize_search_api()



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
