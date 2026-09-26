import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API } from '../config/api';

// Habilitar el envio de cookies (credenciales) de forma global en Axios
axios.defaults.withCredentials = true;

const AuthContext = createContext();

// Flag para evitar loop de refresh
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Interceptor para auto-refresh en 401
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Si es 401 y no es un retry y no es /login o /register
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url.includes('/login') &&
      !originalRequest.url.includes('/register') &&
      !originalRequest.url.includes('/refresh-token') &&
      !originalRequest.url.includes('/me')
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(() => axios(originalRequest));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        await axios.post(`${API}/refresh-token`);
        processQueue(null);
        return axios(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError);
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

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
    // ref (FASE 3): valor del parametro ?ref= ya validado en RegisterPage.
    // Si es null se envia como undefined para que Axios lo omita del body;
    // asi /register normal envia exactamente { name, email, password }.
    const { data } = await axios.post(`${API}/register`, { name, email, password, ref: ref || undefined });
    // El backend ahora devuelve { requires_verification: true, email, user_id } en lugar de loguear directamente
    if (data.requires_verification) {
      // Lanzar error para que RegisterPage redirija a /verify-email
      throw { response: { data } };
    }
    setUser(data);
    return data;
  };

  const logout = async () => {
    await axios.post(`${API}/logout`);
    setUser(null);
  };

  const loginWithGoogle = (userData) => {
    setUser(userData);
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
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser, loginWithGoogle }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
