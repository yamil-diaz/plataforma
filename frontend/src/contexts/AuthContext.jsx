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
  // Época de auth: evita que /me lento borre un login recién completado
  // (típico en /auth/google/callback: checkAuth corre al montar y el OAuth
  // termina después; si /me devuelve 401 pisaba la sesión).
  const authEpochRef = React.useRef(0);

  const checkAuth = async () => {
    const epoch = authEpochRef.current;
    try {
      const { data } = await axios.get(`${API}/me`);
      if (epoch === authEpochRef.current) setUser(data);
    } catch (error) {
      // Access token vencido (Max-Age1h): refresh silencioso con el
      // refresh_token y reintento. Sin esto, cada sesión >1h rebotaba al login.
      if (error?.response?.status === 401) {
        try {
          await axios.post(`${API}/refresh-token`);
          const retry = await axios.get(`${API}/me`);
          if (epoch === authEpochRef.current) setUser(retry.data);
        } catch (_) {
          if (epoch === authEpochRef.current) setUser(null);
        }
      } else if (epoch === authEpochRef.current) {
        setUser(null);
      }
    } finally {
      if (epoch === authEpochRef.current) setLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const login = async (email, password) => {
    const { data } = await axios.post(`${API}/login`, { email, password });
    authEpochRef.current += 1;
    setUser(data);
    setLoading(false);
    return data;
  };

  const register = async (name, email, password, ref) => {
    const { data } = await axios.post(`${API}/register`, { name, email, password, ref: ref || undefined });
    if (data?.requires_verification) {
      try {
        sessionStorage.setItem('pending_verify_email', data.email || email);
        sessionStorage.setItem('pending_verify_user_id', String(data.user_id || ''));
      } catch (_) {}
      return data;
    }
    authEpochRef.current += 1;
    setUser(data);
    setLoading(false);
    return data;
  };

  const logout = async () => {
    await axios.post(`${API}/logout`);
    authEpochRef.current += 1;
    setUser(null);
  };

  const completeAuth = useCallback((userData) => {
    if (userData) {
      authEpochRef.current += 1;
      setUser(userData);
      setLoading(false);
    }
    return userData;
  }, []);

  const loginWithGoogle = useCallback((userData) => {
    if (userData) {
      authEpochRef.current += 1;
      setUser(userData);
      setLoading(false);
    }
    return userData;
  }, []);

  const refreshUser = async () => {
    try {
      const { data } = await axios.get(`${API}/me`);
      authEpochRef.current += 1;
      setUser(data);
    } catch (error) {
      console.error('Error al actualizar datos de usuario:', error);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser, loginWithGoogle, completeAuth }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
