// frontend/src/components/search/SearchParams.jsx
import React from 'react';
import PropTypes from 'prop-types';
import { Sliders, Info } from 'lucide-react';

const SearchParams = ({ params, onChange, disabled = false }) => {
  const studyTypes = [
    { value: '', label: 'All Types' },
    { value: 'brain_mri', label: 'Brain MRI' },
    { value: 'chest_xray', label: 'Chest X-Ray' },
    { value: 'lung_ct', label: 'Lung CT' },
    { value: 'abdominal_ct', label: 'Abdominal CT' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Sliders className="text-slate-600" size={18} />
        <h3 className="text-sm font-bold text-slate-800">Search Parameters</h3>
      </div>

      {/* Top-K Results */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-semibold text-slate-700">
            Number of Results
          </label>
          <span className="text-lg font-bold text-blue-600">{params.topK}</span>
        </div>
        <input
          type="range"
          min="1"
          max="20"
          value={params.topK}
          onChange={(e) => onChange({ ...params, topK: parseInt(e.target.value) })}
          disabled={disabled}
          className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer slider-thumb"
        />
        <div className="flex justify-between text-xs text-slate-500 mt-1">
          <span>1</span>
          <span>20</span>
        </div>
      </div>

      {/* Similarity Threshold */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-semibold text-slate-700">
            Min Similarity
          </label>
          <span className="text-lg font-bold text-teal-600">
            {Math.round(params.minSimilarity * 100)}%
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          value={params.minSimilarity * 100}
          onChange={(e) => onChange({ ...params, minSimilarity: parseFloat(e.target.value) / 100 })}
          disabled={disabled}
          className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer slider-thumb"
        />
        <div className="flex justify-between text-xs text-slate-500 mt-1">
          <span>0%</span>
          <span>100%</span>
        </div>
        <div className="flex items-start gap-2 mt-2 p-2 bg-amber-50 border border-amber-200 rounded">
          <Info size={14} className="text-amber-600 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-amber-700">
            Higher threshold = more strict matching
          </p>
        </div>
      </div>

      {/* Study Type Filter */}
      <div>
        <label className="block text-sm font-semibold text-slate-700 mb-2">
          Study Type Filter
        </label>
        <select
          value={params.studyType}
          onChange={(e) => onChange({ ...params, studyType: e.target.value })}
          disabled={disabled}
          className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-lg text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
        >
          {studyTypes.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </select>
      </div>

      {/* Advanced Options Toggle */}
      <details className="group">
        <summary className="cursor-pointer text-sm font-semibold text-blue-600 hover:text-blue-700 list-none flex items-center gap-2">
          <span className="transform transition-transform group-open:rotate-90">▶</span>
          Advanced Options
        </summary>
        <div className="mt-4 space-y-4 pl-4 border-l-2 border-blue-200">
          {/* Hamming Threshold */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-slate-700">
                Hamming Threshold
              </label>
              <span className="text-sm font-bold text-purple-600">
                {params.hammingThreshold} bits
              </span>
            </div>
            <input
              type="range"
              min="32"
              max="128"
              value={params.hammingThreshold}
              onChange={(e) => onChange({ ...params, hammingThreshold: parseInt(e.target.value) })}
              disabled={disabled}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
            />
            <p className="text-xs text-slate-500 mt-1">
              Maximum bit difference for candidate selection
            </p>
          </div>

          {/* Use FHE Toggle */}
          <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200">
            <div>
              <p className="text-sm font-medium text-slate-800">Use FHE Encryption</p>
              <p className="text-xs text-slate-500 mt-0.5">Encrypted similarity computation</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={params.useFHE}
                onChange={(e) => onChange({ ...params, useFHE: e.target.checked })}
                disabled={disabled}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-300 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500"></div>
            </label>
          </div>
        </div>
      </details>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Info className="text-blue-600 flex-shrink-0 mt-0.5" size={18} />
          <div className="text-xs text-blue-800 space-y-1">
            <p className="font-semibold">Search Performance Tips:</p>
            <ul className="list-disc list-inside space-y-0.5 text-blue-700">
              <li>Lower Top-K = faster results</li>
              <li>Higher similarity threshold = fewer results</li>
              <li>FHE adds 200-500ms processing time</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

SearchParams.propTypes = {
  params: PropTypes.shape({
    topK: PropTypes.number.isRequired,
    minSimilarity: PropTypes.number.isRequired,
    studyType: PropTypes.string,
    hammingThreshold: PropTypes.number,
    useFHE: PropTypes.bool,
  }).isRequired,
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
};

export default SearchParams;
