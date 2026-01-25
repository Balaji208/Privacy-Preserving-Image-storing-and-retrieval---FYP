// frontend/src/pages/Dashboard.jsx
import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import StatsCard from '../components/dashboard/StatsCard';
import ActivityFeed from '../components/dashboard/ActivityFeed';
import QuickActions from '../components/dashboard/QuickActions';
import api from '../services/api';

const Dashboard = () => {
  const { tenant, user } = useAuth();
  const [stats, setStats] = useState(null);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const { data } = await api.get('/stats', {
          params: { tenant_id: tenant?.id || 'hospital_001' }
        });
        
        setStats(data);

        // Transform recent searches into activity format
        const recentActivities = [];
        
        if (data.recent_searches) {
          data.recent_searches.forEach((search) => {
            recentActivities.push({
              id: search.query_id,
              type: 'search',
              title: 'Similarity Search Completed',
              description: `Found ${search.results_count} similar images`,
              timestamp: search.timestamp,
              metadata: {
                results_count: search.results_count,
              },
            });
          });
        }

        // Add mock upload activities (replace with real data from API)
        if (data.recent_uploads) {
          data.recent_uploads.forEach((upload) => {
            recentActivities.push({
              id: upload.image_id,
              type: 'upload',
              title: 'Image Uploaded Successfully',
              description: `${upload.study_type || 'Medical image'} encrypted and indexed`,
              timestamp: upload.upload_date,
              metadata: {
                study_type: upload.study_type,
                patient_id: upload.patient_id,
              },
            });
          });
        }

        // Sort by timestamp
        recentActivities.sort((a, b) => 
          new Date(b.timestamp) - new Date(a.timestamp)
        );

        setActivities(recentActivities);
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
        setError(err.response?.data?.message || 'Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, [tenant]);

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <p className="text-red-800 font-semibold">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-slate-800 mb-2">
            Welcome back, {user?.name || 'Doctor'}
          </h1>
          <p className="text-slate-600">
            {tenant?.name || 'Medical Center'} • Privacy-Preserving Medical Image Search
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatsCard
            title="Total Images"
            value={stats?.total_images?.toLocaleString() || '0'}
            icon="image"
            color="blue"
            subtitle="Encrypted & indexed"
            loading={loading}
            trend={stats?.images_growth ? `+${stats.images_growth}% this week` : undefined}
          />
          <StatsCard
            title="Total Searches"
            value={stats?.total_searches?.toLocaleString() || '0'}
            icon="search"
            color="teal"
            subtitle="FHE-powered queries"
            loading={loading}
            trend={stats?.searches_growth ? `+${stats.searches_growth}% this week` : undefined}
          />
          <StatsCard
            title="Avg Search Time"
            value={stats?.avg_search_time_ms ? `${stats.avg_search_time_ms}ms` : '0ms'}
            icon="clock"
            color="purple"
            subtitle="FHE computation"
            loading={loading}
          />
          <StatsCard
            title="Storage Used"
            value={stats?.storage_used_gb ? `${stats.storage_used_gb} GB` : '0 GB'}
            icon="database"
            color="orange"
            subtitle="Azure Blob Storage"
            loading={loading}
          />
        </div>

        {/* Study Type Breakdown */}
        {stats?.by_study_type && Object.keys(stats.by_study_type).length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <h2 className="text-lg font-bold text-slate-800 mb-4">Images by Study Type</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(stats.by_study_type).map(([type, count]) => (
                <div key={type} className="bg-slate-50 rounded-lg p-4 border border-slate-200">
                  <p className="text-xs text-slate-600 uppercase font-medium mb-1">
                    {type.replace('_', ' ')}
                  </p>
                  <p className="text-2xl font-bold text-slate-800">{count.toLocaleString()}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <QuickActions />

        {/* Activity Feed */}
        <ActivityFeed activities={activities} loading={loading} maxItems={10} />

        {/* System Status */}
        <div className="bg-gradient-to-br from-blue-50 to-teal-50 rounded-xl border border-blue-200 p-6">
          <div className="flex items-start gap-4">
            <div className="flex-1">
              <h3 className="text-lg font-bold text-blue-900 mb-3">System Status</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-xs text-blue-700 mb-1">Encryption</p>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                    <span className="text-sm font-bold text-blue-900">Active</span>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-blue-700 mb-1">FHE Engine</p>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                    <span className="text-sm font-bold text-blue-900">Running</span>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-blue-700 mb-1">Storage</p>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                    <span className="text-sm font-bold text-blue-900">Azure Connected</span>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-blue-700 mb-1">Redis Index</p>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                    <span className="text-sm font-bold text-blue-900">Healthy</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
