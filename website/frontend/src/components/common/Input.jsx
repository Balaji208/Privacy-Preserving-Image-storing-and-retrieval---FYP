// frontend/src/components/common/Input.jsx
import React from 'react';
import PropTypes from 'prop-types';

const Input = ({ 
  label, 
  error, 
  helperText,
  icon: Icon,
  type = 'text',
  className = '',
  containerClassName = '',
  required = false,
  ...props 
}) => {
  const inputStyles = error
    ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
    : 'border-slate-300 focus:border-blue-500 focus:ring-blue-500';

  return (
    <div className={`w-full ${containerClassName}`}>
      {label && (
        <label className="block text-sm font-semibold text-slate-700 mb-2">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      <div className="relative">
        {Icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
            <Icon size={18} />
          </div>
        )}
        <input
          type={type}
          className={`w-full px-4 py-2.5 ${Icon ? 'pl-10' : ''} bg-white border rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 transition-colors ${inputStyles} ${className}`}
          {...props}
        />
      </div>
      {error && (
        <p className="text-sm text-red-600 mt-1.5 flex items-center gap-1">
          <span className="font-medium">⚠</span> {error}
        </p>
      )}
      {helperText && !error && (
        <p className="text-sm text-slate-500 mt-1.5">{helperText}</p>
      )}
    </div>
  );
};

Input.propTypes = {
  label: PropTypes.string,
  error: PropTypes.string,
  helperText: PropTypes.string,
  icon: PropTypes.elementType,
  type: PropTypes.string,
  className: PropTypes.string,
  containerClassName: PropTypes.string,
  required: PropTypes.bool,
};

export default Input;
