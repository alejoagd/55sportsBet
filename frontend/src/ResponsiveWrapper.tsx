// ResponsiveWrapper.tsx
import React from 'react';
import './mobile-responsive.css';

interface ResponsiveWrapperProps {
  children: React.ReactNode;
  className?: string;
}

export const ResponsiveWrapper: React.FC<ResponsiveWrapperProps> = ({ 
  children, 
  className = '' 
}) => {
  return (
    <div className={`responsive-wrapper ${className}`}>
      {children}
    </div>
  );
};

// Hook para detectar tamaño de pantalla
export const useIsMobile = () => {
  const [isMobile, setIsMobile] = React.useState(false);

  React.useEffect(() => {
    const checkIsMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    // Check inicial
    checkIsMobile();

    // Event listener para cambios de tamaño
    window.addEventListener('resize', checkIsMobile);
    return () => window.removeEventListener('resize', checkIsMobile);
  }, []);

  return isMobile;
};

// Componente para navegación responsive
interface ResponsiveNavProps {
  children: React.ReactNode;
  className?: string;
}

export const ResponsiveNav: React.FC<ResponsiveNavProps> = ({ 
  children, 
  className = '' 
}) => {
  const isMobile = useIsMobile();
  
  return (
    <nav className={`
      ${isMobile ? 'horizontal-nav' : 'flex gap-4'}
      ${className}
    `}>
      {children}
    </nav>
  );
};

// Componente para botones responsive
interface ResponsiveButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary';
  className?: string;
  disabled?: boolean;
}

export const ResponsiveButton: React.FC<ResponsiveButtonProps> = ({
  children,
  onClick,
  variant = 'primary',
  className = '',
  disabled = false
}) => {
  const baseClasses = `
    button-${variant}
    transition-all duration-200
    rounded-lg font-medium
    disabled:opacity-50 disabled:cursor-not-allowed
    hover:opacity-80 active:scale-95
  `;

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${baseClasses} ${className}`}
    >
      {children}
    </button>
  );
};

// Componente para cards responsive
interface ResponsiveCardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const ResponsiveCard: React.FC<ResponsiveCardProps> = ({
  title,
  children,
  className = ''
}) => {
  return (
    <div className={`card bg-slate-800 border border-slate-700 ${className}`}>
      {title && (
        <h3 className="card-title text-white font-bold mb-4">
          {title}
        </h3>
      )}
      {children}
    </div>
  );
};

// Componente para grid responsive
interface ResponsiveGridProps {
  children: React.ReactNode;
  cols?: number;
  gap?: number;
  className?: string;
}

export const ResponsiveGrid: React.FC<ResponsiveGridProps> = ({
  children,
  cols = 2,
  gap = 4,
  className = ''
}) => {
  const isMobile = useIsMobile();
  
  const gridClasses = isMobile 
    ? 'grid grid-cols-1 gap-mobile'
    : `grid grid-cols-${cols} gap-${gap}`;

  return (
    <div className={`${gridClasses} ${className}`}>
      {children}
    </div>
  );
};

// Componente para texto responsive
interface ResponsiveTextProps {
  children: React.ReactNode;
  size?: 'sm' | 'base' | 'lg' | 'xl' | '2xl';
  className?: string;
}

export const ResponsiveText: React.FC<ResponsiveTextProps> = ({
  children,
  size = 'base',
  className = ''
}) => {
  const isMobile = useIsMobile();
  
  const sizeClasses = isMobile 
    ? `text-${size}-mobile`
    : `text-${size}`;

  return (
    <span className={`${sizeClasses} ${className}`}>
      {children}
    </span>
  );
};

export default ResponsiveWrapper;