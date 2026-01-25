// frontend/src/pages/Settings.jsx
import React, { useState } from 'react';
import { useSettings } from '../context/SettingsContext';
import { useAuth } from '../context/AuthContext';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import Card from '../components/common/Card';
import { 
  Save, 
  RotateCw, 
  Download, 
  Upload,
  User,
  Search,
  Upload as UploadIcon,
  Bell,
  Shield,
  Zap,
  Moon,
  Sun
} from 'lucide-react';
import { useToast } from '../components/common/Toast';

const Settings = () => {
  const { settings, updateSetting, updateSettings, resetSettings, resetCategory, exportSettings, importSettings } = useSettings();
  const { user, tenant } = useAuth();
  const { showToast, ToastContainer } = useToast();
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    // Simulate save delay
    await new Promise(resolve => setTimeout(resolve, 500));
    setSaving(false);
    showToast('Settings saved successfully', 'success');
  };

  const handleReset = (category) => {
    if (window.confirm(`Reset ${category} settings to defaults?`)) {
      resetCategory(category);
      showToast(`${category} settings reset to defaults`, 'info');
    }
  };

  const handleResetAll = () => {
    if (window.confirm('Reset all settings to defaults? This cannot be undone.')) {
      resetSettings();
      showToast('All settings reset to defaults', 'info');
    }
  };

  const handleExport = () => {
    exportSettings();
    showToast('Settings exported successfully', 'success');
  };

  const handleImport = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    try {
      await importSettings(file);
      showToast('Settings imported successfully', 'success');
    } catch (err) {
      showToast(err.message || 'Failed to import settings', 'error');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-800 mb-2">Settings</h1>
            <p className="text-slate-600">
              Configure your preferences and system settings
            </p>
          </div>
          <div className="flex gap-3">
            <Button onClick={handleExport} icon={Download} variant="ghost" size="sm">
              Export
            </Button>
            <label>
              <input
                type="file"
                accept=".json"
                onChange={handleImport}
                className="hidden"
              />
              <Button as="span" icon={Upload} variant="ghost" size="sm">
                Import
              </Button>
            </label>
            <Button onClick={handleResetAll} icon={RotateCw} variant="ghost" size="sm">
              Reset All
            </Button>
          </div>
        </div>

        {/* Account Settings */}
        <Card title="Account Information" icon={User}>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Name"
              value={user?.name || ''}
              disabled
            />
            <Input
              label="Email"
              value={user?.email || ''}
              disabled
            />
            <Input
              label="Hospital/Clinic"
              value={tenant?.name || ''}
              disabled
            />
            <Input
              label="Tenant ID"
              value={tenant?.id || ''}
              disabled
            />
          </div>
        </Card>

        {/* Display Settings */}
        <Card title="Display Settings">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-800">Theme</p>
                <p className="text-sm text-slate-500">Choose your preferred theme</p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => updateSetting('theme', 'light')}
                  className={`p-3 rounded-lg border-2 transition-all ${
                    settings.theme === 'light'
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <Sun size={20} className={settings.theme === 'light' ? 'text-blue-600' : 'text-slate-600'} />
                </button>
                <button
                  onClick={() => updateSetting('theme', 'dark')}
                  className={`p-3 rounded-lg border-2 transition-all ${
                    settings.theme === 'dark'
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <Moon size={20} className={settings.theme === 'dark' ? 'text-blue-600' : 'text-slate-600'} />
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-800">Results View</p>
                <p className="text-sm text-slate-500">Default view for search results</p>
              </div>
              <select
                value={settings.resultsView}
                onChange={(e) => updateSetting('resultsView', e.target.value)}
                className="px-4 py-2 border border-slate-300 rounded-lg"
              >
                <option value="grid">Grid View</option>
                <option value="list">List View</option>
              </select>
            </div>
          </div>
        </Card>

        {/* Search Settings */}
        <Card title="Search Settings" icon={Search}>
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Default Top-K Results
              </label>
              <input
                type="range"
                min="1"
                max="20"
                value={settings.defaultTopK}
                onChange={(e) => updateSetting('defaultTopK', parseInt(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-sm text-slate-600 mt-1">
                <span>1</span>
                <span className="font-bold text-blue-600">{settings.defaultTopK}</span>
                <span>20</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Default Similarity Threshold
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={settings.defaultMinSimilarity * 100}
                onChange={(e) => updateSetting('defaultMinSimilarity', parseFloat(e.target.value) / 100)}
                className="w-full"
              />
              <div className="flex justify-between text-sm text-slate-600 mt-1">
                <span>0%</span>
                <span className="font-bold text-blue-600">{Math.round(settings.defaultMinSimilarity * 100)}%</span>
                <span>100%</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <div>
                <p className="font-semibold text-slate-800">Enable FHE Encryption</p>
                <p className="text-sm text-slate-500">Use homomorphic encryption for searches</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.enableFHE}
                  onChange={(e) => updateSetting('enableFHE', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-300 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500"></div>
              </label>
            </div>

            <Button onClick={() => handleReset('search')} variant="ghost" size="sm">
              Reset Search Defaults
            </Button>
          </div>
        </Card>

        {/* Upload Settings */}
        <Card title="Upload Settings" icon={UploadIcon}>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <div>
                <p className="font-semibold text-slate-800">Enable Batch Upload</p>
                <p className="text-sm text-slate-500">Upload multiple images at once</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.enableBatchUpload}
                  onChange={(e) => updateSetting('enableBatchUpload', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-300 rounded-full peer peer-checked:bg-blue-600 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
              </label>
            </div>

            <Input
              label="Maximum Batch Size"
              type="number"
              value={settings.maxBatchSize}
              onChange={(e) => updateSetting('maxBatchSize', parseInt(e.target.value))}
              min="1"
              max="50"
            />

            <Button onClick={() => handleReset('upload')} variant="ghost" size="sm">
              Reset Upload Defaults
            </Button>
          </div>
        </Card>

        {/* Notifications */}
        <Card title="Notifications" icon={Bell}>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <div>
                <p className="font-semibold text-slate-800">Enable Notifications</p>
                <p className="text-sm text-slate-500">Show system notifications</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.enableNotifications}
                  onChange={(e) => updateSetting('enableNotifications', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-300 rounded-full peer peer-checked:bg-blue-600 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
              </label>
            </div>

            {settings.enableNotifications && (
              <>
                <div className="flex items-center justify-between pl-4">
                  <span className="text-sm text-slate-700">Notify on upload complete</span>
                  <input
                    type="checkbox"
                    checked={settings.notifyOnUploadComplete}
                    onChange={(e) => updateSetting('notifyOnUploadComplete', e.target.checked)}
                    className="rounded"
                  />
                </div>
                <div className="flex items-center justify-between pl-4">
                  <span className="text-sm text-slate-700">Notify on search complete</span>
                  <input
                    type="checkbox"
                    checked={settings.notifyOnSearchComplete}
                    onChange={(e) => updateSetting('notifyOnSearchComplete', e.target.checked)}
                    className="rounded"
                  />
                </div>
              </>
            )}
          </div>
        </Card>

        {/* Privacy & Security */}
        <Card title="Privacy & Security" icon={Shield}>
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
              <Shield className="text-emerald-600" size={24} />
              <div>
                <p className="font-semibold text-emerald-900">Encryption Status: Active</p>
                <p className="text-sm text-emerald-700">All data is encrypted using FHE and HSM</p>
              </div>
            </div>

            <Input
              label="Session Timeout (minutes)"
              type="number"
              value={settings.sessionTimeout}
              onChange={(e) => updateSetting('sessionTimeout', parseInt(e.target.value))}
              min="5"
              max="120"
            />
          </div>
        </Card>

        {/* Performance */}
        <Card title="Performance" icon={Zap}>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <div>
                <p className="font-semibold text-slate-800">Enable Cache</p>
                <p className="text-sm text-slate-500">Cache images for faster loading</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.enableCache}
                  onChange={(e) => updateSetting('enableCache', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-300 rounded-full peer peer-checked:bg-blue-600 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
              </label>
            </div>
          </div>
        </Card>

        {/* Save Button */}
        <div className="flex justify-end gap-3">
          <Button onClick={handleSave} loading={saving} icon={Save} variant="primary" size="lg">
            Save Settings
          </Button>
        </div>
      </div>

      <ToastContainer />
    </div>
  );
};

export default Settings;
