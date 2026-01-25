// frontend/src/components/upload/MetadataForm.jsx
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { 
  User, 
  Calendar, 
  Activity, 
  FileText,
  AlertCircle,
  Stethoscope,
  Layers
} from 'lucide-react';
import Input from '../common/Input';

const MetadataForm = ({ metadata, onChange, disabled = false }) => {
  const [errors, setErrors] = useState({});

  const studyTypes = [
    { value: '', label: 'Select Study Type' },
    { value: 'brain_mri', label: 'Brain MRI' },
    { value: 'chest_xray', label: 'Chest X-Ray' },
    { value: 'lung_ct', label: 'Lung CT Scan' },
    { value: 'abdominal_ct', label: 'Abdominal CT' },
    { value: 'spine_mri', label: 'Spine MRI' },
    { value: 'cardiac_mri', label: 'Cardiac MRI' },
  ];

  const severityLevels = [
    { value: '', label: 'Not Specified' },
    { value: 'mild', label: 'Mild' },
    { value: 'moderate', label: 'Moderate' },
    { value: 'severe', label: 'Severe' },
    { value: 'critical', label: 'Critical' },
  ];

  const validateField = (name, value) => {
    const newErrors = { ...errors };

    switch (name) {
      case 'patient_id':
        if (value && !/^[A-Z0-9]{6,12}$/i.test(value)) {
          newErrors.patient_id = 'Patient ID must be 6-12 alphanumeric characters';
        } else {
          delete newErrors.patient_id;
        }
        break;
      case 'age':
        if (value && (isNaN(value) || value < 0 || value > 150)) {
          newErrors.age = 'Age must be between 0 and 150';
        } else {
          delete newErrors.age;
        }
        break;
      default:
        break;
    }

    setErrors(newErrors);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    onChange({ ...metadata, [name]: value });
    validateField(name, value);
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-bold text-slate-800 mb-2">Image Metadata</h3>
        <p className="text-sm text-slate-600">
          Provide additional information to improve searchability and clinical context
        </p>
      </div>

      {/* Patient Information Section */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <User className="text-blue-600" size={18} />
          <h4 className="text-sm font-bold text-slate-800">Patient Information</h4>
        </div>

        <div className="space-y-4">
          <Input
            label="Patient ID"
            name="patient_id"
            value={metadata.patient_id || ''}
            onChange={handleChange}
            disabled={disabled}
            placeholder="e.g., PAT123456"
            icon={User}
            error={errors.patient_id}
            helperText="Optional: Alphanumeric ID (6-12 characters)"
          />

          <Input
            label="Age"
            name="age"
            type="number"
            value={metadata.age || ''}
            onChange={handleChange}
            disabled={disabled}
            placeholder="e.g., 45"
            icon={Calendar}
            error={errors.age}
            helperText="Patient age in years"
          />
        </div>
      </div>

      {/* Clinical Information Section */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="text-teal-600" size={18} />
          <h4 className="text-sm font-bold text-slate-800">Clinical Information</h4>
        </div>

        <div className="space-y-4">
          {/* Study Type */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              <div className="flex items-center gap-2">
                <Layers size={16} />
                Study Type
                <span className="text-red-500">*</span>
              </div>
            </label>
            <select
              name="study_type"
              value={metadata.study_type || ''}
              onChange={handleChange}
              disabled={disabled}
              className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-lg text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              required
            >
              {studyTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
            {!metadata.study_type && (
              <p className="text-xs text-red-600 mt-1.5 flex items-center gap-1">
                <AlertCircle size={12} />
                Study type is required for proper indexing
              </p>
            )}
          </div>

          {/* Diagnosis */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              <div className="flex items-center gap-2">
                <Stethoscope size={16} />
                Diagnosis
              </div>
            </label>
            <input
              type="text"
              name="diagnosis"
              value={metadata.diagnosis || ''}
              onChange={handleChange}
              disabled={disabled}
              placeholder="e.g., Alzheimer's Disease, Stage 2"
              className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            />
            <p className="text-xs text-slate-500 mt-1.5">
              Primary diagnosis or clinical finding
            </p>
          </div>

          {/* Severity */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Severity Level
            </label>
            <select
              name="severity"
              value={metadata.severity || ''}
              onChange={handleChange}
              disabled={disabled}
              className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-lg text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {severityLevels.map((level) => (
                <option key={level.value} value={level.value}>
                  {level.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Additional Notes Section */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="text-purple-600" size={18} />
          <h4 className="text-sm font-bold text-slate-800">Additional Notes</h4>
        </div>

        <textarea
          name="notes"
          value={metadata.notes || ''}
          onChange={handleChange}
          disabled={disabled}
          placeholder="Any additional clinical notes or observations..."
          rows={4}
          className="w-full px-4 py-3 bg-white border border-slate-300 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 resize-none"
        />
        <p className="text-xs text-slate-500 mt-1.5">
          Optional: Include any relevant clinical context or observations
        </p>
      </div>

      {/* Privacy Notice */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="text-blue-600 flex-shrink-0 mt-0.5" size={18} />
          <div className="text-xs text-blue-800">
            <p className="font-semibold mb-1">Privacy & Compliance:</p>
            <ul className="list-disc list-inside space-y-0.5 text-blue-700">
              <li>All metadata is encrypted alongside the image</li>
              <li>Patient identifiers are anonymized in search results</li>
              <li>Data complies with HIPAA and GDPR requirements</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

MetadataForm.propTypes = {
  metadata: PropTypes.shape({
    patient_id: PropTypes.string,
    age: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    study_type: PropTypes.string,
    diagnosis: PropTypes.string,
    severity: PropTypes.string,
    notes: PropTypes.string,
  }).isRequired,
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
};

export default MetadataForm;
