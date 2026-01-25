// frontend/src/components/search/ResultDetailModal.jsx
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import Modal from '../common/Modal';
import { 
  Download, 
  Flag, 
  FileText,
  ZoomIn,
  ZoomOut,
  User,
  Calendar,
  Activity,
  Pill,
  AlertCircle
} from 'lucide-react';
import Button from '../common/Button';

const ResultDetailModal = ({ isOpen, onClose, result, queryImage }) => {
  const [zoom, setZoom] = useState(1);
  const [activeTab, setActiveTab] = useState('comparison'); // 'comparison' or 'metadata'

  if (!result) return null;

  const handleZoomIn = () => setZoom(Math.min(zoom + 0.25, 3));
  const handleZoomOut = () => setZoom(Math.max(zoom - 0.25, 0.5));

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Case Details - Rank #${result.rank}`}
      size="xl"
    >
      <div className="space-y-6">
        {/* Tabs */}
        <div className="flex gap-2 border-b border-slate-200">
          <button
            onClick={() => setActiveTab('comparison')}
            className={`px-4 py-2 font-semibold text-sm transition-colors ${
              activeTab === 'comparison'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-slate-600 hover:text-slate-800'
            }`}
          >
            Image Comparison
          </button>
          <button
            onClick={() => setActiveTab('metadata')}
            className={`px-4 py-2 font-semibold text-sm transition-colors ${
              activeTab === 'metadata'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-slate-600 hover:text-slate-800'
            }`}
          >
            Patient Metadata
          </button>
        </div>

        {activeTab === 'comparison' && (
          <div className="space-y-4">
            {/* Zoom Controls */}
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-800">Visual Comparison</h3>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-600 font-medium">Zoom: {Math.round(zoom * 100)}%</span>
                <Button size="sm" variant="ghost" onClick={handleZoomOut} icon={ZoomOut} />
                <Button size="sm" variant="ghost" onClick={handleZoomIn} icon={ZoomIn} />
              </div>
            </div>

            {/* Image Comparison Grid */}
            <div className="grid grid-cols-2 gap-4">
              {/* Query Image */}
              <div className="space-y-2">
                <p className="text-xs font-bold text-slate-600 uppercase">Query Image</p>
                <div className="bg-slate-100 rounded-lg overflow-hidden border-2 border-blue-500">
                  <img 
                    src={queryImage} 
                    alt="Query" 
                    className="w-full h-80 object-contain transition-transform"
                    style={{ transform: `scale(${zoom})` }}
                  />
                </div>
              </div>

              {/* Result Image */}
              <div className="space-y-2">
                <p className="text-xs font-bold text-slate-600 uppercase">Matched Case</p>
                <div className="bg-slate-100 rounded-lg overflow-hidden border-2 border-emerald-500">
                  <img 
                    src={result.thumbnail_url} 
                    alt="Result" 
                    className="w-full h-80 object-contain transition-transform"
                    style={{ transform: `scale(${zoom})` }}
                  />
                </div>
              </div>
            </div>

            {/* Similarity Metrics */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                <p className="text-xs text-blue-700 font-medium mb-2">Similarity Score</p>
                <p className="text-3xl font-bold text-blue-900">
                  {Math.round(result.similarity_score * 100)}%
                </p>
              </div>
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 text-center">
                <p className="text-xs text-purple-700 font-medium mb-2">Hamming Distance</p>
                <p className="text-3xl font-bold text-purple-900">
                  {result.hamming_distance}
                  <span className="text-lg">/256</span>
                </p>
              </div>
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 text-center">
                <p className="text-xs text-emerald-700 font-medium mb-2">Confidence</p>
                <p className="text-xl font-bold text-emerald-900 uppercase">
                  {result.confidence.replace('_', ' ')}
                </p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'metadata' && (
          <div className="space-y-6">
            {/* Patient Information */}
            <div>
              <h3 className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
                <User size={16} />
                Patient Information
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                  <p className="text-xs text-slate-600 mb-1">Patient ID</p>
                  <p className="font-mono font-semibold text-slate-800">
                    {result.metadata.patient_id || 'N/A'}
                  </p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                  <p className="text-xs text-slate-600 mb-1">Age</p>
                  <p className="font-semibold text-slate-800">
                    {result.metadata.age ? `${result.metadata.age} years` : 'N/A'}
                  </p>
                </div>
              </div>
            </div>

            {/* Clinical Information */}
            <div>
              <h3 className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
                <Activity size={16} />
                Clinical Information
              </h3>
              <div className="space-y-3">
                <div className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <AlertCircle className="text-amber-600 flex-shrink-0 mt-0.5" size={18} />
                  <div>
                    <p className="text-xs font-semibold text-amber-800 mb-1">Diagnosis</p>
                    <p className="text-sm text-amber-900">
                      {result.metadata.diagnosis || 'Not specified'}
                    </p>
                  </div>
                </div>

                {result.metadata.severity && (
                  <div className="flex items-start gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <Pill className="text-red-600 flex-shrink-0 mt-0.5" size={18} />
                    <div>
                      <p className="text-xs font-semibold text-red-800 mb-1">Severity</p>
                      <p className="text-sm text-red-900 capitalize">
                        {result.metadata.severity}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Study Information */}
            <div>
              <h3 className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
                <Calendar size={16} />
                Study Information
              </h3>
              <div className="bg-slate-50 rounded-lg p-4 border border-slate-200 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Study Type</span>
                  <span className="font-semibold text-slate-800 uppercase">
                    {result.metadata.study_type?.replace('_', ' ') || 'Unknown'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Image ID</span>
                  <span className="font-mono text-xs text-slate-800">
                    {result.image_id}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3 pt-4 border-t border-slate-200">
          <Button variant="primary" icon={Download}>
            Download Image
          </Button>
          <Button variant="secondary" icon={FileText}>
            Add to Report
          </Button>
          <Button variant="ghost" icon={Flag}>
            Flag as Incorrect
          </Button>
        </div>
      </div>
    </Modal>
  );
};

ResultDetailModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  result: PropTypes.object,
  queryImage: PropTypes.string,
};

export default ResultDetailModal;
