// frontend/src/components/search/ResultsGrid.jsx
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Grid, List, SortAsc, SortDesc } from 'lucide-react';
import ResultCard from './ResultCard';
import Spinner from '../common/Spinner';

const ResultsGrid = ({ results, loading, stats, onViewDetails }) => {
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'list'
  const [sortBy, setSortBy] = useState('similarity'); // 'similarity', 'confidence', 'hamming'
  const [sortOrder, setSortOrder] = useState('desc');

  // Sort results
  const sortedResults = [...results].sort((a, b) => {
    let comparison = 0;
    
    switch (sortBy) {
      case 'similarity':
        comparison = a.similarity_score - b.similarity_score;
        break;
      case 'confidence':
        { const confidenceOrder = { very_high: 4, high: 3, medium: 2, low: 1 };
        comparison = (confidenceOrder[a.confidence] || 0) - (confidenceOrder[b.confidence] || 0);
        break; }
      case 'hamming':
        comparison = a.hamming_distance - b.hamming_distance;
        break;
      default:
        comparison = 0;
    }
    
    return sortOrder === 'asc' ? comparison : -comparison;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner size="lg" text="Searching encrypted database..." />
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="text-center py-20 bg-white rounded-xl border border-slate-200">
        <div className="w-20 h-20 bg-slate-100 rounded-full mx-auto mb-4 flex items-center justify-center">
          <Grid className="text-slate-400" size={40} />
        </div>
        <h3 className="text-lg font-bold text-slate-800 mb-2">No Results</h3>
        <p className="text-slate-500 text-sm">
          Upload a query image to find similar medical cases
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Results Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white rounded-xl border border-slate-200 p-4">
        <div>
          <h2 className="text-lg font-bold text-slate-800">
            Search Results
          </h2>
          <p className="text-sm text-slate-500">
            Found {results.length} similar {results.length === 1 ? 'case' : 'cases'}
            {stats && ` in ${stats.fhe_computation_time_ms}ms`}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Sort Options */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="similarity">Sort by Similarity</option>
            <option value="confidence">Sort by Confidence</option>
            <option value="hamming">Sort by Hamming</option>
          </select>

          {/* Sort Order */}
          <button
            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            title={sortOrder === 'asc' ? 'Ascending' : 'Descending'}
          >
            {sortOrder === 'asc' ? (
              <SortAsc size={20} className="text-slate-600" />
            ) : (
              <SortDesc size={20} className="text-slate-600" />
            )}
          </button>

          {/* View Mode Toggle */}
          <div className="flex border border-slate-300 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 transition-colors ${
                viewMode === 'grid' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-white text-slate-600 hover:bg-slate-50'
              }`}
            >
              <Grid size={18} />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 transition-colors ${
                viewMode === 'list' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-white text-slate-600 hover:bg-slate-50'
              }`}
            >
              <List size={18} />
            </button>
          </div>
        </div>
      </div>

      {/* Stats Summary */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-xs text-blue-700 font-medium mb-1">Candidates Retrieved</p>
            <p className="text-2xl font-bold text-blue-900">{stats.candidates_retrieved}</p>
          </div>
          <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
            <p className="text-xs text-teal-700 font-medium mb-1">Candidates Ranked</p>
            <p className="text-2xl font-bold text-teal-900">{stats.candidates_ranked}</p>
          </div>
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
            <p className="text-xs text-purple-700 font-medium mb-1">FHE Computation</p>
            <p className="text-2xl font-bold text-purple-900">{stats.fhe_computation_time_ms}ms</p>
          </div>
        </div>
      )}

      {/* Results Display */}
      <div className={
        viewMode === 'grid'
          ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'
          : 'space-y-4'
      }>
        {sortedResults.map((result) => (
          <ResultCard
            key={result.image_id}
            result={result}
            onViewDetails={onViewDetails}
          />
        ))}
      </div>
    </div>
  );
};

ResultsGrid.propTypes = {
  results: PropTypes.array.isRequired,
  loading: PropTypes.bool,
  stats: PropTypes.object,
  onViewDetails: PropTypes.func.isRequired,
};

export default ResultsGrid;
