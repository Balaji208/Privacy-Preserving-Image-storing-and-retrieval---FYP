// frontend/src/components/common/Spinner.jsx
import React from 'react';
import PropTypes from 'prop-types';
import { Loader2 } from 'lucide-react';

const Spinner = ({ 
  size = 'md', 
  color = 'blue', 
  text,
  fullScreen = false,
  className = '' 
}) => {
  const sizeStyles = {
    sm: 20,
    md: 32,
    lg: 48,
    xl: 64,
  };

  const colorStyles = {
    blue: 'text-blue-600',
    teal: 'text-teal-600',
    slate: 'text-slate-600',
    white: 'text-white',
  };

  const spinner = (
    <div className={`flex flex-col items-center justify-center gap-3 ${className}`}>
      <Loader2 
        className={`animate-spin ${colorStyles[color]}`} 
        size={sizeStyles[size]} 
      />
      {text && (
        <p className={`text-sm font-medium ${colorStyles[color]}`}>{text}</p>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 z-50 bg-white/80 backdrop-blur-sm flex items-center justify-center">
        {spinner}
      </div>
    );
  }

  return spinner;
};

Spinner.propTypes = {
  size: PropTypes.oneOf(['sm', 'md', 'lg', 'xl']),
  color: PropTypes.oneOf(['blue', 'teal', 'slate', 'white']),
  text: PropTypes.string,
  fullScreen: PropTypes.bool,
  className: PropTypes.string,
};

export default Spinner;
