// frontend/src/components/dashboard/ActivityFeed.jsx
import React from 'react';
import PropTypes from 'prop-types';
import { 
  Upload, 
  Search, 
  Image as ImageIcon, 
  CheckCircle,
  Clock
} from 'lucide-react';

const ActivityFeed = ({ activities = [], loading = false, maxItems = 10 }) => {
  const getActivityIcon = (type) => {
    const icons = {
      upload: Upload,
      search: Search,
      image: ImageIcon,
      success: CheckCircle,
    };
    return icons[type] || Clock;
  };

  const getActivityColor = (type) => {
    const colors = {
      upload: 'bg-blue-50 text-blue-600 border-blue-100',
      search: 'bg-teal-50 text-teal-600 border-teal-100',
      image: 'bg-purple-50 text-purple-600 border-purple-100',
      success: 'bg-emerald-50 text-emerald-600 border-emerald-100',
    };
    return colors[type] || 'bg-slate-50 text-slate-600 border-slate-100';
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <h3 className="text-lg font-bold text-slate-800 mb-4">Recent Activity</h3>
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-start gap-3 animate-pulse">
              <div className="w-10 h-10 bg-slate-200 rounded-lg"></div>
              <div className="flex-1">
                <div className="h-4 bg-slate-200 rounded w-3/4 mb-2"></div>
                <div className="h-3 bg-slate-200 rounded w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-slate-800">Recent Activity</h3>
        <span className="text-xs text-slate-500 font-medium">Last 24 hours</span>
      </div>
      
      {activities.length === 0 ? (
        <div className="text-center py-8">
          <Clock className="mx-auto text-slate-300 mb-3" size={48} />
          <p className="text-slate-500 text-sm">No recent activity</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {activities.slice(0, maxItems).map((activity, index) => {
            const Icon = getActivityIcon(activity.type);
            const colorClass = getActivityColor(activity.type);
            
            return (
              <div 
                key={activity.id || index} 
                className="flex items-start gap-3 p-3 rounded-lg hover:bg-slate-50 transition-colors"
              >
                <div className={`w-10 h-10 rounded-lg border flex items-center justify-center flex-shrink-0 ${colorClass}`}>
                  <Icon size={18} />
                </div>
                
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 mb-0.5">
                    {activity.title}
                  </p>
                  <p className="text-xs text-slate-500 truncate">
                    {activity.description}
                  </p>
                  {activity.metadata && (
                    <div className="flex gap-2 mt-1">
                      {activity.metadata.patient_id && (
                        <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                          {activity.metadata.patient_id}
                        </span>
                      )}
                      {activity.metadata.study_type && (
                        <span className="text-xs bg-blue-100 text-blue-600 px-2 py-0.5 rounded">
                          {activity.metadata.study_type}
                        </span>
                      )}
                    </div>
                  )}
                </div>
                
                <span className="text-xs text-slate-400 font-medium whitespace-nowrap">
                  {formatTimestamp(activity.timestamp)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

ActivityFeed.propTypes = {
  activities: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      type: PropTypes.oneOf(['upload', 'search', 'image', 'success']),
      title: PropTypes.string.isRequired,
      description: PropTypes.string,
      timestamp: PropTypes.string.isRequired,
      metadata: PropTypes.object,
    })
  ),
  loading: PropTypes.bool,
  maxItems: PropTypes.number,
};

export default ActivityFeed;
