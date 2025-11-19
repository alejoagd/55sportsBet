// src/components/AdminButton.tsx
import React from 'react';
import { useIsAdmin } from './Hooks/useAdminMode';

interface AdminButtonProps {
  children: React.ReactNode;
  fallback?: React.ReactNode; // Qué mostrar si no es admin (opcional)
  className?: string;
  onClick?: () => void;
  disabled?: boolean;
  title?: string;
  hideCompletely?: boolean; // Si true, no renderiza nada cuando no es admin
}

// Wrapper para botones que solo admins pueden ver
export const AdminButton: React.FC<AdminButtonProps> = ({
  children,
  fallback = null,
  className = '',
  onClick,
  disabled = false,
  title,
  hideCompletely = true
}) => {
  const isAdmin = useIsAdmin();

  // Si no es admin y debe ocultarse completamente
  if (!isAdmin && hideCompletely) {
    return null;
  }

  // Si no es admin pero hay un fallback
  if (!isAdmin && fallback) {
    return <>{fallback}</>;
  }

  // Si no es admin y no hay fallback, mostrar versión deshabilitada
  if (!isAdmin) {
    return (
      <button
        className={`${className} opacity-50 cursor-not-allowed`}
        disabled={true}
        title="Acceso restringido - Solo administradores"
      >
        {children}
      </button>
    );
  }

  // Si es admin, mostrar botón normal
  return (
    <button
      className={className}
      onClick={onClick}
      disabled={disabled}
      title={title}
    >
      {children}
    </button>
  );
};

// Wrapper para cualquier contenido administrativo
interface AdminOnlyProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  hideCompletely?: boolean;
}

export const AdminOnly: React.FC<AdminOnlyProps> = ({
  children,
  fallback = null,
  hideCompletely = true
}) => {
  const isAdmin = useIsAdmin();

  if (!isAdmin) {
    if (hideCompletely) {
      return null;
    }
    return <>{fallback}</>;
  }

  return <>{children}</>;
};

// Badge que indica modo administrativo
export const AdminBadge: React.FC = () => {
  const isAdmin = useIsAdmin();

  if (!isAdmin) return null;

  return (
    <div className="fixed top-4 right-4 bg-red-500 text-white px-3 py-1 rounded-full text-xs font-bold z-50">
      🔧 ADMIN
    </div>
  );
};

export default AdminButton;