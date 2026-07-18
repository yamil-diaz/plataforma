import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

// Habilitar el envío de cookies (credenciales) de forma global en Axios
axios.defaults.withCredentials = true;

const AuthContext = createContext();

const API = 'http://localhost:8000/api';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = async () => {
    try {
      const { data } = await axios.get(`${API}/me`);
      setUser(data);
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const login = async (email, password) => {
    const { data } = await axios.post(`${API}/login`, { email, password });
    setUser(data);
    return data;
  };

  const register = async (name, email, password) => {
    const { data } = await axios.post(`${API}/register`, { name, email, password });
    setUser(data);
    return data;
  };

  const logout = async () => {
    await axios.post(`${API}/logout`);
    setUser(null);
  };

  const refreshUser = async () => {
    try {
      const { data } = await axios.get(`${API}/me`);
      setUser(data);
    } catch (error) {
      console.error('Error al actualizar datos de usuario:', error);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
