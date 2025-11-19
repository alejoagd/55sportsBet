// src/components/AdminLogin.tsx
import React, { useState } from 'react';

interface AdminLoginProps {
  isVisible: boolean;
  onLogin: (password: string) => boolean;
  onClose: () => void;
}

export const AdminLogin: React.FC<AdminLoginProps> = ({
  isVisible,
  onLogin,
  onClose
}) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  if (!isVisible) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    // Simular delay de verificación
    await new Promise(resolve => setTimeout(resolve, 500));

    const success = onLogin(password);
    
    if (success) {
      setPassword('');
      setError('');
    } else {
      setError('Contraseña incorrecta');
    }
    
    setIsLoading(false);
  };

  const handleClose = () => {
    setPassword('');
    setError('');
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-lg p-6 w-full max-w-md mx-4 border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-white">🔐 Acceso Administrativo</h3>
          <button
            onClick={handleClose}
            className="text-slate-400 hover:text-white text-2xl"
          >
            ×
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Contraseña de administrador
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Ingresa la contraseña..."
              disabled={isLoading}
              autoFocus
            />
          </div>
          
          {error && (
            <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              {error}
            </div>
          )}
          
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={isLoading || !password.trim()}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Verificando...' : 'Acceder'}
            </button>
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg font-medium transition-colors"
            >
              Cancelar
            </button>
          </div>
        </form>
        
        <div className="mt-4 text-xs text-slate-500 bg-slate-900/50 rounded-lg p-3">
          <p>💡 <strong>Para desarrolladores:</strong></p>
          <p>• Modo desarrollo: acceso automático</p>
          <p>• Modo producción: requiere contraseña</p>
          <p>• Localhost: siempre permitido</p>
        </div>
      </div>
    </div>
  );
};

export default AdminLogin;