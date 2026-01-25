// frontend/src/context/SettingsContext.js
import React, { createContext, useContext, useState, useEffect } from 'react';
import PropTypes from 'prop-types';

const SettingsContext = createContext(null);

export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
};

const defaultSettings = {
  // Display Settings
  theme: 'light', // 'light' | 'dark'
  language: 'en',
  dateFormat: 'MM/DD/YYYY',
  timeFormat: '12h', // '12h' | '24h'

  // Search Settings
  defaultTopK: 5,
  defaultMinSimilarity: 0.7,
  defaultHammingThreshold: 66,
  enableFHE: true,
  autoRefreshResults: false,

  // Upload Settings
  defaultStudyType: '',
  autoExtractMetadata: true,
  enableBatchUpload: true,
  maxBatchSize: 10,

  // Display Preferences
  resultsView: 'grid', // 'grid' | 'list'
  thumbnailSize: 'medium', // 'small' | 'medium' | 'large'
  showConfidenceBadges: true,
  showHammingDistance: true,

  // Privacy & Security
  encryptionEnabled: true,
  requireEncryption: true,
  sessionTimeout: 30, // minutes
  autoLogout: true,

  // Notifications
  enableNotifications: true,
  notifyOnUploadComplete: true,
  notifyOnSearchComplete: false,
  notificationPosition: 'top-right', // 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left'

  // Performance
  enableImageCompression: true,
  compressionQuality: 0.8,
  enableLazyLoading: true,
  enableCache: true,
  cacheTimeout: 3600, // seconds
};

export const SettingsProvider = ({ children }) => {
  const [settings, setSettings] = useState(defaultSettings);
  const [loading, setLoading] = useState(true);

  // Load settings from localStorage on mount
  useEffect(() => {
    const loadSettings = () => {
      try {
        const storedSettings = localStorage.getItem('userSettings');
        if (storedSettings) {
          const parsed = JSON.parse(storedSettings);
          setSettings({ ...defaultSettings, ...parsed });
        }
      } catch (error) {
        console.error('Failed to load settings:', error);
      } finally {
        setLoading(false);
      }
    };

    loadSettings();
  }, []);

  // Save settings to localStorage whenever they change
  useEffect(() => {
    if (!loading) {
      try {
        localStorage.setItem('userSettings', JSON.stringify(settings));
      } catch (error) {
        console.error('Failed to save settings:', error);
      }
    }
  }, [settings, loading]);

  // Update a single setting
  const updateSetting = (key, value) => {
    setSettings(prev => ({
      ...prev,
      [key]: value,
    }));
  };

  // Update multiple settings at once
  const updateSettings = (updates) => {
    setSettings(prev => ({
      ...prev,
      ...updates,
    }));
  };

  // Reset to default settings
  const resetSettings = () => {
    setSettings(defaultSettings);
    localStorage.removeItem('userSettings');
  };

  // Reset specific category
  const resetCategory = (category) => {
    const categoryDefaults = {};
    const categoryKeys = {
      display: ['theme', 'language', 'dateFormat', 'timeFormat'],
      search: ['defaultTopK', 'defaultMinSimilarity', 'defaultHammingThreshold', 'enableFHE', 'autoRefreshResults'],
      upload: ['defaultStudyType', 'autoExtractMetadata', 'enableBatchUpload', 'maxBatchSize'],
      privacy: ['encryptionEnabled', 'requireEncryption', 'sessionTimeout', 'autoLogout'],
      notifications: ['enableNotifications', 'notifyOnUploadComplete', 'notifyOnSearchComplete', 'notificationPosition'],
      performance: ['enableImageCompression', 'compressionQuality', 'enableLazyLoading', 'enableCache', 'cacheTimeout'],
    };

    if (categoryKeys[category]) {
      categoryKeys[category].forEach(key => {
        categoryDefaults[key] = defaultSettings[key];
      });
      updateSettings(categoryDefaults);
    }
  };

  // Export settings as JSON
  const exportSettings = () => {
    const dataStr = JSON.stringify(settings, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `medsearch-settings-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Import settings from JSON
  const importSettings = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const imported = JSON.parse(e.target.result);
          // Validate imported settings
          const validSettings = {};
          Object.keys(defaultSettings).forEach(key => {
            if (Object.prototype.hasOwnProperty.call(imported, key)) {
              validSettings[key] = imported[key];
            }
          });
          updateSettings(validSettings);
          resolve(true);
        } catch (error) {
          reject(new Error('Invalid settings file'));
        }
      };
      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    });
  };

  // Get search parameters from settings
  const getSearchDefaults = () => ({
    topK: settings.defaultTopK,
    minSimilarity: settings.defaultMinSimilarity,
    hammingThreshold: settings.defaultHammingThreshold,
    useFHE: settings.enableFHE,
  });

  // Get upload parameters from settings
  const getUploadDefaults = () => ({
    studyType: settings.defaultStudyType,
    autoExtractMetadata: settings.autoExtractMetadata,
    maxBatchSize: settings.maxBatchSize,
  });

  // Apply theme
  useEffect(() => {
    if (settings.theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [settings.theme]);

  const value = {
    settings,
    loading,
    updateSetting,
    updateSettings,
    resetSettings,
    resetCategory,
    exportSettings,
    importSettings,
    getSearchDefaults,
    getUploadDefaults,
  };

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
};

SettingsProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export default SettingsContext;
