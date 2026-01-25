// frontend/src/services/api.js
import axios from 'axios';

/**
 * Base API configuration
 * Centralizes all HTTP requests to the backend
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8002/api/v1',  // ✅ FIXED
  timeout: 120000, // 2 minutes - Extended for FHE operations
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request interceptor
 * Adds authentication token to all requests
 */
api.interceptors.request.use(
  (config) => {
    // Get token from localStorage
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Add timestamp for request tracking
    config.metadata = { startTime: new Date() };

    // Log request in development
    if (import.meta.env.DEV) {  // ✅ FIXED
      console.log(`[API Request] ${config.method.toUpperCase()} ${config.url}`, {
        params: config.params,
        data: config.data,
      });
    }

    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

/**
 * Response interceptor
 * Handles common response patterns and errors
 */
api.interceptors.response.use(
  (response) => {
    // Calculate request duration
    const duration = new Date() - response.config.metadata.startTime;

    // Log response in development
    if (import.meta.env.DEV) {  // ✅ FIXED
      console.log(
        `[API Response] ${response.config.method.toUpperCase()} ${response.config.url}`,
        {
          status: response.status,
          duration: `${duration}ms`,
          data: response.data,
        }
      );
    }

    // Add performance metrics to response
    response.duration = duration;
    return response;
  },
  (error) => {
    // Calculate request duration even on error
    const duration = error.config?.metadata?.startTime
      ? new Date() - error.config.metadata.startTime
      : 0;

    // Handle different error types
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;

      console.error(`[API Error ${status}]`, {
        url: error.config?.url,
        method: error.config?.method,
        duration: `${duration}ms`,
        message: data?.message || error.message,
        details: data?.details,
      });

      // Handle specific status codes
      switch (status) {
        case 401:
          // Unauthorized - redirect to login
          localStorage.removeItem('authToken');
          localStorage.removeItem('user');
          localStorage.removeItem('tenant');
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
          break;

        case 403:
          // Forbidden - insufficient permissions
          console.warn('Access forbidden:', data?.message);
          break;

        case 404:
          // Not found
          console.warn('Resource not found:', error.config?.url);
          break;

        case 429:
          // Rate limited
          console.warn('Rate limit exceeded. Please try again later.');
          break;

        case 500:
        case 502:
        case 503:
          // Server errors
          console.error('Server error:', data?.message);
          break;

        default:
          console.error('Unexpected error:', data?.message);
      }
    } else if (error.request) {
      // Request made but no response received
      console.error('[API Network Error]', {
        url: error.config?.url,
        message: 'No response from server',
        duration: `${duration}ms`,
      });
    } else {
      // Error in request configuration
      console.error('[API Configuration Error]', error.message);
    }

    return Promise.reject(error);
  }
);

/**
 * Helper function to handle multipart/form-data requests
 */
export const createFormDataRequest = (url, formData, config = {}) => {
  return api.post(url, formData, {
    ...config,
    headers: {
      ...config.headers,
      'Content-Type': 'multipart/form-data',
    },
  });
};

/**
 * Helper function for download requests
 */
export const downloadFile = async (url, filename, params = {}) => {
  try {
    const response = await api.get(url, {
      params,
      responseType: 'blob',
    });

    // Create download link
    const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = blobUrl;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(blobUrl);

    return { success: true };
  } catch (error) {
    console.error('Download failed:', error);
    return { success: false, error: error.message };
  }
};

/**
 * Health check endpoint
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

/**
 * Search for similar images
 * @param {File} imageFile - Image file to search
 * @param {number} k - Number of results to return (1-20)
 * @returns {Promise<Object>} Search results
 */
export const searchSimilarImages = async (imageFile, k) => {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('k', k.toString());
  formData.append('tenant_id', 'user_001'); // Can be made dynamic later

  try {
    console.log(`[API] Sending search request: k=${k}, file=${imageFile.name}`);
    
    const response = await fetch(`${API_BASE_URL}/search`, {
      method: 'POST',
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      console.error('[API] Error response:', data);
      throw new Error(data.error || data.details || 'Search request failed');
    }

    console.log(`[API] Success: ${data.count} results in ${data.query_info?.processing_time_ms}ms`);
    return data;
    
  } catch (error) {
    console.error('[API] Request failed:', error);
    
    if (error.message.includes('fetch')) {
      throw new Error('Cannot connect to backend server. Make sure it is running on port 5000.');
    }
    
    throw error;
  }
};

/**
 * Check backend health status
 * @returns {Promise<Object>} Health status
 */
export const checkHealth = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return await response.json();
  } catch (error) {
    console.error('[API] Health check failed:', error);
    throw error;
  }
};
export default api;
