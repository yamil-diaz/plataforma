import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';

import HomePage from './pages/HomePage';
import ReaderPage from './pages/ReaderPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import AdminBookFormPage from './pages/AdminBookFormPage';
import AdminImportPage from './pages/AdminImportPage';

// Componente para proteger rutas (Debe estar autenticado)
const ProtectedRoute = ({ children, adminOnly = false }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center text-[#A0A0A0]">
        Cargando usuario...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (adminOnly && user.role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  return children;
};

function AppRoutes() {
  return (
    <Routes>
      {/* Rutas Públicas de Navegación */}
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      
      {/* Rutas Protegidas de Lectura (Debe estar logueado para ganar Rayos y leer) */}
      <Route 
        path="/books/:bookId" 
        element={
          <ProtectedRoute>
            <ReaderPage />
          </ProtectedRoute>
        } 
      />

      {/* Rutas Protegidas de Administrador */}
      <Route 
        path="/admin/new-book" 
        element={
          <ProtectedRoute adminOnly={true}>
            <AdminBookFormPage />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin/import" 
        element={
          <ProtectedRoute adminOnly={true}>
            <AdminImportPage />
          </ProtectedRoute>
        } 
      />

      {/* Redirección por defecto */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}
