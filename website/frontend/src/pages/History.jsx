// frontend/src/pages/History.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import SearchHistoryList from '../components/history/SearchHistoryList';
import UploadHistoryList from '../components/history/UploadHistoryList';
import api from '../services/api';

const History = () => {
  const navigate = useNavigate();
  const { tenant } = useAuth();
  const [activeTab, setActiveTab] = useState('searches'); // 'searches' or 'uploads'
  const [searches, setSearches] = useState([]);
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        const tenantId = tenant?.id || 'hospital_001';

        // Fetch both histories in parallel
        const [searchRes, uploadRes] = await Promise.all([
          api.get('/history/searches', { params: { tenant_id: tenantId } })
            .catch(() => ({ data: { searches: [] } })),
          api.get('/history/uploads', { params: { tenant_id: tenantId } })
            .catch(() => ({ data: { uploads: [] } })),
        ]);

        setSearches(searchRes.data.searches || []);
        setUploads(uploadRes.data.uploads || []);
      } catch (err) {
        console.error('Failed to fetch history:', err);
        setError(err.response?.data?.message || 'Failed to load history');
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [tenant]);

  const handleViewResults = (search) => {
    // Navigate to search results page or open modal with cached results
    navigate(`/search/results/${search.query_id}`);
  };

  const handleRerunSearch = (search) => {
    // Navigate to search page with pre-filled parameters
    navigate('/search', { 
      state: { 
        rerunParams: search.parameters,
        queryId: search.query_id 
      } 
    });
  };

  const handleViewImage = (upload) => {
    // Navigate to image detail page
    navigate(`/images/${upload.image_id}`);
  };

  const handleSearchSimilar = (upload) => {
    // Navigate to search page with this image as query
    navigate('/search', { 
      state: { 
        queryImageId: upload.image_id,
        queryThumbnail: upload.thumbnail_url
      } 
    });
  };

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <p className="text-red-800 font-semibold">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-slate-800 mb-2">History</h1>
          <p className="text-slate-600">
            View your past searches and uploaded images
          </p>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-1 inline-flex">
          <button
            onClick={() => setActiveTab('searches')}
            className={`px-6 py-2.5 rounded-lg font-semibold transition-all ${
              activeTab === 'searches'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-800 hover:bg-slate-50'
            }`}
          >
            Search History ({searches.length})
          </button>
          <button
            onClick={() => setActiveTab('uploads')}
            className={`px-6 py-2.5 rounded-lg font-semibold transition-all ${
              activeTab === 'uploads'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-800 hover:bg-slate-50'
            }`}
          >
            Upload History ({uploads.length})
          </button>
        </div>

        {/* Content */}
        {activeTab === 'searches' ? (
          <SearchHistoryList
            searches={searches}
            loading={loading}
            onViewResults={handleViewResults}
            onRerunSearch={handleRerunSearch}
          />
        ) : (
          <UploadHistoryList
            uploads={uploads}
            loading={loading}
            onViewImage={handleViewImage}
            onSearchSimilar={handleSearchSimilar}
          />
        )}
      </div>
    </div>
  );
};

export default History;
