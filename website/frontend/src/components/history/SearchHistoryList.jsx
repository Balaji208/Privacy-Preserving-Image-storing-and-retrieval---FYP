// frontend/src/components/history/SearchHistoryList.jsx
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { 
  Search, 
  Calendar, 
  Clock, 
  Eye, 
  RotateCw,
  Filter,
  ChevronDown,
  Image as ImageIcon,
  TrendingUp
} from 'lucide-react';
import Button from '../common/Button';

const SearchHistoryList = ({ 
  searches = [], 
  loading = false,
  onViewResults,
  onRerunSearch 
}) => {
  const [sortBy, setSortBy] = useState('date'); // date, results, time
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

  const formatDuration = (ms) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  // Sort searches
  const sortedSearches = [...searches].sort((a, b) => {
    switch (sortBy) {
      case 'date':
        return new Date(b.timestamp) - new Date(a.timestamp);
      case 'results':
        return b.results_count - a.results_count;
      case 'time':
        return a.processing_time_ms - b.processing_time_ms;
      default:
        return 0;
    }
  });

  // Filter by study type
  const filteredSearches = filterStudyType === 'all' 
    ? sortedSearches 
    : sortedSearches.filter(s => s.study_type === filterStudyType);

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-slate-200 p-6 animate-pulse">
            <div className="flex gap-4">
              <div className="w-24 h-24 bg-slate-200 rounded-lg"></div>
              <div className="flex-1">
                <div className="h-5 bg-slate-200 rounded w-1/3 mb-3"></div>
                <div className="h-4 bg-slate-200 rounded w-1/2 mb-2"></div>
                <div className="h-4 bg-slate-200 rounded w-2/3"></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (searches.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
        <Search className="mx-auto text-slate-300 mb-4" size={64} />
        <h3 className="text-lg font-bold text-slate-800 mb-2">No Search History</h3>
        <p className="text-slate-500 text-sm mb-6">
          Your search history will appear here once you perform your first similarity search
        </p>
        <Button onClick={() => window.location.href = '/search'} icon={Search}>
          Start New Search
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
              <option value="results">Most Results</option>
              <option value="time">Fastest</option>
            </select>
          </div>

          <div className="ml-auto text-sm text-slate-500 font-medium">
            {filteredSearches.length} {filteredSearches.length === 1 ? 'search' : 'searches'}
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

      {/* Search History Items */}
      <div className="space-y-4">
        {filteredSearches.map((search) => (
          <div 
            key={search.query_id} 
            className="bg-white rounded-xl border border-slate-200 p-6 hover:shadow-md transition-all duration-200"
          >
            <div className="flex gap-6">
              {/* Query Image Thumbnail */}
              <div className="flex-shrink-0">
                <div className="w-32 h-32 bg-slate-100 rounded-lg overflow-hidden border-2 border-slate-200">
                  {search.query_thumbnail ? (
                    <img 
                      src={search.query_thumbnail} 
                      alt="Query" 
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <ImageIcon className="text-slate-400" size={32} />
                    </div>
                  )}
                </div>
              </div>

              {/* Search Details */}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-lg font-bold text-slate-800 mb-1">
                      Search #{search.query_id.slice(-8)}
                    </h3>
                    <div className="flex items-center gap-4 text-sm text-slate-500">
                      <span className="flex items-center gap-1">
                        <Calendar size={14} />
                        {formatDate(search.timestamp)}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock size={14} />
                        {formatDuration(search.processing_time_ms)}
                      </span>
                    </div>
                  </div>
                  
                  {search.study_type && (
                    <span className="px-3 py-1 bg-blue-50 text-blue-700 text-xs font-bold rounded-full border border-blue-200">
                      {search.study_type.replace('_', ' ').toUpperCase()}
                    </span>
                  )}
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                    <p className="text-xs text-slate-600 font-medium mb-1">Results Found</p>
                    <p className="text-2xl font-bold text-slate-800">{search.results_count}</p>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                    <p className="text-xs text-slate-600 font-medium mb-1">Avg Similarity</p>
                    <p className="text-2xl font-bold text-teal-600">
                      {search.avg_similarity ? `${Math.round(search.avg_similarity * 100)}%` : 'N/A'}
                    </p>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                    <p className="text-xs text-slate-600 font-medium mb-1">FHE Time</p>
                    <p className="text-2xl font-bold text-purple-600">
                      {search.fhe_time_ms ? `${search.fhe_time_ms}ms` : 'N/A'}
                    </p>
                  </div>
                </div>

                {/* Parameters */}
                {search.parameters && (
                  <div className="mb-4">
                    <p className="text-xs text-slate-500 font-medium mb-2">Search Parameters:</p>
                    <div className="flex flex-wrap gap-2">
                      <span className="text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded">
                        Top-K: {search.parameters.top_k}
                      </span>
                      {search.parameters.min_similarity && (
                        <span className="text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded">
                          Min Similarity: {search.parameters.min_similarity}
                        </span>
                      )}
                      {search.parameters.hamming_threshold && (
                        <span className="text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded">
                          Hamming: {search.parameters.hamming_threshold}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3">
                  <Button 
                    onClick={() => onViewResults(search)}
                    variant="primary"
                    size="sm"
                    icon={Eye}
                  >
                    View Results
                  </Button>
                  <Button 
                    onClick={() => onRerunSearch(search)}
                    variant="secondary"
                    size="sm"
                    icon={RotateCw}
                  >
                    Rerun Search
                  </Button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

SearchHistoryList.propTypes = {
  searches: PropTypes.arrayOf(
    PropTypes.shape({
      query_id: PropTypes.string.isRequired,
      timestamp: PropTypes.string.isRequired,
      results_count: PropTypes.number.isRequired,
      processing_time_ms: PropTypes.number,
      fhe_time_ms: PropTypes.number,
      avg_similarity: PropTypes.number,
      study_type: PropTypes.string,
      query_thumbnail: PropTypes.string,
      parameters: PropTypes.object,
    })
  ),
  loading: PropTypes.bool,
  onViewResults: PropTypes.func.isRequired,
  onRerunSearch: PropTypes.func.isRequired,
};

export default SearchHistoryList;
