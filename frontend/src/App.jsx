import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box } from '@mui/material';
import { AuthProvider } from './contexts/AuthProvider';
import { useAuth } from './hooks/useAuth';
import Navbar from './components/Navbar';
import Login from './components/auth/Login';
import Dashboard from './components/Dashboard';
import VendorList from './components/vendors/VendorList';
import VendorForm from './components/vendors/VendorForm';
import POList from './components/purchase-orders/POList';
import POForm from './components/purchase-orders/POForm';
import ASNList from './components/asn/ASNList';
import ASNForm from './components/asn/ASNForm';
import GateQueue from './components/gate/GateQueue';
import UserManagement from './components/admin/UserManagement';
import './App.css';

// Create theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

// Protected Route component
const ProtectedRoute = ({ children, requiredRole }) => {
  const { isAuthenticated, hasRole, loading } = useAuth();

  if (loading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>Loading...</Box>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole && !hasRole(requiredRole)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

// App Routes component
const AppRoutes = () => {
  const { isAuthenticated } = useAuth();

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {isAuthenticated && <Navbar />}
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Routes>
          {/* Public routes */}
          <Route
            path="/login"
            element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />}
          />

          {/* Protected routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          {/* Vendor Management */}
          <Route
            path="/vendors"
            element={
              <ProtectedRoute>
                <VendorList />
              </ProtectedRoute>
            }
          />
          <Route
            path="/vendors/create"
            element={
              <ProtectedRoute>
                <VendorForm />
              </ProtectedRoute>
            }
          />
          <Route
            path="/vendors/:id/edit"
            element={
              <ProtectedRoute>
                <VendorForm />
              </ProtectedRoute>
            }
          />

          {/* Purchase Orders */}
          <Route
            path="/purchase-orders"
            element={
              <ProtectedRoute>
                <POList />
              </ProtectedRoute>
            }
          />
          <Route
            path="/purchase-orders/create"
            element={
              <ProtectedRoute>
                <POForm />
              </ProtectedRoute>
            }
          />
          <Route
            path="/purchase-orders/:id/edit"
            element={
              <ProtectedRoute>
                <POForm />
              </ProtectedRoute>
            }
          />

          {/* ASN Management */}
          <Route
            path="/asn"
            element={
              <ProtectedRoute>
                <ASNList />
              </ProtectedRoute>
            }
          />
          <Route
            path="/asn/create"
            element={
              <ProtectedRoute>
                <ASNForm />
              </ProtectedRoute>
            }
          />
          <Route
            path="/asn/:id/edit"
            element={
              <ProtectedRoute>
                <ASNForm />
              </ProtectedRoute>
            }
          />

          {/* Gate Check-in */}
          <Route
            path="/gate"
            element={
              <ProtectedRoute>
                <GateQueue />
              </ProtectedRoute>
            }
          />

          {/* Admin routes */}
          <Route
            path="/admin/users"
            element={
              <ProtectedRoute requiredRole="admin">
                <UserManagement />
              </ProtectedRoute>
            }
          />

          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Box>
    </Box>
  );
};

// Main App component
function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <Router>
          <AppRoutes />
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;