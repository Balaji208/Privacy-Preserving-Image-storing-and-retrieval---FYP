// frontend/src/components/layout/Sidebar.jsx
import React from 'react';
import PropTypes from 'prop-types';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Upload, 
  Search, 
  History, 
  Settings,
  BarChart3,
  FileText,
  Database,
  Shield,
  HelpCircle
} from 'lucide-react';

const Sidebar = ({ isOpen, onClose }) => {
  const navItems = [
    {
      section: 'Main',
      items: [
        { path: '/', label: 'Dashboard', icon: LayoutDashboard },
        { path: '/search', label: 'Search Similar', icon: Search },
        { path: '/upload', label: 'Upload Image', icon: Upload },
        { path: '/history', label: 'History', icon: History },
      ]
    },
    {
      section: 'Management',
      items: [
        { path: '/database', label: 'Database', icon: Database },
        { path: '/analytics', label: 'Analytics', icon: BarChart3 },
        { path: '/reports', label: 'Reports', icon: FileText },
      ]
    },
    {
      section: 'System',
      items: [
        { path: '/security', label: 'Security', icon: Shield },
        { path: '/settings', label: 'Settings', icon: Settings },
        { path: '/help', label: 'Help & Docs', icon: HelpCircle },
      ]
    }
  ];

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        ></div>
      )}

      {/* Sidebar */}
      <aside 
        className={`
          fixed lg:sticky top-0 left-0 h-screen w-64 bg-white border-r border-slate-200 
          flex flex-col z-50 transition-transform duration-300 lg:translate-x-0
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Sidebar Content */}
        <div className="flex-1 overflow-y-auto py-6 px-4">
          <nav className="space-y-8">
            {navItems.map((section) => (
              <div key={section.section}>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 px-3">
                  {section.section}
                </h3>
                <div className="space-y-1">
                  {section.items.map((item) => {
                    const Icon = item.icon;
                    return (
                      <NavLink
                        key={item.path}
                        to={item.path}
                        onClick={() => onClose && onClose()}
                        className={({ isActive }) => `
                          flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-all
                          ${isActive 
                            ? 'bg-blue-50 text-blue-700 shadow-sm' 
                            : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                          }
                        `}
                      >
                        <Icon size={20} />
                        <span>{item.label}</span>
                      </NavLink>
                    );
                  })}
                </div>
              </div>
            ))}
          </nav>
        </div>

        {/* Sidebar Footer - System Info */}
        <div className="p-4 border-t border-slate-200">
          <div className="bg-gradient-to-br from-blue-50 to-teal-50 rounded-xl p-4 border border-blue-100">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="text-blue-600" size={16} />
              <span className="text-xs font-bold text-blue-900">System Status</span>
            </div>
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-slate-600">Encryption</span>
                <span className="font-semibold text-emerald-600">Active</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-600">FHE Engine</span>
                <span className="font-semibold text-emerald-600">Running</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-600">Storage</span>
                <span className="font-semibold text-blue-600">Azure</span>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

Sidebar.propTypes = {
  isOpen: PropTypes.bool,
  onClose: PropTypes.func,
};

export default Sidebar;
