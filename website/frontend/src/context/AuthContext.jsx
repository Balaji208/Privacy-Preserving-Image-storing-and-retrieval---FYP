// frontend/src/context/AuthContext.jsx
// Find the login function and update the mockTenant:

const login = async (credentials) => {
  try {
    const mockUser = {
      id: 'user_001',  // ✅ Changed from user_001
      name: credentials.username || 'Dr. Sarah Johnson',
      email: credentials.email || 'sarah.johnson@hospital.com',
      role: 'radiologist',
      permissions: ['view', 'upload', 'search', 'export'],
    };

    const mockTenant = {
      id: 'user_001',  // ✅ Changed from hospital_001 to user_001
      name: credentials.hospitalName || 'City General Hospital',
      plan: 'enterprise',
      features: ['fhe_search', 'batch_upload', 'advanced_analytics'],
    };

    const mockToken = btoa(JSON.stringify({ 
      userId: mockUser.id, 
      tenantId: mockTenant.id,
      exp: Date.now() + 24 * 60 * 60 * 1000
    }));

    localStorage.setItem('user', JSON.stringify(mockUser));
    localStorage.setItem('tenant', JSON.stringify(mockTenant));
    localStorage.setItem('authToken', mockToken);

    setUser(mockUser);
    setTenant(mockTenant);
    setIsAuthenticated(true);

    return { success: true };
  } catch (error) {
    console.error('Login failed:', error);
    return { success: false, error: error.message };
  }
};
