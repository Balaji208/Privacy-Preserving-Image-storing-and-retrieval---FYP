// frontend/src/components/common/Card.jsx
import React from 'react';
import PropTypes from 'prop-types';

const Card = ({ 
  children, 
  title, 
  subtitle,
  icon: Icon,
  className = '',
  hoverable = false,
  padding = 'md',
  ...props 
}) => {
  const paddingStyles = {
    none: '',
    sm: 'p-3',
    md: 'p-6',
    lg: 'p-8',
  };

  const hoverStyles = hoverable 
    ? 'hover:shadow-lg hover:-translate-y-0.5 cursor-pointer' 
    : '';

  return (
    <div 
      className={`bg-white rounded-xl border border-slate-200 shadow-sm transition-all duration-200 ${hoverStyles} ${paddingStyles[padding]} ${className}`}
      {...props}
    >
      {(title || Icon) && (
        <div className="flex items-start gap-3 mb-4">
          {Icon && (
            <div className="flex-shrink-0 w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center">
              <Icon className="text-blue-600" size={20} />
            </div>
          )}
          <div className="flex-1">
            {title && (
              <h3 className="text-lg font-bold text-slate-800">{title}</h3>
            )}
            {subtitle && (
              <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>
            )}
          </div>
        </div>
      )}
      <div>{children}</div>
    </div>
  );
};

Card.propTypes = {
  children: PropTypes.node.isRequired,
  title: PropTypes.string,
  subtitle: PropTypes.string,
  icon: PropTypes.elementType,
  className: PropTypes.string,
  hoverable: PropTypes.bool,
  padding: PropTypes.oneOf(['none', 'sm', 'md', 'lg']),
};

export default Card;
