// frontend/src/hooks/useUpload.js
import { useState, useCallback } from 'react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useSettings } from '../context/SettingsContext';

export const useUpload = () => {
  const { tenant } = useAuth();
  const { settings } = useSettings();
  
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle'); // idle, uploading, encrypting, extracting, hashing, indexing, complete
  const [error, setError] = useState(null);
  const [uploadedImages, setUploadedImages] = useState([]);
  const [currentFile, setCurrentFile] = useState(0);
  const [totalFiles, setTotalFiles] = useState(0);

  /**
   * Simulate progress stages for better UX
   */
  const simulateProgress = (stage) => {
    const stages = {
      uploading: { start: 0, end: 20 },
      encrypting: { start: 20, end: 40 },
      extracting: { start: 40, end: 70 },
      hashing: { start: 70, end: 85 },
      indexing: { start: 85, end: 100 },
    };

    const stageProgress = stages[stage];
    if (!stageProgress) return;

    let current = stageProgress.start;
    const increment = (stageProgress.end - stageProgress.start) / 10;

    const interval = setInterval(() => {
      current += increment;
      if (current >= stageProgress.end) {
        clearInterval(interval);
        setProgress(stageProgress.end);
      } else {
        setProgress(current);
      }
    }, 200);

    return interval;
  };

  /**
   * Upload single image with metadata
   * @param {File} file - Image file to upload
   * @param {Object} metadata - Image metadata
   */
  const uploadSingle = useCallback(async (file, metadata = {}) => {
    if (!file) {
      setError('No file provided');
      return { success: false, error: 'No file provided' };
    }

    setUploading(true);
    setError(null);
    setProgress(0);
    setCurrentFile(1);
    setTotalFiles(1);

    try {
      // Stage 1: Uploading
      setStatus('uploading');
      const uploadInterval = simulateProgress('uploading');

      const formData = new FormData();
      formData.append('file', file);
      formData.append('tenant_id', tenant?.id || 'hospital_001');

      // Add metadata
      if (metadata.patient_id) formData.append('patient_id', metadata.patient_id);
      if (metadata.study_type) formData.append('study_type', metadata.study_type);
      if (metadata.age) formData.append('age', metadata.age);
      if (metadata.diagnosis) formData.append('diagnosis', metadata.diagnosis);
      if (metadata.severity) formData.append('severity', metadata.severity);
      if (metadata.notes) formData.append('notes', metadata.notes);

      // Additional metadata as JSON
      const additionalMetadata = {
        age: metadata.age,
        diagnosis: metadata.diagnosis,
        severity: metadata.severity,
        notes: metadata.notes,
      };
      formData.append('metadata', JSON.stringify(additionalMetadata));

      clearInterval(uploadInterval);

      // Make API call
      const { data } = await api.post('/storage/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 20) / progressEvent.total);
          setProgress(percentCompleted);
        },
      });

      // Stage 2: Encrypting
      setStatus('encrypting');
      await new Promise(resolve => setTimeout(resolve, 1000));
      setProgress(40);

      // Stage 3: Feature Extraction
      setStatus('extracting');
      await new Promise(resolve => setTimeout(resolve, 1500));
      setProgress(70);

      // Stage 4: Hashing
      setStatus('hashing');
      await new Promise(resolve => setTimeout(resolve, 800));
      setProgress(85);

      // Stage 5: Indexing
      setStatus('indexing');
      await new Promise(resolve => setTimeout(resolve, 500));
      setProgress(100);

      // Complete
      setStatus('complete');
      
      const uploadedImage = {
        image_id: data.image_id,
        blob_name: data.blob_name,
        processing_time: data.processing_time_ms,
        features_extracted: data.features_extracted,
        hash_generated: data.hash_generated,
        indexed: data.indexed,
        metadata: metadata,
        filename: file.name,
      };

      setUploadedImages([uploadedImage]);

      // Show notification if enabled
      if (settings.notifyOnUploadComplete && settings.enableNotifications) {
        // Trigger notification (would be implemented in a NotificationContext)
        console.log('Upload complete notification triggered');
      }

      return {
        success: true,
        data: uploadedImage,
      };
    } catch (err) {
      const errorMessage = err.response?.data?.message || err.message || 'Upload failed';
      setError(errorMessage);
      setStatus('idle');
      console.error('Upload error:', err);
      return {
        success: false,
        error: errorMessage,
      };
    } finally {
      setUploading(false);
    }
  }, [tenant, settings]);

  /**
   * Upload multiple images in batch
   * @param {Array<{file: File, metadata: Object}>} filesWithMetadata - Array of files with their metadata
   */
  const uploadBatch = useCallback(async (filesWithMetadata) => {
    if (!filesWithMetadata || filesWithMetadata.length === 0) {
      setError('No files provided');
      return { success: false, error: 'No files provided' };
    }

    const maxBatch = settings.maxBatchSize || 10;
    if (filesWithMetadata.length > maxBatch) {
      setError(`Maximum ${maxBatch} files allowed per batch`);
      return { success: false, error: `Maximum ${maxBatch} files allowed` };
    }

    setUploading(true);
    setError(null);
    setTotalFiles(filesWithMetadata.length);
    setUploadedImages([]);

    const results = [];
    const errors = [];

    for (let i = 0; i < filesWithMetadata.length; i++) {
      setCurrentFile(i + 1);
      setProgress(0);

      const { file, metadata } = filesWithMetadata[i];
      const result = await uploadSingle(file, metadata);

      if (result.success) {
        results.push(result.data);
      } else {
        errors.push({ filename: file.name, error: result.error });
      }

      // Small delay between uploads
      if (i < filesWithMetadata.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }

    setUploading(false);
    setStatus('complete');

    if (errors.length > 0) {
      const errorMsg = `${errors.length} of ${filesWithMetadata.length} uploads failed`;
      setError(errorMsg);
    }

    return {
      success: errors.length === 0,
      results,
      errors,
      totalUploaded: results.length,
      totalFailed: errors.length,
    };
  }, [settings, uploadSingle]);

  /**
   * Reset upload state
   */
  const reset = useCallback(() => {
    setUploading(false);
    setProgress(0);
    setStatus('idle');
    setError(null);
    setUploadedImages([]);
    setCurrentFile(0);
    setTotalFiles(0);
  }, []);

  /**
   * Cancel ongoing upload
   */
  const cancel = useCallback(() => {
    // In production, this would cancel the API request
    reset();
  }, [reset]);

  return {
    uploadSingle,
    uploadBatch,
    uploading,
    progress,
    status,
    error,
    uploadedImages,
    currentFile,
    totalFiles,
    reset,
    cancel,
  };
};

export default useUpload;
