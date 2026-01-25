// frontend/src/components/dashboard/QuickActions.jsx
import React from 'react';
import PropTypes from 'prop-types';
import { useNavigate } from 'react-router-dom';
import { 
  Upload, 
  Search, 
  History, 
  Settings,
  FileText,
  BarChart3
} from 'lucide-react';

const QuickActions = ({ className = '' }) => {
  const navigate = useNavigate();

  const actions = [
    {
      id: 'upload',
      title: 'Upload Image',
      description: 'Add new medical images to the encrypted database',
      icon: Upload,
      color: 'blue',
      route: '/upload',
      primary: true,
    },
    {
      id: 'search',
      title: 'Search Similar',
      description: 'Find similar cases using FHE-powered search',
      icon: Search,
      color: 'teal',
      route: '/search',
      primary: true,
    },
    {
      id: 'history',
      title: 'View History',
      description: 'Browse past searches and uploads',
      icon: History,
      color: 'purple',
      route: '/history',
    },
    {
      id: 'reports',
      title: 'Generate Report',
      description: 'Create clinical comparison reports',
      icon: FileText,
      color: 'orange',
      route: '/reports',
    },
    {
      id: 'analytics',
      title: 'Analytics',
      description: 'View system performance metrics',
      icon: BarChart3,
      color: 'green',
      route: '/analytics',
    },
    {
      id: 'settings',
      title: 'Settings',
      description: 'Configure search parameters and preferences',
      icon: Settings,
      color: 'slate',
      route: '/settings',
    },
  ];

  const colorConfig = {
    blue: {
      bg: 'bg-blue-50 hover:bg-blue-100',
      icon: 'text-blue-600',
      border: 'border-blue-200',
      shadow: 'hover:shadow-blue-100',
    },
    teal: {
      bg: 'bg-teal-50 hover:bg-teal-100',
      icon: 'text-teal-600',
      border: 'border-teal-200',
      shadow: 'hover:shadow-teal-100',
    },
    purple: {
      bg: 'bg-purple-50 hover:bg-purple-100',
      icon: 'text-purple-600',
      border: 'border-purple-200',
      shadow: 'hover:shadow-purple-100',
    },
    orange: {
      bg: 'bg-orange-50 hover:bg-orange-100',
      icon: 'text-orange-600',
      border: 'border-orange-200',
      shadow: 'hover:shadow-orange-100',
    },
    green: {
      bg: 'bg-emerald-50 hover:bg-emerald-100',
      icon: 'text-emerald-600',
      border: 'border-emerald-200',
      shadow: 'hover:shadow-emerald-100',
    },
    slate: {
      bg: 'bg-slate-50 hover:bg-slate-100',
      icon: 'text-slate-600',
      border: 'border-slate-200',
      shadow: 'hover:shadow-slate-100',
    },
  };

  return (
    <div className={`bg-white rounded-xl border border-slate-200 p-6 shadow-sm ${className}`}>
      <h3 className="text-lg font-bold text-slate-800 mb-4">Quick Actions</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {actions.map((action) => {
          const Icon = action.icon;
          const colors = colorConfig[action.color];
          
          return (
            <button
              key={action.id}
              onClick={() => navigate(action.route)}
              className={`group relative p-4 rounded-xl border ${colors.border} ${colors.bg} transition-all duration-200 hover:shadow-lg ${colors.shadow} text-left ${
                action.primary ? 'md:col-span-1' : ''
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`w-10 h-10 rounded-lg bg-white border ${colors.border} flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform`}>
                  <Icon className={colors.icon} size={20} />
                </div>
                
                <div className="flex-1 min-w-0">
                  <h4 className={`text-sm font-bold ${colors.icon} mb-1`}>
                    {action.title}
                  </h4>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {action.description}
                  </p>
                </div>
              </div>
              
              {action.primary && (
                <div className="absolute top-2 right-2">
                  <span className={`text-[9px] uppercase font-bold ${colors.icon} bg-white px-2 py-0.5 rounded-full border ${colors.border}`}>
                    Primary
                  </span>
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};

QuickActions.propTypes = {
  className: PropTypes.string,
};

export default QuickActions;
