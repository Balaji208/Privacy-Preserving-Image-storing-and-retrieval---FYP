// frontend/src/components/layout/Header.jsx
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { 
  Bell, 
  User, 
  Settings, 
  LogOut, 
  Shield,
  ChevronDown,
  Menu,
  X
} from 'lucide-react';

const Header = ({ 
  hospitalName = 'Medical Center',
  userName = 'Dr. Smith',
  onMenuToggle,
  isSidebarOpen 
}) => {
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);

  const notifications = [
    {
      id: 1,
      type: 'success',
      message: 'Search completed with 5 similar cases found',
      time: '2 min ago',
      unread: true,
    },
    {
      id: 2,
      type: 'info',
      message: 'New image uploaded and encrypted successfully',
      time: '15 min ago',
      unread: true,
    },
    {
      id: 3,
      type: 'warning',
      message: 'System maintenance scheduled for tonight',
      time: '1 hour ago',
      unread: false,
    },
  ];

  const unreadCount = notifications.filter(n => n.unread).length;

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-sm">
      <div className="flex items-center justify-between px-6 py-4">
        {/* Left Section - Logo & Menu Toggle */}
        <div className="flex items-center gap-4">
          <button
            onClick={onMenuToggle}
            className="lg:hidden p-2 hover:bg-slate-100 rounded-lg transition-colors"
          >
            {isSidebarOpen ? <X size={24} /> : <Menu size={24} />}
          </button>

          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-teal-600 rounded-lg flex items-center justify-center">
              <Shield className="text-white" size={24} />
            </div>
            <div className="hidden sm:block">
              <h1 className="text-xl font-bold text-slate-800">MedSearch AI</h1>
              <p className="text-xs text-slate-500">Privacy-Preserving Medical Search</p>
            </div>
          </div>
        </div>

        {/* Right Section - Notifications & User */}
        <div className="flex items-center gap-3">
          {/* FHE Status Indicator */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-full">
            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
            <span className="text-xs font-semibold text-emerald-700">FHE Active</span>
          </div>

          {/* Notifications */}
          <div className="relative">
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              className="relative p-2 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <Bell size={20} className="text-slate-600" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                  {unreadCount}
                </span>
              )}
            </button>

            {/* Notifications Dropdown */}
            {showNotifications && (
              <>
                <div 
                  className="fixed inset-0 z-40" 
                  onClick={() => setShowNotifications(false)}
                ></div>
                <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-xl border border-slate-200 z-50">
                  <div className="p-4 border-b border-slate-200">
                    <h3 className="font-bold text-slate-800">Notifications</h3>
                    <p className="text-xs text-slate-500 mt-0.5">You have {unreadCount} unread messages</p>
                  </div>
                  <div className="max-h-96 overflow-y-auto">
                    {notifications.map((notification) => (
                      <div
                        key={notification.id}
                        className={`p-4 border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors ${
                          notification.unread ? 'bg-blue-50/50' : ''
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`w-2 h-2 rounded-full mt-1.5 ${
                            notification.type === 'success' ? 'bg-emerald-500' :
                            notification.type === 'warning' ? 'bg-amber-500' :
                            'bg-blue-500'
                          }`}></div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-slate-800">{notification.message}</p>
                            <p className="text-xs text-slate-500 mt-1">{notification.time}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="p-3 text-center border-t border-slate-200">
                    <button className="text-sm font-semibold text-blue-600 hover:text-blue-700">
                      View All Notifications
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* User Menu */}
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-3 p-2 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <div className="hidden md:block text-right">
                <p className="text-sm font-semibold text-slate-800">{userName}</p>
                <p className="text-xs text-slate-500">{hospitalName}</p>
              </div>
              <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-teal-500 rounded-full flex items-center justify-center">
                <User className="text-white" size={18} />
              </div>
              <ChevronDown size={16} className="text-slate-400 hidden md:block" />
            </button>

            {/* User Dropdown */}
            {showUserMenu && (
              <>
                <div 
                  className="fixed inset-0 z-40" 
                  onClick={() => setShowUserMenu(false)}
                ></div>
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-xl border border-slate-200 z-50">
                  <div className="p-4 border-b border-slate-200">
                    <p className="font-bold text-slate-800">{userName}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{hospitalName}</p>
                    <p className="text-xs text-slate-400 mt-1 font-mono">ID: hospital_001</p>
                  </div>
                  <div className="py-2">
                    <button className="w-full px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-3 transition-colors">
                      <User size={16} />
                      Profile Settings
                    </button>
                    <button className="w-full px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-3 transition-colors">
                      <Settings size={16} />
                      System Settings
                    </button>
                    <button className="w-full px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-3 transition-colors">
                      <Shield size={16} />
                      Privacy & Security
                    </button>
                  </div>
                  <div className="py-2 border-t border-slate-200">
                    <button className="w-full px-4 py-2.5 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-3 transition-colors font-semibold">
                      <LogOut size={16} />
                      Logout
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

Header.propTypes = {
  hospitalName: PropTypes.string,
  userName: PropTypes.string,
  onMenuToggle: PropTypes.func,
  isSidebarOpen: PropTypes.bool,
};

export default Header;
