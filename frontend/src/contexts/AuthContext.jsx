import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../config/api';

// Habilitar el envío de cookies (credenciales) de forma global en Axios
axios.defaults.withCredentials = true;

const AuthContext = createContext();

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

  const register = async (name, email, password, ref) => {
    // ref (FASE 3): valor del parámetro ?ref= ya validado en RegisterPage.
    // Si es null se envía como undefined para que Axios lo omita del body;
    // así /register normal envía exactamente { name, email, password }.
    const { data } = await axios.post(`${API}/register`, { name, email, password, ref: ref || undefined });
    // El backend ahora devuelve { requires_verification: true, email, user_id } en lugar de loguear directamente
    if (data.requires_verification) {
      // No hacer login automático, solo devolver la data para que el frontend redirija
      return data;
    }
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
