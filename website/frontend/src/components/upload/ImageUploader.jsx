// frontend/src/components/upload/ImageUploader.jsx
import React, { useState, useRef } from 'react';
import PropTypes from 'prop-types';
import { 
  Upload, 
  X, 
  Image as ImageIcon, 
  AlertCircle,
  CheckCircle,
  FileImage
} from 'lucide-react';

const ImageUploader = ({ 
  onFilesSelect, 
  selectedFiles = [], 
  onRemoveFile,
  maxFiles = 10,
  disabled = false 
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [errors, setErrors] = useState([]);
  const fileInputRef = useRef(null);

  const allowedTypes = ['image/jpeg', 'image/png', 'image/jpg'];
  const maxSize = 10 * 1024 * 1024; // 10MB

  const validateFile = (file) => {
    const errors = [];
    
    if (!allowedTypes.includes(file.type)) {
      errors.push(`${file.name}: Only JPEG and PNG images are supported`);
    }
    if (file.size > maxSize) {
      errors.push(`${file.name}: File size must be less than 10MB`);
    }
    
    return errors;
  };

  const handleFiles = (newFiles) => {
    const fileArray = Array.from(newFiles);
    const validationErrors = [];
    const validFiles = [];

    // Check max files limit
    if (selectedFiles.length + fileArray.length > maxFiles) {
      validationErrors.push(`Maximum ${maxFiles} files allowed`);
      setErrors(validationErrors);
      return;
    }

    fileArray.forEach(file => {
      const fileErrors = validateFile(file);
      if (fileErrors.length > 0) {
        validationErrors.push(...fileErrors);
      } else {
        validFiles.push(file);
      }
    });

    setErrors(validationErrors);

    if (validFiles.length > 0) {
      // Create preview URLs
      const filesWithPreviews = validFiles.map(file => ({
        file,
        preview: URL.createObjectURL(file),
        id: Math.random().toString(36).substr(2, 9)
      }));
      
      onFilesSelect([...selectedFiles, ...filesWithPreviews]);
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

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  };

  const handleRemove = (fileId) => {
    const fileToRemove = selectedFiles.find(f => f.id === fileId);
    if (fileToRemove?.preview) {
      URL.revokeObjectURL(fileToRemove.preview);
    }
    onRemoveFile(fileId);
  };

  return (
    <div className="space-y-6">
      {/* Drop Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer ${
          dragActive 
            ? 'border-blue-500 bg-blue-50 scale-[1.02]' 
            : 'border-slate-300 hover:border-blue-400 hover:bg-slate-50'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept="image/jpeg,image/png,image/jpg"
          onChange={handleChange}
          disabled={disabled}
          multiple
        />

        <div className="space-y-4">
          <div className="w-20 h-20 bg-blue-50 rounded-full mx-auto flex items-center justify-center">
            <Upload className="text-blue-600" size={40} />
          </div>
          
          <div>
            <p className="text-lg font-bold text-slate-800 mb-2">
              Drop medical images here
            </p>
            <p className="text-sm text-slate-600 mb-1">
              or click to browse your files
            </p>
            <p className="text-xs text-slate-500">
              JPEG, PNG • Max 10MB per file • Up to {maxFiles} files
            </p>
          </div>

          {selectedFiles.length > 0 && (
            <div className="flex items-center justify-center gap-2 text-sm">
              <CheckCircle className="text-emerald-600" size={18} />
              <span className="font-semibold text-emerald-700">
                {selectedFiles.length} {selectedFiles.length === 1 ? 'file' : 'files'} selected
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Errors */}
      {errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="text-red-600 flex-shrink-0 mt-0.5" size={20} />
            <div className="flex-1">
              <p className="text-sm font-semibold text-red-800 mb-2">Upload Errors:</p>
              <ul className="space-y-1">
                {errors.map((error, index) => (
                  <li key={index} className="text-sm text-red-700">• {error}</li>
                ))}
              </ul>
            </div>
            <button 
              onClick={() => setErrors([])}
              className="text-red-600 hover:text-red-800"
            >
              <X size={18} />
            </button>
          </div>
        </div>
      )}

      {/* Selected Files Preview */}
      {selectedFiles.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-800">
              Selected Images ({selectedFiles.length}/{maxFiles})
            </h3>
            <button
              onClick={() => {
                selectedFiles.forEach(f => f.preview && URL.revokeObjectURL(f.preview));
                onFilesSelect([]);
                setErrors([]);
              }}
              disabled={disabled}
              className="text-sm text-red-600 hover:text-red-700 font-medium disabled:opacity-50"
            >
              Clear All
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {selectedFiles.map((fileObj) => (
              <div 
                key={fileObj.id} 
                className="relative group bg-white rounded-lg border-2 border-slate-200 overflow-hidden hover:border-blue-400 transition-all"
              >
                {/* Image Preview */}
                <div className="aspect-square bg-slate-100 relative">
                  <img 
                    src={fileObj.preview} 
                    alt={fileObj.file.name}
                    className="w-full h-full object-cover"
                  />
                  
                  {/* Remove Button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemove(fileObj.id);
                    }}
                    disabled={disabled}
                    className="absolute top-2 right-2 p-1.5 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600 disabled:opacity-50"
                  >
                    <X size={14} />
                  </button>

                  {/* File Type Badge */}
                  <div className="absolute bottom-2 left-2 px-2 py-1 bg-black/60 rounded text-white text-xs font-mono">
                    {fileObj.file.type.split('/')[1].toUpperCase()}
                  </div>
                </div>

                {/* File Info */}
                <div className="p-3">
                  <div className="flex items-start gap-2">
                    <FileImage className="text-blue-600 flex-shrink-0 mt-0.5" size={16} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-slate-800 truncate" title={fileObj.file.name}>
                        {fileObj.file.name}
                      </p>
                      <p className="text-xs text-slate-500">
                        {(fileObj.file.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload Info */}
      {selectedFiles.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <ImageIcon className="text-blue-600 flex-shrink-0 mt-0.5" size={18} />
            <div className="text-xs text-blue-800">
              <p className="font-semibold mb-1">Before Upload:</p>
              <ul className="list-disc list-inside space-y-0.5 text-blue-700">
                <li>All images will be encrypted using HSM before storage</li>
                <li>Features will be extracted using ConvNeXt V2 model</li>
                <li>256-bit perceptual hashes will be generated</li>
                <li>Images will be indexed for FHE similarity search</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

ImageUploader.propTypes = {
  onFilesSelect: PropTypes.func.isRequired,
  selectedFiles: PropTypes.array,
  onRemoveFile: PropTypes.func.isRequired,
  maxFiles: PropTypes.number,
  disabled: PropTypes.bool,
};

export default ImageUploader;
