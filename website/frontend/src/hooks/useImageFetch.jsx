// frontend/src/hooks/useImageFetch.js
import { useState, useCallback, useEffect } from 'react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useSettings } from '../context/SettingsContext';

export const useImageFetch = (imageId = null) => {
  const { tenant } = useAuth();
  const { settings } = useSettings();
  
  const [loading, setLoading] = useState(false);
  const [imageData, setImageData] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [error, setError] = useState(null);
  const [cached, setCached] = useState(false);

  // Cache management
  const CACHE_PREFIX = 'img_cache_';
  const CACHE_TIMEOUT = settings.cacheTimeout * 1000 || 3600000; // Default 1 hour

  /**
   * Check if cached data is still valid
   */
  const isCacheValid = useCallback((cacheData) => {
    if (!cacheData || !cacheData.timestamp) return false;
    const now = Date.now();
    return (now - cacheData.timestamp) < CACHE_TIMEOUT;
  }, [CACHE_TIMEOUT]);

  /**
   * Get image from cache
   */
  const getFromCache = useCallback((imgId) => {
    if (!settings.enableCache) return null;

    try {
      const cacheKey = `${CACHE_PREFIX}${imgId}`;
      const cached = localStorage.getItem(cacheKey);
      if (!cached) return null;

      const parsed = JSON.parse(cached);
      if (isCacheValid(parsed)) {
        return parsed;
      } else {
        // Remove expired cache
        localStorage.removeItem(cacheKey);
        return null;
      }
    } catch (err) {
      console.error('Cache read error:', err);
      return null;
    }
  }, [settings.enableCache, isCacheValid]);

  /**
   * Save image to cache
   */
  const saveToCache = useCallback((imgId, data) => {
    if (!settings.enableCache) return;

    try {
      const cacheKey = `${CACHE_PREFIX}${imgId}`;
      const cacheData = {
        ...data,
        timestamp: Date.now(),
      };
      localStorage.setItem(cacheKey, JSON.stringify(cacheData));
    } catch (err) {
      // Handle quota exceeded or other storage errors
      console.error('Cache write error:', err);
      // Clear old cache entries if storage is full
      clearOldCache();
    }
  }, [settings.enableCache]);

  /**
   * Clear old cache entries
   */
  const clearOldCache = useCallback(() => {
    try {
      const keys = Object.keys(localStorage);
      keys.forEach(key => {
        if (key.startsWith(CACHE_PREFIX)) {
          const cached = localStorage.getItem(key);
          if (cached) {
            const parsed = JSON.parse(cached);
            if (!isCacheValid(parsed)) {
              localStorage.removeItem(key);
            }
          }
        }
      });
    } catch (err) {
      console.error('Cache cleanup error:', err);
    }
  }, [isCacheValid]);

  /**
   * Fetch full image by ID
   * @param {string} imgId - Image ID to fetch
   */
  const fetchImage = useCallback(async (imgId) => {
    if (!imgId) {
      setError('No image ID provided');
      return null;
    }

    // Check cache first
    const cachedData = getFromCache(imgId);
    if (cachedData) {
      setImageData(cachedData.imageData);
      setMetadata(cachedData.metadata);
      setCached(true);
      return cachedData;
    }

    setLoading(true);
    setError(null);
    setCached(false);

    try {
      const { data } = await api.get(`/images/${imgId}`, {
        params: { tenant_id: tenant?.id || 'hospital_001' },
      });

      const result = {
        imageData: data.image_data,
        metadata: data.metadata,
        contentType: data.content_type,
        imageId: data.image_id,
      };

      setImageData(result.imageData);
      setMetadata(result.metadata);

      // Save to cache
      saveToCache(imgId, result);

      return result;
    } catch (err) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to fetch image';
      setError(errorMessage);
      console.error('Image fetch error:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [tenant, getFromCache, saveToCache]);

  /**
   * Fetch image thumbnail
   * @param {string} imgId - Image ID to fetch
   */
  const fetchThumbnail = useCallback(async (imgId) => {
    if (!imgId) {
      setError('No image ID provided');
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      const { data } = await api.get(`/images/${imgId}/thumbnail`, {
        params: { tenant_id: tenant?.id || 'hospital_001' },
        responseType: 'blob',
      });

      const url = URL.createObjectURL(data);
      return url;
    } catch (err) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to fetch thumbnail';
      setError(errorMessage);
      console.error('Thumbnail fetch error:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [tenant]);

  /**
   * Download image file
   * @param {string} imgId - Image ID to download
   * @param {string} filename - Filename for download
   */
  const downloadImage = useCallback(async (imgId, filename = 'medical_image.jpg') => {
    const result = await fetchImage(imgId);
    if (!result) return false;

    try {
      // Convert base64 to blob
      const byteCharacters = atob(result.imageData);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: result.contentType });

      // Create download link
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);

      return true;
    } catch (err) {
      console.error('Download error:', err);
      setError('Failed to download image');
      return false;
    }
  }, [fetchImage]);

  /**
   * Clear cache for specific image
   */
  const clearCache = useCallback((imgId) => {
    if (imgId) {
      localStorage.removeItem(`${CACHE_PREFIX}${imgId}`);
    } else {
      // Clear all image cache
      clearOldCache();
    }
  }, [clearOldCache]);

  // Auto-fetch if imageId is provided
  useEffect(() => {
    if (imageId) {
      fetchImage(imageId);
    }
  }, [imageId]); // Don't include fetchImage to avoid infinite loop

  return {
    fetchImage,
    fetchThumbnail,
    downloadImage,
    loading,
    imageData,
    metadata,
    error,
    cached,
    clearCache,
  };
};

export default useImageFetch;
