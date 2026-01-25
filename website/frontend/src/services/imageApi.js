// frontend/src/services/imageApi.js
import api, { downloadFile } from './api';

/**
 * Image Retrieval Service API
 * Handles fetching and downloading encrypted medical images
 */

/**
 * Fetch full decrypted image by ID
 * @param {string} imageId - Image ID
 * @param {string} tenantId - Tenant ID
 * @returns {Promise<Object>} Image data with metadata
 */
export const getImage = async (imageId, tenantId) => {
  try {
    const response = await api.get(`/images/${imageId}`, {
      params: { tenant_id: tenantId },
    });

    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.message || error.message || 'Failed to fetch image',
    };
  }
};

/**
 * Fetch image thumbnail
 * @param {string} imageId - Image ID
 * @param {string} tenantId - Tenant ID
 * @returns {Promise<Object>} Thumbnail URL or blob
 */
export const getThumbnail = async (imageId, tenantId) => {
  try {
    const response = await api.get(`/images/${imageId}/thumbnail`, {
      params: { tenant_id: tenantId },
      responseType: 'blob',
    });

    // Create blob URL for image display
    const imageUrl = URL.createObjectURL(response.data);

    return {
      success: true,
      url: imageUrl,
      blob: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.message || error.message || 'Failed to fetch thumbnail',
    };
  }
};

/**
 * Download image file
 * @param {string} imageId - Image ID
 * @param {string} tenantId - Tenant ID
 * @param {string} filename - Desired filename for download
 * @returns {Promise<Object>} Download result
 */
export const downloadImage = async (imageId, tenantId, filename = 'medical_image.jpg') => {
  try {
    const result = await downloadFile(
      `/images/${imageId}/download`,
      filename,
      { tenant_id: tenantId }
    );
    return result;
  } catch (error) {
    return {
      success: false,
      error: error.message || 'Download failed',
    };
  }
};

/**
 * Get image metadata only (without image data)
 * @param {string} imageId - Image ID
 * @param {string} tenantId - Tenant ID
 * @returns {Promise<Object>} Image metadata
 */
export const getImageMetadata = async (imageId, tenantId) => {
  try {
    const response = await api.get(`/images/${imageId}/metadata`, {
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

/**
 * Update image metadata
 * @param {string} imageId - Image ID
 * @param {string} tenantId - Tenant ID
 * @param {Object} metadata - Updated metadata
 * @returns {Promise<Object>} Update result
 */
export const updateImageMetadata = async (imageId, tenantId, metadata) => {
  try {
    const response = await api.put(`/images/${imageId}/metadata`, {
      tenant_id: tenantId,
      metadata,
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
 * Get multiple images by IDs (batch fetch)
 * @param {Array<string>} imageIds - Array of image IDs
 * @param {string} tenantId - Tenant ID
 * @returns {Promise<Object>} Batch image data
 */
export const getImagesBatch = async (imageIds, tenantId) => {
  try {
    const response = await api.post('/images/batch', {
      image_ids: imageIds,
      tenant_id: tenantId,
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
 * Get upload history for images
 * @param {string} tenantId - Tenant ID
 * @param {Object} options - Filter and pagination options
 * @returns {Promise<Object>} Upload history
 */
export const getUploadHistory = async (tenantId, options = {}) => {
  try {
    const response = await api.get('/history/uploads', {
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
 * Get image by patient ID
 * @param {string} patientId - Patient ID
 * @param {string} tenantId - Tenant ID
 * @returns {Promise<Object>} Patient's images
 */
export const getImagesByPatient = async (patientId, tenantId) => {
  try {
    const response = await api.get('/images/patient', {
      params: {
        patient_id: patientId,
        tenant_id: tenantId,
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
 * Get all images by study type
 * @param {string} studyType - Study type filter
 * @param {string} tenantId - Tenant ID
 * @returns {Promise<Object>} Filtered images
 */
export const getImagesByStudyType = async (studyType, tenantId) => {
  try {
    const response = await api.get('/images/study-type', {
      params: {
        study_type: studyType,
        tenant_id: tenantId,
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

export default {
  getImage,
  getThumbnail,
  downloadImage,
  getImageMetadata,
  updateImageMetadata,
  getImagesBatch,
  getUploadHistory,
  getImagesByPatient,
  getImagesByStudyType,
};
