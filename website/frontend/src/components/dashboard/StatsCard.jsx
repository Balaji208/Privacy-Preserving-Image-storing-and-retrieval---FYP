// frontend/src/components/dashboard/StatsCard.jsx
import React from 'react';
import PropTypes from 'prop-types';
import { 
  Activity, 
  Clock, 
  Database, 
  Shield, 
  Image, 
  Search,
  TrendingUp,
  Users
} from 'lucide-react';

const StatsCard = ({ 
  title, 
  value, 
  icon, 
  color = 'blue', 
  trend,
  subtitle,
  loading = false 
}) => {
  // Icon mapping
  const iconMap = {
    pulse: Activity,
    clock: Clock,
    database: Database,
    shield: Shield,
    image: Image,
    search: Search,
    trending: TrendingUp,
    users: Users,
  };

  const Icon = iconMap[icon] || Activity;

  // Color configurations
  const colorConfig = {
    blue: {
      bg: 'bg-blue-50',
      icon: 'text-blue-600',
      border: 'border-blue-100',
      trend: 'text-blue-600',
    },
    teal: {
      bg: 'bg-teal-50',
      icon: 'text-teal-600',
      border: 'border-teal-100',
      trend: 'text-teal-600',
    },
    green: {
      bg: 'bg-emerald-50',
      icon: 'text-emerald-600',
      border: 'border-emerald-100',
      trend: 'text-emerald-600',
    },
    purple: {
      bg: 'bg-purple-50',
      icon: 'text-purple-600',
      border: 'border-purple-100',
      trend: 'text-purple-600',
    },
    orange: {
      bg: 'bg-orange-50',
      icon: 'text-orange-600',
      border: 'border-orange-100',
      trend: 'text-orange-600',
    },
  };

  const colors = colorConfig[color];

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm animate-pulse">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="h-4 bg-slate-200 rounded w-24 mb-3"></div>
            <div className="h-8 bg-slate-200 rounded w-32"></div>
          </div>
          <div className={`w-12 h-12 ${colors.bg} rounded-lg`}></div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-xl border ${colors.border} p-6 shadow-sm hover:shadow-md transition-all duration-200`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-slate-600 mb-1">{title}</p>
          <p className="text-3xl font-bold text-slate-800 mb-2">{value}</p>
          
          {subtitle && (
            <p className="text-xs text-slate-500">{subtitle}</p>
          )}
          
          {trend && (
            <div className={`flex items-center gap-1 text-sm font-semibold ${colors.trend} mt-2`}>
              <TrendingUp size={14} />
              <span>{trend}</span>
            </div>
          )}
        </div>
        
        <div className={`w-12 h-12 ${colors.bg} rounded-lg flex items-center justify-center flex-shrink-0`}>
          <Icon className={colors.icon} size={24} />
        </div>
      </div>
    </div>
  );
};

StatsCard.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  icon: PropTypes.oneOf(['pulse', 'clock', 'database', 'shield', 'image', 'search', 'trending', 'users']),
  color: PropTypes.oneOf(['blue', 'teal', 'green', 'purple', 'orange']),
  trend: PropTypes.string,
  subtitle: PropTypes.string,
  loading: PropTypes.bool,
};

export default StatsCard;
