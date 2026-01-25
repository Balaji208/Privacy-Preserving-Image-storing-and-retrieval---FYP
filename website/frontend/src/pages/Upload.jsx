// frontend/src/pages/Upload.jsx
import React, { useState } from 'react';
import { useUpload } from '../hooks/useUpload';
import { useSettings } from '../context/SettingsContext';
import ImageUploader from '../components/upload/ImageUploader';
import MetadataForm from '../components/upload/MetadataForm';
import UploadProgress from '../components/upload/UploadProgress';
import Button from '../components/common/Button';
import { Upload as UploadIcon, ArrowLeft } from 'lucide-react';

const Upload = () => {
  const { uploadSingle, uploadBatch, uploading, progress, status, error, uploadedImages, currentFile, totalFiles, reset } = useUpload();
  const { getUploadDefaults } = useSettings();
  
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [metadata, setMetadata] = useState({
    patient_id: '',
    age: '',
    study_type: '',
    diagnosis: '',
    severity: '',
    notes: '',
    ...getUploadDefaults(),
  });
  const [uploadMode, setUploadMode] = useState('single'); // 'single' | 'batch'
  const [currentStep, setCurrentStep] = useState('select'); // 'select' | 'metadata' | 'uploading' | 'complete'

  const handleFilesSelect = (files) => {
    setSelectedFiles(files);
    if (files.length > 1) {
      setUploadMode('batch');
    }
  };

  const handleRemoveFile = (fileId) => {
    setSelectedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const handleNext = () => {
    if (currentStep === 'select' && selectedFiles.length > 0) {
      setCurrentStep('metadata');
    }
  };

  const handleBack = () => {
    if (currentStep === 'metadata') {
      setCurrentStep('select');
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;

    setCurrentStep('uploading');

    if (uploadMode === 'single') {
      const result = await uploadSingle(selectedFiles[0].file, metadata);
      if (result.success) {
        setCurrentStep('complete');
      }
    } else {
      const filesWithMetadata = selectedFiles.map(f => ({
        file: f.file,
        metadata: metadata, // In batch mode, same metadata for all
      }));
      const result = await uploadBatch(filesWithMetadata);
      if (result.success || result.totalUploaded > 0) {
        setCurrentStep('complete');
      }
    }
  };

  const handleReset = () => {
    reset();
    setSelectedFiles([]);
    setMetadata({
      patient_id: '',
      age: '',
      study_type: '',
      diagnosis: '',
      severity: '',
      notes: '',
      ...getUploadDefaults(),
    });
    setCurrentStep('select');
    setUploadMode('single');
  };

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-800 mb-2">
            Upload Medical Images
          </h1>
          <p className="text-slate-600">
            Securely upload and encrypt medical images for privacy-preserving search
          </p>
        </div>

        {/* Progress Steps */}
        {currentStep !== 'complete' && (
          <div className="mb-8">
            <div className="flex items-center justify-center gap-4">
              {['select', 'metadata', 'uploading'].map((step, index) => (
                <React.Fragment key={step}>
                  <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                      currentStep === step
                        ? 'bg-blue-600 text-white'
                        : index < ['select', 'metadata', 'uploading'].indexOf(currentStep)
                        ? 'bg-emerald-500 text-white'
                        : 'bg-slate-200 text-slate-500'
                    }`}>
                      {index + 1}
                    </div>
                    <span className={`text-sm font-medium ${
                      currentStep === step ? 'text-blue-600' : 'text-slate-600'
                    }`}>
                      {step === 'select' ? 'Select Images' : step === 'metadata' ? 'Add Metadata' : 'Upload'}
                    </span>
                  </div>
                  {index < 2 && (
                    <div className={`w-12 h-0.5 ${
                      index < ['select', 'metadata', 'uploading'].indexOf(currentStep)
                        ? 'bg-emerald-500'
                        : 'bg-slate-200'
                    }`}></div>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        )}

        {/* Content */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
          {currentStep === 'select' && (
            <div className="p-8">
              <ImageUploader
                onFilesSelect={handleFilesSelect}
                selectedFiles={selectedFiles}
                onRemoveFile={handleRemoveFile}
                disabled={uploading}
              />
              
              {selectedFiles.length > 0 && (
                <div className="mt-6 flex justify-end">
                  <Button
                    onClick={handleNext}
                    icon={UploadIcon}
                    variant="primary"
                    size="lg"
                  >
                    Continue to Metadata
                  </Button>
                </div>
              )}
            </div>
          )}

          {currentStep === 'metadata' && (
            <div className="p-8">
              <MetadataForm
                metadata={metadata}
                onChange={setMetadata}
                disabled={uploading}
              />
              
              <div className="mt-8 flex justify-between">
                <Button
                  onClick={handleBack}
                  icon={ArrowLeft}
                  variant="ghost"
                >
                  Back to Images
                </Button>
                <Button
                  onClick={handleUpload}
                  icon={UploadIcon}
                  variant="primary"
                  size="lg"
                  disabled={!metadata.study_type}
                >
                  Upload {selectedFiles.length} {selectedFiles.length === 1 ? 'Image' : 'Images'}
                </Button>
              </div>
            </div>
          )}

          {currentStep === 'uploading' && (
            <div className="p-8">
              <UploadProgress
                status={status}
                progress={progress}
                currentFile={currentFile}
                totalFiles={totalFiles}
                error={error}
              />
            </div>
          )}

          {currentStep === 'complete' && (
            <div className="p-8">
              <UploadProgress
                status="complete"
                progress={100}
                currentFile={totalFiles}
                totalFiles={totalFiles}
              />
              
              <div className="mt-6 flex justify-center gap-4">
                <Button
                  onClick={() => window.location.href = '/search'}
                  variant="primary"
                >
                  Search Similar Images
                </Button>
                <Button
                  onClick={handleReset}
                  variant="secondary"
                >
                  Upload More Images
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Upload Summary */}
        {uploadedImages.length > 0 && currentStep === 'complete' && (
          <div className="mt-6 bg-emerald-50 border border-emerald-200 rounded-xl p-6">
            <h3 className="text-lg font-bold text-emerald-900 mb-3">Upload Summary</h3>
            <div className="space-y-2">
              {uploadedImages.map((img) => (
                <div key={img.image_id} className="flex items-center justify-between text-sm">
                  <span className="text-emerald-800">{img.filename}</span>
                  <span className="font-mono text-xs text-emerald-600">{img.image_id.slice(-8)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Upload;
