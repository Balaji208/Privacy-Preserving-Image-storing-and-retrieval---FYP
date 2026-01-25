// frontend/src/components/layout/Footer.jsx
import React from 'react';
import PropTypes from 'prop-types';
import { Shield, Lock, Server, Heart } from 'lucide-react';

const Footer = ({ className = '' }) => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className={`bg-white border-t border-slate-200 mt-auto ${className}`}>
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Top Section */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* About */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-teal-600 rounded-lg flex items-center justify-center">
                <Shield className="text-white" size={18} />
              </div>
              <h3 className="font-bold text-slate-800">MedSearch AI</h3>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed">
              Privacy-preserving medical image similarity search powered by Fully Homomorphic Encryption.
            </p>
          </div>

          {/* Features */}
          <div>
            <h4 className="font-bold text-slate-800 mb-3 text-sm">Features</h4>
            <ul className="space-y-2 text-sm text-slate-600">
              <li className="hover:text-blue-600 cursor-pointer transition-colors">Encrypted Search</li>
              <li className="hover:text-blue-600 cursor-pointer transition-colors">Image Upload</li>
              <li className="hover:text-blue-600 cursor-pointer transition-colors">Case Matching</li>
              <li className="hover:text-blue-600 cursor-pointer transition-colors">Search History</li>
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="font-bold text-slate-800 mb-3 text-sm">Resources</h4>
            <ul className="space-y-2 text-sm text-slate-600">
              <li className="hover:text-blue-600 cursor-pointer transition-colors">Documentation</li>
              <li className="hover:text-blue-600 cursor-pointer transition-colors">API Reference</li>
              <li className="hover:text-blue-600 cursor-pointer transition-colors">Security Guide</li>
              <li className="hover:text-blue-600 cursor-pointer transition-colors">Contact Support</li>
            </ul>
          </div>

          {/* Security Info */}
          <div>
            <h4 className="font-bold text-slate-800 mb-3 text-sm">Security</h4>
            <div className="space-y-3">
              <div className="flex items-start gap-2">
                <Lock className="text-emerald-600 flex-shrink-0 mt-0.5" size={16} />
                <div>
                  <p className="text-xs font-semibold text-slate-800">End-to-End Encrypted</p>
                  <p className="text-xs text-slate-500">All data encrypted at rest</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <Server className="text-blue-600 flex-shrink-0 mt-0.5" size={16} />
                <div>
                  <p className="text-xs font-semibold text-slate-800">FHE Powered</p>
                  <p className="text-xs text-slate-500">Search on encrypted data</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-slate-200 pt-6">
          {/* Bottom Section */}
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm text-slate-600">
              © {currentYear} MedSearch AI. All rights reserved.
            </p>

            {/* Technology Stack */}
            <div className="flex items-center gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <Shield size={14} className="text-blue-600" />
                BFV Encryption
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Server size={14} className="text-teal-600" />
                Azure Storage
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Lock size={14} className="text-emerald-600" />
                HSM Protected
              </span>
            </div>

            {/* Links */}
            <div className="flex items-center gap-4 text-sm">
              <a href="/privacy" className="text-slate-600 hover:text-blue-600 transition-colors">
                Privacy Policy
              </a>
              <span className="text-slate-300">|</span>
              <a href="/terms" className="text-slate-600 hover:text-blue-600 transition-colors">
                Terms of Service
              </a>
              <span className="text-slate-300">|</span>
              <a href="/compliance" className="text-slate-600 hover:text-blue-600 transition-colors">
                HIPAA Compliance
              </a>
            </div>
          </div>

          {/* Made with Love */}
          <div className="mt-6 text-center">
            <p className="text-xs text-slate-500 flex items-center justify-center gap-1">
              Built with <Heart size={12} className="text-red-500 fill-red-500" /> for healthcare professionals
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
};

Footer.propTypes = {
  className: PropTypes.string,
};

export default Footer;
