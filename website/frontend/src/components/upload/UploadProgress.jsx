// frontend/src/components/upload/UploadProgress.jsx
import React from 'react';
import PropTypes from 'prop-types';
import { 
  Lock, 
  Cpu, 
  Hash, 
  Database,
  CheckCircle,
  Loader2,
  AlertCircle,
  Upload as UploadIcon
} from 'lucide-react';

const UploadProgress = ({ 
  status, 
  progress, 
  currentFile,
  totalFiles,
  error 
}) => {
  const stages = [
    { 
      id: 'uploading', 
      label: 'Uploading', 
      icon: UploadIcon,
      description: 'Transferring image to server'
    },
    { 
      id: 'encrypting', 
      label: 'Encrypting', 
      icon: Lock,
      description: 'Encrypting with HSM keys'
    },
    { 
      id: 'extracting', 
      label: 'Feature Extraction', 
      icon: Cpu,
      description: 'Processing with ConvNeXt V2'
    },
    { 
      id: 'hashing', 
      label: 'Generating Hash', 
      icon: Hash,
      description: 'Creating 256-bit perceptual hash'
    },
    { 
      id: 'indexing', 
      label: 'Indexing', 
      icon: Database,
      description: 'Adding to FHE search index'
    },
  ];

  const getCurrentStageIndex = () => {
    return stages.findIndex(stage => stage.id === status);
  };

  const currentStageIndex = getCurrentStageIndex();

  if (error) {
    return (
      <div className="bg-white border border-red-200 rounded-xl p-8">
        <div className="flex flex-col items-center text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
            <AlertCircle className="text-red-600" size={32} />
          </div>
          <h3 className="text-lg font-bold text-red-800 mb-2">Upload Failed</h3>
          <p className="text-sm text-red-600 mb-6">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-2.5 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (status === 'complete') {
    return (
      <div className="bg-white border border-emerald-200 rounded-xl p-8">
        <div className="flex flex-col items-center text-center">
          <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mb-4 animate-bounce">
            <CheckCircle className="text-emerald-600" size={32} />
          </div>
          <h3 className="text-lg font-bold text-emerald-800 mb-2">
            Upload Complete!
          </h3>
          <p className="text-sm text-emerald-700 mb-2">
            {totalFiles} {totalFiles === 1 ? 'image' : 'images'} successfully encrypted and indexed
          </p>
          <p className="text-xs text-slate-500 mb-6">
            Your images are now searchable using FHE-powered similarity search
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => window.location.href = '/search'}
              className="px-6 py-2.5 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors"
            >
              Search Similar
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2.5 bg-white text-blue-600 font-semibold rounded-lg border-2 border-blue-600 hover:bg-blue-50 transition-colors"
            >
              Upload More
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-8">
      {/* Header */}
      <div className="text-center mb-8">
        <h3 className="text-lg font-bold text-slate-800 mb-2">
          Processing Upload
        </h3>
        {totalFiles > 1 && (
          <p className="text-sm text-slate-600">
            File {currentFile} of {totalFiles}
          </p>
        )}
      </div>

      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-slate-700">
            Overall Progress
          </span>
          <span className="text-sm font-bold text-blue-600">
            {Math.round(progress)}%
          </span>
        </div>
        <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
          <div 
            className="bg-gradient-to-r from-blue-500 via-teal-500 to-emerald-500 h-full rounded-full transition-all duration-500 relative overflow-hidden"
            style={{ width: `${progress}%` }}
          >
            <div className="absolute inset-0 bg-white/30 animate-pulse"></div>
          </div>
        </div>
      </div>

      {/* Processing Stages */}
      <div className="space-y-4">
        {stages.map((stage, index) => {
          const Icon = stage.icon;
          const isActive = index === currentStageIndex;
          const isComplete = index < currentStageIndex;
          const isPending = index > currentStageIndex;

          return (
            <div
              key={stage.id}
              className={`flex items-start gap-4 p-4 rounded-lg transition-all ${
                isActive 
                  ? 'bg-blue-50 border-2 border-blue-500' 
                  : isComplete
                  ? 'bg-emerald-50 border border-emerald-200'
                  : 'bg-slate-50 border border-slate-200'
              }`}
            >
              {/* Icon */}
              <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                isActive 
                  ? 'bg-blue-500' 
                  : isComplete
                  ? 'bg-emerald-500'
                  : 'bg-slate-300'
              }`}>
                {isActive ? (
                  <Loader2 className="text-white animate-spin" size={20} />
                ) : isComplete ? (
                  <CheckCircle className="text-white" size={20} />
                ) : (
                  <Icon className="text-white" size={20} />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <h4 className={`text-sm font-bold mb-1 ${
                  isActive 
                    ? 'text-blue-900' 
                    : isComplete
                    ? 'text-emerald-900'
                    : 'text-slate-600'
                }`}>
                  {stage.label}
                  {isActive && <span className="ml-2 text-xs">• Processing...</span>}
                  {isComplete && <span className="ml-2 text-xs">• Complete</span>}
                </h4>
                <p className={`text-xs ${
                  isActive 
                    ? 'text-blue-700' 
                    : isComplete
                    ? 'text-emerald-700'
                    : 'text-slate-500'
                }`}>
                  {stage.description}
                </p>
              </div>

              {/* Progress Indicator */}
              {isActive && (
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-ping"></div>
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-ping animation-delay-200"></div>
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-ping animation-delay-400"></div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Info Message */}
      <div className="mt-6 bg-purple-50 border border-purple-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Lock className="text-purple-600 flex-shrink-0 mt-0.5" size={16} />
          <p className="text-xs text-purple-800">
            <span className="font-semibold">FHE Processing:</span> Your images are being 
            encrypted and processed to enable privacy-preserving similarity search. 
            This may take 30-60 seconds per image.
          </p>
        </div>
      </div>
    </div>
  );
};

UploadProgress.propTypes = {
  status: PropTypes.oneOf([
    'uploading',
    'encrypting',
    'extracting',
    'hashing',
    'indexing',
    'complete'
  ]).isRequired,
  progress: PropTypes.number.isRequired,
  currentFile: PropTypes.number,
  totalFiles: PropTypes.number,
  error: PropTypes.string,
};

export default UploadProgress;
