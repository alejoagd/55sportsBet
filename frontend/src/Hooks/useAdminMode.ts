// src/hooks/useAdminMode.ts
import { useState, useEffect } from 'react';

// Configuración del sistema de permisos
const ADMIN_CONFIG = {
  // Cambiar a 'development' para activar modo admin
  MODE: 'development', // 'development' | 'production'
  
  // Password para activar modo admin (opcional)
  ADMIN_PASSWORD: '55sports2025',
  
  // URL patterns que activan modo admin automáticamente
  ADMIN_URLS: [
    'localhost',
    '127.0.0.1',
    'netlify.app',
  ]
};

export const useAdminMode = () => {
  const [isAdmin, setIsAdmin] = useState(false);
  const [showAdminLogin, setShowAdminLogin] = useState(false);

  useEffect(() => {
    // ✅ CORREGIDO: Si está en production, NO es admin
    if (ADMIN_CONFIG.MODE === 'production') {
      setIsAdmin(false);  // ⬅️ CAMBIO AQUÍ: false en vez de true
      return;
    }

    // Método 2: Detección automática por URL (solo en development)
    const currentHost = window.location.hostname;
    const isDevUrl = ADMIN_CONFIG.ADMIN_URLS.some(url => 
      currentHost.includes(url)
    );

    if (isDevUrl) {
      setIsAdmin(true);
      return;
    }

    // Método 3: Verificar si ya está logueado via localStorage
    const savedAdminStatus = localStorage.getItem('55sports_admin');
    if (savedAdminStatus === 'true') {
      setIsAdmin(true);
    }
  }, []);

  const loginAsAdmin = (password: string): boolean => {
    if (password === ADMIN_CONFIG.ADMIN_PASSWORD) {
      setIsAdmin(true);
      localStorage.setItem('55sports_admin', 'true');
      setShowAdminLogin(false);
      return true;
    }
    return false;
  };

  const logoutAdmin = () => {
    setIsAdmin(false);
    localStorage.removeItem('55sports_admin');
  };

  const toggleAdminLogin = () => {
    setShowAdminLogin(!showAdminLogin);
  };

  return {
    isAdmin,
    showAdminLogin,
    loginAsAdmin,
    logoutAdmin,
    toggleAdminLogin
  };
};

// Hook simplificado para componentes
export const useIsAdmin = (): boolean => {
  const { isAdmin } = useAdminMode();
  return isAdmin;
};