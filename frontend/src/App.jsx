import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';

import HomePage from './pages/HomePage';
import ReaderPage from './pages/ReaderPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import AdminBookFormPage from './pages/AdminBookFormPage';
import AdminImportPage from './pages/AdminImportPage';
import DashboardPage from './pages/DashboardPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import CoursesPage from './pages/CoursesPage';
import CoursePlayerPage from './pages/CoursePlayerPage';
import AdminCourseFormPage from './pages/AdminCourseFormPage';
import AdminGutenbergPage from './pages/AdminGutenbergPage';
import ProfilePage from './pages/ProfilePage';
import CompetitionsPage from './pages/CompetitionsPage';
import CompetitionQuizPage from './pages/CompetitionQuizPage';
import AdminCompetitionPage from './pages/AdminCompetitionPage';
import AdminQRCodesPage from './pages/AdminQRCodesPage';
import TermsPage from './pages/TermsPage';
import IAPage from './pages/IAPage';

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
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/terminos" element={<TermsPage />} />
      <Route path="/courses" element={<CoursesPage />} />
      <Route path="/courses/:id" element={<CoursePlayerPage />} />
      <Route path="/profile/:id" element={<ProfilePage />} />
      <Route path="/competitions" element={<CompetitionsPage />} />
      <Route path="/competitions/:id" element={<CompetitionQuizPage />} />
      
      {/* Rutas Protegidas de Lectura (Debe estar logueado para ganar Rayos y leer) */}
      <Route 
        path="/books/:bookId" 
        element={
          <ProtectedRoute>
            <ReaderPage />
          </ProtectedRoute>
        } 
      />

      {/* Panel de Escritor / Dashboard */}
      <Route 
        path="/dashboard" 
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        } 
      />

      {/* IA de Aeternum: solo autenticado (NO adminOnly) */}
      <Route
        path="/ia"
        element={
          <ProtectedRoute>
            <IAPage />
          </ProtectedRoute>
        }
      />

      {/* Rutas Protegidas de Administrador */}
      <Route 
        path="/admin/new-book" 
        element={
          <ProtectedRoute>
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
      <Route 
        path="/admin/new-course" 
        element={
          <ProtectedRoute adminOnly={true}>
            <AdminCourseFormPage />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin/gutenberg" 
        element={
          <ProtectedRoute adminOnly={true}>
            <AdminGutenbergPage />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin/competitions/new" 
        element={
          <ProtectedRoute adminOnly={true}>
            <AdminCompetitionPage />
          </ProtectedRoute>
        } 
      />
      <Route
        path="/admin/qr-codes"
        element={
          <ProtectedRoute adminOnly={true}>
            <AdminQRCodesPage />
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
