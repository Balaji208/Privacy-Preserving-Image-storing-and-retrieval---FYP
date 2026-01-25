// frontend/src/components/search/QueryPanel.jsx
import React, { useState, useRef } from 'react';
import PropTypes from 'prop-types';
import { Upload, X, Image as ImageIcon, AlertCircle } from 'lucide-react';
import Button from '../common/Button';

const QueryPanel = ({ onFileSelect, selectedFile, onClearFile, loading }) => {
  const [dragActive, setDragActive] = useState(false);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const allowedTypes = ['image/jpeg', 'image/png', 'image/jpg'];
  const maxSize = 10 * 1024 * 1024; // 10MB

  const validateFile = (file) => {
    if (!allowedTypes.includes(file.type)) {
      setError('Only JPEG and PNG images are supported');
      return false;
    }
    if (file.size > maxSize) {
      setError('File size must be less than 10MB');
      return false;
    }
    setError(null);
    return true;
  };

  const handleFile = (file) => {
    if (validateFile(file)) {
      onFileSelect(file);
      
      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleClear = () => {
    setPreview(null);
    setError(null);
    onClearFile();
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-bold text-slate-800 mb-2">Query Image</h3>
        <p className="text-xs text-slate-500">Upload a medical image to find similar cases</p>
      </div>

      {/* File Upload Area */}
      {!preview ? (
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
            dragActive 
              ? 'border-blue-500 bg-blue-50' 
              : 'border-slate-300 hover:border-blue-400 hover:bg-slate-50'
          }`}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept="image/jpeg,image/png,image/jpg"
            onChange={handleChange}
            disabled={loading}
          />

          <div className="space-y-3">
            <div className="w-16 h-16 bg-blue-50 rounded-full mx-auto flex items-center justify-center">
              <Upload className="text-blue-600" size={32} />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800 mb-1">
                Drop your image here or click to browse
              </p>
              <p className="text-xs text-slate-500">
                JPEG, PNG • Max 10MB
              </p>
            </div>
          </div>
        </div>
      ) : (
        /* Image Preview */
        <div className="relative border-2 border-slate-200 rounded-xl overflow-hidden bg-slate-50">
          <img 
            src={preview} 
            alt="Query preview" 
            className="w-full h-64 object-contain"
          />
          <button
            onClick={handleClear}
            disabled={loading}
            className="absolute top-2 right-2 p-2 bg-white/90 hover:bg-white rounded-lg shadow-lg transition-colors disabled:opacity-50"
          >
            <X size={18} className="text-slate-600" />
          </button>
          
          {selectedFile && (
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-4">
              <p className="text-white text-sm font-medium truncate">
                {selectedFile.name}
              </p>
              <p className="text-white/80 text-xs">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </p>
            </div>
          )}
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="text-red-600 flex-shrink-0 mt-0.5" size={16} />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* File Info */}
      {selectedFile && !error && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="flex items-center gap-2 text-sm">
            <ImageIcon className="text-blue-600" size={16} />
            <span className="font-medium text-blue-900">
              Ready for FHE search
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

QueryPanel.propTypes = {
  onFileSelect: PropTypes.func.isRequired,
  selectedFile: PropTypes.object,
  onClearFile: PropTypes.func.isRequired,
  loading: PropTypes.bool,
};

export default QueryPanel;
