// frontend/src/pages/Search.jsx
import React, { useState } from 'react';
import { useSearch } from '../hooks/useSearch';
import { useSettings } from '../context/SettingsContext';
import QueryPanel from '../components/search/QueryPanel';
import SearchParams from '../components/search/SearchParams';
import ResultsGrid from '../components/search/ResultsGrid';
import ResultDetailModal from '../components/search/ResultDetailModal';
import Button from '../components/common/Button';
import { Search as SearchIcon, RotateCw } from 'lucide-react';

const Search = () => {
  const { search, loading, results, stats, error, clearResults } = useSearch();
  const { getSearchDefaults } = useSettings();
  
  const [selectedFile, setSelectedFile] = useState(null);
  const [queryPreview, setQueryPreview] = useState(null);
  const [searchParams, setSearchParams] = useState({
    topK: 5,
    minSimilarity: 0.7,
    studyType: '',
    hammingThreshold: 66,
    useFHE: true,
    ...getSearchDefaults(),
  });
  const [selectedResult, setSelectedResult] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    
    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setQueryPreview(reader.result);
    };
    reader.readAsDataURL(file);
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    setQueryPreview(null);
    clearResults();
  };

  const handleSearch = async () => {
    if (!selectedFile) return;
    
    await search(selectedFile, searchParams);
  };

  const handleViewDetails = (result) => {
    setSelectedResult(result);
    setShowDetailModal(true);
  };

  const handleRerun = () => {
    if (selectedFile) {
      handleSearch();
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="flex h-screen">
        {/* Left Panel - Query & Parameters */}
        <div className="w-96 bg-white border-r border-slate-200 overflow-y-auto">
          <div className="p-6 space-y-6">
            <div>
              <h1 className="text-2xl font-bold text-slate-800 mb-2">
                Similarity Search
              </h1>
              <p className="text-sm text-slate-600">
                Find similar medical images using FHE-powered search
              </p>
            </div>

            {/* Query Panel */}
            <QueryPanel
              onFileSelect={handleFileSelect}
              selectedFile={selectedFile}
              onClearFile={handleClearFile}
              loading={loading}
            />

            {/* Search Parameters */}
            {selectedFile && (
              <>
                <div className="border-t border-slate-200 pt-6">
                  <SearchParams
                    params={searchParams}
                    onChange={setSearchParams}
                    disabled={loading}
                  />
                </div>

                {/* Search Button */}
                <Button
                  onClick={handleSearch}
                  loading={loading}
                  disabled={!selectedFile || loading}
                  icon={SearchIcon}
                  variant="primary"
                  size="lg"
                  className="w-full"
                >
                  {loading ? 'Searching Encrypted Database...' : 'Run FHE Search'}
                </Button>

                {/* Rerun Button */}
                {results.length > 0 && !loading && (
                  <Button
                    onClick={handleRerun}
                    icon={RotateCw}
                    variant="secondary"
                    size="md"
                    className="w-full"
                  >
                    Rerun Search
                  </Button>
                )}
              </>
            )}

            {/* Error Display */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-sm text-red-800 font-medium">
                  {error}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Results */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-8">
            <ResultsGrid
              results={results}
              loading={loading}
              stats={stats}
              onViewDetails={handleViewDetails}
            />
          </div>
        </div>
      </div>

      {/* Result Detail Modal */}
      <ResultDetailModal
        isOpen={showDetailModal}
        onClose={() => setShowDetailModal(false)}
        result={selectedResult}
        queryImage={queryPreview}
      />
    </div>
  );
};

export default Search;
