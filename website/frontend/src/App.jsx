import React, { useState } from 'react';
import { searchSimilarImages } from "./services/api";  // ✅ Correct path

import './styles/global.css';

function App() {
  const [selectedImage, setSelectedImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [kValue, setKValue] = useState(5);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [queryInfo, setQueryInfo] = useState(null);

  const handleImageUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedImage(file);
      setError(null);
      
      // Create preview URL
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewUrl(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSearch = async () => {
    if (!selectedImage) {
      setError('Please upload an image first');
      return;
    }

    if (kValue < 1 || kValue > 20) {
      setError('k value must be between 1 and 20');
      return;
    }

    setLoading(true);
    setError(null);
    setResults([]);
    setQueryInfo(null);

    try {
      console.log(`Searching with k=${kValue}...`);
      const response = await searchSimilarImages(selectedImage, kValue);
      
      if (response.status === 'success') {
        setResults(response.results);
        setQueryInfo(response.query_info);
        console.log(`Found ${response.count} similar images`);
      } else {
        setError(response.error || 'Search failed');
      }
    } catch (err) {
      console.error('Search error:', err);
      setError(err.message || 'Failed to search for similar images');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSelectedImage(null);
    setPreviewUrl(null);
    setResults([]);
    setError(null);
    setQueryInfo(null);
    setKValue(5);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>🔒 Encrypted Image Search</h1>
        <p>Privacy-preserving similarity search using homomorphic encryption</p>
      </header>

      <main className="main-content">
        {/* Upload Section */}
        <section className="upload-section">
          <h2>Upload Query Image</h2>
          
          <div className="upload-controls">
            <input 
              type="file" 
              accept="image/*" 
              onChange={handleImageUpload}
              className="file-input"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="file-label">
              Choose Image
            </label>

            {previewUrl && (
              <button onClick={handleReset} className="btn-secondary">
                Clear
              </button>
            )}
          </div>

          {previewUrl && (
            <div className="image-preview">
              <img src={previewUrl} alt="Query preview" />
              <p className="image-name">{selectedImage?.name}</p>
            </div>
          )}
        </section>

        {/* K Value Input */}
        <section className="k-input-section">
          <label htmlFor="k-value">
            <span className="label-text">Number of similar images (k):</span>
            <input 
              type="number" 
              id="k-value"
              min="1" 
              max="20" 
              value={kValue}
              onChange={(e) => setKValue(parseInt(e.target.value) || 1)}
              disabled={loading}
              className="k-input"
            />
          </label>
          <p className="helper-text">Enter a value between 1 and 20</p>
        </section>

        {/* Search Button */}
        <div className="search-button-container">
          <button 
            onClick={handleSearch} 
            disabled={loading || !selectedImage}
            className={`btn-primary ${loading ? 'loading' : ''}`}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Searching...
              </>
            ) : (
              'Search Similar Images'
            )}
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            {error}
          </div>
        )}

        {/* Query Info */}
        {queryInfo && (
          <div className="query-info">
            <h3>Search Statistics</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Processing Time:</span>
                <span className="info-value">{queryInfo.processing_time_ms?.toFixed(0)}ms</span>
              </div>
              <div className="info-item">
                <span className="info-label">Candidates Evaluated:</span>
                <span className="info-value">{queryInfo.num_candidates}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Results Returned:</span>
                <span className="info-value">{results.length}</span>
              </div>
            </div>
          </div>
        )}

        {/* Results Display */}
        {results.length > 0 && (
          <section className="results-section">
            <h2>Similar Images Found: {results.length}</h2>
            
            <div className="results-grid">
              {results.map((result, index) => (
                <div key={index} className="result-card">
                  <div className="rank-badge">#{result.rank}</div>
                  <img 
                    src={result.image_data} 
                    alt={result.image_id}
                    className="result-image"
                  />
                  <div className="result-info">
                    <div className="info-row">
                      <span className="info-label">Class:</span>
                      <span className="class-badge">{result.class_name}</span>
                    </div>
                    <div className="info-row">
                      <span className="info-label">ID:</span>
                      <span className="info-value">{result.image_id}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>

      <footer className="app-footer">
        <p>Powered by BFV Homomorphic Encryption • ConvNeXt-V2 • DeepHash v4.0</p>
      </footer>
    </div>
  );
}

export default App;
