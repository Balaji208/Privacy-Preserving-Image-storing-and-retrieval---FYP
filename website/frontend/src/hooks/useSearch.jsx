// frontend/src/hooks/useSearch.js
import { useState, useCallback } from 'react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useSettings } from '../context/SettingsContext';

export const useSearch = () => {
  const { tenant } = useAuth();
  const { settings } = useSettings();
  
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [queryId, setQueryId] = useState(null);

  /**
   * Execute similarity search
   * @param {File|Blob} queryImage - The query image file
   * @param {Object} params - Search parameters
   * @param {number} params.topK - Number of results to return
   * @param {number} params.minSimilarity - Minimum similarity threshold (0-1)
   * @param {string} params.studyType - Optional study type filter
   * @param {number} params.hammingThreshold - Hamming distance threshold
   * @param {boolean} params.useFHE - Whether to use FHE encryption
   */
  const search = useCallback(async (queryImage, params = {}) => {
    if (!queryImage) {
      setError('No query image provided');
      return null;
    }

    setLoading(true);
    setError(null);
    setResults([]);
    setStats(null);

    try {
      const formData = new FormData();
      formData.append('query_image', queryImage);
      formData.append('tenant_id', tenant?.id || 'hospital_001');
      
      // Use provided params or fall back to settings defaults
      formData.append('top_k', params.topK || settings.defaultTopK || 5);
      
      if (params.minSimilarity !== undefined) {
        formData.append('min_similarity', params.minSimilarity);
      }
      
      if (params.studyType) {
        formData.append('study_type', params.studyType);
      }

      if (params.hammingThreshold !== undefined) {
        formData.append('hamming_threshold', params.hammingThreshold);
      }

      const startTime = Date.now();

      const { data } = await api.post('/search', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const endTime = Date.now();
      const clientTime = endTime - startTime;

      setResults(data.results || []);
      setStats({
        ...data.stats,
        client_time_ms: clientTime,
        server_time_ms: data.processing_time_ms,
      });
      setQueryId(data.query_id);

      return {
        success: true,
        results: data.results,
        stats: data.stats,
        queryId: data.query_id,
      };
    } catch (err) {
      const errorMessage = err.response?.data?.message || err.message || 'Search failed';
      setError(errorMessage);
      console.error('Search error:', err);
      return {
        success: false,
        error: errorMessage,
      };
    } finally {
      setLoading(false);
    }
  }, [tenant, settings]);

  /**
   * Clear search results and reset state
   */
  const clearResults = useCallback(() => {
    setResults([]);
    setStats(null);
    setError(null);
    setQueryId(null);
  }, []);

  /**
   * Retry last search
   */
  const retry = useCallback((queryImage, params) => {
    return search(queryImage, params);
  }, [search]);

  return {
    search,
    loading,
    results,
    stats,
    error,
    queryId,
    clearResults,
    retry,
  };
};

export default useSearch;
