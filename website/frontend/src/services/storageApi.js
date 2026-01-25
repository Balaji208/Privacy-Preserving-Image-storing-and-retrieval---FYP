// frontend/src/services/storageApi.js
import api, { createFormDataRequest } from './api';

/**
 * Storage Service API
 * Handles image upload and indexing operations
 */

/**
 * Upload and index a single medical image
 * @param {File} file - Image file to upload
 * @param {Object} metadata - Image metadata
 * @returns {Promise<Object>} Upload result with image_id and processing details
 */
export const uploadImage = async (file, metadata = {}) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('tenant_id', metadata.tenant_id || 'hospital_001');

  // Add optional metadata fields
  if (metadata.patient_id) formData.append('patient_id', metadata.patient_id);
  if (metadata.study_type) formData.append('study_type', metadata.study_type);
  if (metadata.age) formData.append('age', metadata.age);
  if (metadata.diagnosis) formData.append('diagnosis', metadata.diagnosis);
  if (metadata.severity) formData.append('severity', metadata.severity);

  // Additional metadata as JSON
  const additionalMetadata = {
    age: metadata.age,
    diagnosis: metadata.diagnosis,
    severity: metadata.severity,
    notes: metadata.notes,
  };
  formData.append('metadata', JSON.stringify(additionalMetadata));

  try {
    const response = await createFormDataRequest('/storage/upload', formData, {
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        console.log(`Upload progress: ${percentCompleted}%`);
      },
    });

    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.message || error.message || 'Upload failed',
    };
  }
};

/**
 * Upload multiple images in batch
 * @param {Array<{file: File, metadata: Object}>} filesWithMetadata
 * @returns {Promise<Object>} Batch upload results
 */
export const uploadBatch = async (filesWithMetadata) => {
  const results = [];
  const errors = [];

  for (let i = 0; i < filesWithMetadata.length; i++) {
    const { file, metadata } = filesWithMetadata[i];
    const result = await uploadImage(file, metadata);

    if (result.success) {
      results.push({
        filename: file.name,
        ...result.data,
      });
    } else {
      errors.push({
        filename: file.name,
        error: result.error,
      });
    }
  }

  return {
    success: errors.length === 0,
    results,
    errors,
    totalUploaded: results.length,
    totalFailed: errors.length,
  };
};

/**
 * Get upload status
 * @param {string} imageId - Image ID to check status
 * @returns {Promise<Object>} Upload status details
 */
export const getUploadStatus = async (imageId) => {
  try {
    const response = await api.get(`/storage/status/${imageId}`);
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
 * Delete an uploaded image
 * @param {string} imageId - Image ID to delete
 * @param {string} tenantId - Tenant ID
 * @returns {Promise<Object>} Deletion result
 */
export const deleteImage = async (imageId, tenantId) => {
  try {
    const response = await api.delete(`/storage/delete/${imageId}`, {
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
 * Get storage statistics
 * @param {string} tenantId - Tenant ID
 * @returns {Promise<Object>} Storage statistics
 */
export const getStorageStats = async (tenantId) => {
  try {
    const response = await api.get('/storage/stats', {
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
  uploadImage,
  uploadBatch,
  getUploadStatus,
  deleteImage,
  getStorageStats,
};
