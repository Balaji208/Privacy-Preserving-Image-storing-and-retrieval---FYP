// frontend/src/components/history/UploadHistoryList.jsx
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { 
  Upload, 
  Calendar, 
  Search,
  Eye,
  Filter,
  ChevronDown,
  Image as ImageIcon,
  FileCheck,
  Lock
} from 'lucide-react';
import Button from '../common/Button';

const UploadHistoryList = ({ 
  uploads = [], 
  loading = false,
  onViewImage,
  onSearchSimilar 
}) => {
  const [sortBy, setSortBy] = useState('date'); // date, name
  const [filterStudyType, setFilterStudyType] = useState('all');
  const [showFilters, setShowFilters] = useState(false);

  const formatDate = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Sort uploads
  const sortedUploads = [...uploads].sort((a, b) => {
    switch (sortBy) {
      case 'date':
        return new Date(b.upload_date) - new Date(a.upload_date);
      case 'name':
        return a.patient_id?.localeCompare(b.patient_id || '') || 0;
      default:
        return 0;
    }
  });

  // Filter by study type
  const filteredUploads = filterStudyType === 'all' 
    ? sortedUploads 
    : sortedUploads.filter(u => u.study_type === filterStudyType);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-slate-200 overflow-hidden animate-pulse">
            <div className="h-48 bg-slate-200"></div>
            <div className="p-4">
              <div className="h-4 bg-slate-200 rounded w-3/4 mb-2"></div>
              <div className="h-3 bg-slate-200 rounded w-1/2"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (uploads.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
        <Upload className="mx-auto text-slate-300 mb-4" size={64} />
        <h3 className="text-lg font-bold text-slate-800 mb-2">No Upload History</h3>
        <p className="text-slate-500 text-sm mb-6">
          Your uploaded images will appear here once you add them to the system
        </p>
        <Button onClick={() => window.location.href = '/upload'} icon={Upload}>
          Upload First Image
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2 text-sm font-semibold text-slate-700 hover:text-blue-600 transition-colors"
          >
            <Filter size={18} />
            Filters
            <ChevronDown 
              size={16} 
              className={`transition-transform ${showFilters ? 'rotate-180' : ''}`}
            />
          </button>

          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-slate-600">Sort by:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="date">Most Recent</option>
              <option value="name">Patient ID</option>
            </select>
          </div>

          <div className="ml-auto text-sm text-slate-500 font-medium">
            {filteredUploads.length} {filteredUploads.length === 1 ? 'image' : 'images'}
          </div>
        </div>

        {showFilters && (
          <div className="mt-4 pt-4 border-t border-slate-200">
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Study Type
            </label>
            <div className="flex flex-wrap gap-2">
              {['all', 'brain_mri', 'chest_xray', 'lung_ct', 'abdominal_ct'].map((type) => (
                <button
                  key={type}
                  onClick={() => setFilterStudyType(type)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    filterStudyType === type
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {type === 'all' ? 'All Types' : type.replace('_', ' ').toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Upload History Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredUploads.map((upload) => (
          <div 
            key={upload.image_id} 
            className="bg-white rounded-xl border border-slate-200 overflow-hidden hover:shadow-lg transition-all duration-200"
          >
            {/* Image Thumbnail */}
            <div className="relative h-48 bg-slate-100 group">
              {upload.thumbnail_url ? (
                <img 
                  src={upload.thumbnail_url} 
                  alt={upload.patient_id} 
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <ImageIcon className="text-slate-400" size={48} />
                </div>
              )}
              
              {/* Encryption Badge */}
              <div className="absolute top-2 right-2 bg-emerald-500 text-white text-xs font-bold px-2 py-1 rounded-full flex items-center gap-1 shadow-lg">
                <Lock size={12} />
                Encrypted
              </div>

              {/* Study Type Badge */}
              {upload.study_type && (
                <div className="absolute top-2 left-2 bg-blue-600 text-white text-xs font-bold px-2 py-1 rounded shadow-lg">
                  {upload.study_type.replace('_', ' ').toUpperCase()}
                </div>
              )}

              {/* Hover Overlay */}
              <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                <Button 
                  onClick={() => onViewImage(upload)}
                  variant="ghost"
                  size="sm"
                  className="bg-white/90 hover:bg-white text-slate-800"
                  icon={Eye}
                >
                  View
                </Button>
              </div>
            </div>

            {/* Upload Details */}
            <div className="p-4">
              <h3 className="text-sm font-bold text-slate-800 mb-2 truncate">
                {upload.patient_id || 'Unknown Patient'}
              </h3>
              
              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500">Image ID:</span>
                  <span className="font-mono text-slate-700">{upload.image_id.slice(-8)}</span>
                </div>
                
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500">Upload Date:</span>
                  <span className="text-slate-700">{formatDate(upload.upload_date)}</span>
                </div>

                {upload.file_size && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">File Size:</span>
                    <span className="text-slate-700">{formatFileSize(upload.file_size)}</span>
                  </div>
                )}

                {upload.diagnosis && (
                  <div className="text-xs mt-3 p-2 bg-amber-50 border border-amber-200 rounded">
                    <span className="font-semibold text-amber-800">Diagnosis:</span>{' '}
                    <span className="text-amber-700">{upload.diagnosis}</span>
                  </div>
                )}
              </div>

              {/* Metadata Tags */}
              {upload.metadata && (
                <div className="flex flex-wrap gap-1 mb-4">
                  {upload.metadata.age && (
                    <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                      Age: {upload.metadata.age}
                    </span>
                  )}
                  {upload.metadata.severity && (
                    <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                      {upload.metadata.severity}
                    </span>
                  )}
                </div>
              )}

              {/* Status Indicator */}
              <div className="flex items-center gap-2 mb-4 text-xs">
                <FileCheck className="text-emerald-600" size={14} />
                <span className="text-emerald-600 font-semibold">Indexed & Encrypted</span>
              </div>

              {/* Actions */}
              <Button 
                onClick={() => onSearchSimilar(upload)}
                variant="primary"
                size="sm"
                icon={Search}
                className="w-full"
              >
                Find Similar Cases
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

UploadHistoryList.propTypes = {
  uploads: PropTypes.arrayOf(
    PropTypes.shape({
      image_id: PropTypes.string.isRequired,
      patient_id: PropTypes.string,
      upload_date: PropTypes.string.isRequired,
      study_type: PropTypes.string,
      thumbnail_url: PropTypes.string,
      file_size: PropTypes.number,
      diagnosis: PropTypes.string,
      metadata: PropTypes.object,
    })
  ),
  loading: PropTypes.bool,
  onViewImage: PropTypes.func.isRequired,
  onSearchSimilar: PropTypes.func.isRequired,
};

export default UploadHistoryList;
