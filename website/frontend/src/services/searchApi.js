// frontend/src/services/searchApi.js
import api, { createFormDataRequest } from './api';

/**
 * Search Service API
 * Handles similarity search operations using FHE
 */

/**
 * Search for similar images
 * @param {File|Blob} queryImage - Query image file
 * @param {Object} params - Search parameters
 * @returns {Promise<Object>} Search results with similarity scores
 */
export const searchSimilarImages = async (queryImage, params = {}) => {
  const formData = new FormData();
  formData.append('query_image', queryImage);
  formData.append('tenant_id', params.tenant_id || 'user_001');
  formData.append('top_k', params.topK || 5);

  // Optional filters
  if (params.minSimilarity !== undefined) {
    formData.append('min_similarity', params.minSimilarity);
  }
  if (params.studyType) {
    formData.append('study_type', params.studyType);
  }
  if (params.hammingThreshold !== undefined) {
    formData.append('hamming_threshold', params.hammingThreshold);
  }

  // Advanced filters
  if (params.filters) {
    formData.append('filters', JSON.stringify(params.filters));
  }

  try {
    const response = await createFormDataRequest('/search', formData, {
      timeout: 120000, // 2 minutes for FHE computation
    });

    return {
      success: true,
      data: response.data,
      duration: response.duration,
    };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.message || error.message || 'Search failed',
    };
  }
};

/**
 * Search by image ID (use existing indexed image as query)
 * @param {string} imageId - Image ID to use as query
 * @param {Object} params - Search parameters
 * @returns {Promise<Object>} Search results
 */
export const searchByImageId = async (imageId, params = {}) => {
  try {
    const response = await api.post('/search/by-id', {
      image_id: imageId,
      tenant_id: params.tenant_id || 'hospital_001',
      top_k: params.topK || 5,
      min_similarity: params.minSimilarity,
      study_type: params.studyType,
      filters: params.filters,
    });

    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.message || error.message,
    };
  }
};

/**
 * Get search results by query ID
 * @param {string} queryId - Query ID from previous search
 * @returns {Promise<Object>} Cached search results
 */
export const getSearchResults = async (queryId) => {
  try {
    const response = await api.get(`/search/results/${queryId}`);
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.message || error.message,
    };
  }
};

/**
 * Get search history
 * @param {string} tenantId - Tenant ID
 * @param {Object} options - Pagination and filter options
 * @returns {Promise<Object>} Search history
 */
export const getSearchHistory = async (tenantId, options = {}) => {
  try {
    const response = await api.get('/history/searches', {
      params: {
        tenant_id: tenantId,
        limit: options.limit || 50,
        offset: options.offset || 0,
        study_type: options.studyType,
        from_date: options.fromDate,
        to_date: options.toDate,
      },
    });

    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.message || error.message,
    };
  }
};

/**
 * Delete search history entry
 * @param {string} queryId - Query ID to delete
 * @returns {Promise<Object>} Deletion result
 */
export const deleteSearchHistory = async (queryId) => {
  try {
    const response = await api.delete(`/history/searches/${queryId}`);
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.message || error.message,
    };
  }
};

/**
 * Get search statistics
 * @param {string} tenantId - Tenant ID
 * @returns {Promise<Object>} Search statistics
 */
export const getSearchStats = async (tenantId) => {
  try {
    const response = await api.get('/search/stats', {
      params: { tenant_id: tenantId },
    });
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.message || error.message,
    };
  }
};

export default {
  searchSimilarImages,
  searchByImageId,
  getSearchResults,
  getSearchHistory,
  deleteSearchHistory,
  getSearchStats,
};
