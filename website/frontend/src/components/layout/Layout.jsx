// frontend/src/components/layout/Layout.jsx
import React from 'react';

const Layout = ({ children }) => {
  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="bg-white border-b border-slate-200 p-4">
        <h1 className="text-xl font-bold">MedSearch AI</h1>
      </nav>
      <main>{children}</main>
    </div>
  );
};

export default Layout;
