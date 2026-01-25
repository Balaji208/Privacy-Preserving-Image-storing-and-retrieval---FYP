// frontend/src/components/search/ResultCard.jsx
import React from 'react';
import PropTypes from 'prop-types';
import { Eye, User, Calendar, Activity } from 'lucide-react';
import Button from '../common/Button';

const ResultCard = ({ result, onViewDetails }) => {
  const confidenceConfig = {
    very_high: {
      bg: 'bg-emerald-100',
      text: 'text-emerald-700',
      border: 'border-emerald-200',
      label: 'Very High',
    },
    high: {
      bg: 'bg-blue-100',
      text: 'text-blue-700',
      border: 'border-blue-200',
      label: 'High',
    },
    medium: {
      bg: 'bg-amber-100',
      text: 'text-amber-700',
      border: 'border-amber-200',
      label: 'Medium',
    },
    low: {
      bg: 'bg-slate-100',
      text: 'text-slate-700',
      border: 'border-slate-200',
      label: 'Low',
    },
  };

  const config = confidenceConfig[result.confidence] || confidenceConfig.low;

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden hover:shadow-lg transition-all duration-200 group">
      {/* Image Section */}
      <div className="relative h-56 bg-slate-100">
        {/* Rank Badge */}
        <div className="absolute top-3 left-3 z-10">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-blue-700 rounded-full flex items-center justify-center shadow-lg">
            <span className="text-white font-bold text-sm">#{result.rank}</span>
          </div>
        </div>

        {/* Confidence Badge */}
        <div className="absolute top-3 right-3 z-10">
          <span className={`px-3 py-1 rounded-full text-xs font-bold border ${config.bg} ${config.text} ${config.border} shadow-sm`}>
            {config.label}
          </span>
        </div>

        {/* Image */}
        <img 
          src={result.thumbnail_url} 
          alt={`Result ${result.rank}`}
          className="w-full h-full object-contain p-2"
          loading="lazy"
        />

        {/* Hover Overlay */}
        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <Button 
            onClick={() => onViewDetails(result)}
            variant="ghost"
            className="bg-white hover:bg-white text-slate-800"
            icon={Eye}
          >
            View Details
          </Button>
        </div>
      </div>

      {/* Details Section */}
      <div className="p-4">
        {/* Similarity Score */}
        <div className="mb-4">
          <div className="flex items-end justify-between mb-2">
            <span className="text-xs font-medium text-slate-600">Similarity Score</span>
            <span className="text-3xl font-bold text-blue-600">
              {Math.round(result.similarity_score * 100)}%
            </span>
          </div>
          <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
            <div 
              className="bg-gradient-to-r from-blue-500 to-teal-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${result.similarity_score * 100}%` }}
            ></div>
          </div>
        </div>

        {/* Hamming Distance */}
        <div className="mb-4 p-3 bg-purple-50 border border-purple-200 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-purple-700">Hamming Distance</span>
            <span className="font-mono text-sm font-bold text-purple-900">
              {result.hamming_distance}/256
            </span>
          </div>
          <div className="w-full bg-purple-200 rounded-full h-1.5 mt-2">
            <div 
              className="bg-purple-600 h-full rounded-full"
              style={{ width: `${((256 - result.hamming_distance) / 256) * 100}%` }}
            ></div>
          </div>
        </div>

        {/* Metadata */}
        <div className="space-y-2 mb-4">
          {result.metadata.patient_id && (
            <div className="flex items-center gap-2 text-sm">
              <User size={14} className="text-slate-400" />
              <span className="text-slate-600 text-xs">Patient:</span>
              <span className="font-semibold text-slate-800 text-xs">
                {result.metadata.patient_id}
              </span>
            </div>
          )}

          {result.metadata.diagnosis && (
            <div className="flex items-center gap-2 text-sm">
              <Activity size={14} className="text-slate-400" />
              <span className="text-slate-600 text-xs">Diagnosis:</span>
              <span className="font-medium text-slate-800 text-xs truncate">
                {result.metadata.diagnosis}
              </span>
            </div>
          )}

          {result.metadata.age && (
            <div className="flex items-center gap-2 text-sm">
              <Calendar size={14} className="text-slate-400" />
              <span className="text-slate-600 text-xs">Age:</span>
              <span className="font-medium text-slate-800 text-xs">
                {result.metadata.age} years
              </span>
            </div>
          )}
        </div>

        {/* Study Type Tag */}
        {result.metadata.study_type && (
          <div className="mb-4">
            <span className="inline-block px-3 py-1 bg-slate-100 text-slate-700 text-xs font-bold rounded-full">
              {result.metadata.study_type.replace('_', ' ').toUpperCase()}
            </span>
          </div>
        )}

        {/* Action Button */}
        <Button 
          onClick={() => onViewDetails(result)}
          variant="secondary"
          size="sm"
          icon={Eye}
          className="w-full"
        >
          View Case Details
        </Button>
      </div>
    </div>
  );
};

ResultCard.propTypes = {
  result: PropTypes.shape({
    rank: PropTypes.number.isRequired,
    image_id: PropTypes.string.isRequired,
    similarity_score: PropTypes.number.isRequired,
    hamming_distance: PropTypes.number.isRequired,
    confidence: PropTypes.oneOf(['very_high', 'high', 'medium', 'low']).isRequired,
    thumbnail_url: PropTypes.string.isRequired,
    metadata: PropTypes.shape({
      patient_id: PropTypes.string,
      diagnosis: PropTypes.string,
      age: PropTypes.number,
      study_type: PropTypes.string,
    }),
  }).isRequired,
  onViewDetails: PropTypes.func.isRequired,
};

export default ResultCard;
