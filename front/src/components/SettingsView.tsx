import React, {useState} from 'react';
import {User, Lock, ShieldCheck, Eye, EyeOff, Loader2, Moon, Sun} from 'lucide-react';
import {cn} from '../lib/utils';

interface SettingsViewProps {
  userEmail: string;
  darkMode: boolean;
  onToggleDark: () => void;
  onChangePassword: (currentPwd: string, newPwd: string) => Promise<void>;
  onRevokeOtherSessions: () => Promise<void>;
}

function SectionCard({title, icon: Icon, children}: {title: string; icon: React.ElementType; children: React.ReactNode}) {
  return (
    <div className="bg-surface-container-lowest rounded-2xl shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 px-6 py-4 border-b border-outline-variant/10">
        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
          <Icon size={16} className="text-primary" />
        </div>
        <h3 className="font-manrope font-bold text-on-surface text-sm">{title}</h3>
      </div>
      <div className="px-6 py-5">{children}</div>
    </div>
  );
}

function PasswordInput({
  id,
  label,
  value,
  onChange,
  hint,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  hint?: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-xs font-bold text-on-surface-variant uppercase tracking-wide">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={show ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl px-4 py-2.5 pr-10 text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition"
        />
        <button
          type="button"
          onClick={() => setShow((s) => !s)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface transition-colors"
          tabIndex={-1}
        >
          {show ? <EyeOff size={15} /> : <Eye size={15} />}
        </button>
      </div>
      {hint && <p className="text-[11px] text-on-surface-variant">{hint}</p>}
    </div>
  );
}

export function SettingsView({userEmail, darkMode, onToggleDark, onChangePassword, onRevokeOtherSessions}: SettingsViewProps) {
  const [currentPwd, setCurrentPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [pwdError, setPwdError] = useState<string | null>(null);
  const [savingPwd, setSavingPwd] = useState(false);
  const [revoking, setRevoking] = useState(false);

  const handleSubmitPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwdError(null);

    if (newPwd.length < 12) {
      setPwdError('La nueva contraseña debe tener al menos 12 caracteres.');
      return;
    }
    if (newPwd !== confirmPwd) {
      setPwdError('Las contraseñas nuevas no coinciden.');
      return;
    }

    setSavingPwd(true);
    try {
      await onChangePassword(currentPwd, newPwd);
      setCurrentPwd('');
      setNewPwd('');
      setConfirmPwd('');
    } catch (err) {
      setPwdError(err instanceof Error ? err.message : 'Error al cambiar la contraseña.');
    } finally {
      setSavingPwd(false);
    }
  };

  const handleRevoke = async () => {
    setRevoking(true);
    try {
      await onRevokeOtherSessions();
    } finally {
      setRevoking(false);
    }
  };

  return (
    <div className="max-w-xl space-y-6">
      {/* Appearance */}
      <SectionCard title="Apariencia" icon={darkMode ? Moon : Sun}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-bold text-on-surface">Modo oscuro</p>
            <p className="text-xs text-on-surface-variant mt-0.5">
              {darkMode ? 'Tema oscuro activo' : 'Tema claro activo'}
            </p>
          </div>
          <button
            type="button"
            onClick={onToggleDark}
            className={cn(
              'relative w-11 h-6 rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary/40',
              darkMode ? 'bg-primary' : 'bg-outline-variant',
            )}
            aria-label="Toggle dark mode"
          >
            <span
              className={cn(
                'absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200 flex items-center justify-center',
                darkMode ? 'translate-x-5' : 'translate-x-0',
              )}
            >
              {darkMode
                ? <Moon size={11} className="text-primary" />
                : <Sun size={11} className="text-on-surface-variant" />}
            </span>
          </button>
        </div>
      </SectionCard>

      {/* Account */}
      <SectionCard title="Cuenta" icon={User}>
        <div className="space-y-1">
          <p className="text-xs font-bold text-on-surface-variant uppercase tracking-wide">Email</p>
          <p className="text-sm font-semibold text-on-surface bg-surface-container-low rounded-xl px-4 py-2.5 border border-outline-variant/20">
            {userEmail}
          </p>
        </div>
      </SectionCard>

      {/* Change password */}
      <SectionCard title="Cambiar contraseña" icon={Lock}>
        <form onSubmit={(e) => void handleSubmitPassword(e)} className="space-y-4">
          <PasswordInput
            id="current-pwd"
            label="Contraseña actual"
            value={currentPwd}
            onChange={setCurrentPwd}
          />
          <PasswordInput
            id="new-pwd"
            label="Nueva contraseña"
            value={newPwd}
            onChange={setNewPwd}
            hint="Mínimo 12 caracteres."
          />
          <PasswordInput
            id="confirm-pwd"
            label="Confirmar nueva contraseña"
            value={confirmPwd}
            onChange={setConfirmPwd}
          />

          {pwdError && (
            <p className="text-sm text-red-600 font-medium bg-red-50 rounded-xl px-4 py-2.5">{pwdError}</p>
          )}

          <button
            type="submit"
            disabled={savingPwd || !currentPwd || !newPwd || !confirmPwd}
            className={cn(
              'w-full py-2.5 rounded-xl text-sm font-bold transition-colors flex items-center justify-center gap-2',
              'bg-primary text-white hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed',
            )}
          >
            {savingPwd ? <Loader2 size={15} className="animate-spin" /> : null}
            Guardar contraseña
          </button>
        </form>
      </SectionCard>

      {/* Sessions */}
      <SectionCard title="Sesiones activas" icon={ShieldCheck}>
        <div className="space-y-3">
          <p className="text-sm text-on-surface-variant">
            Cierra todas las sesiones abiertas en otros dispositivos. Tu sesión actual permanecerá activa.
          </p>
          <button
            onClick={() => void handleRevoke()}
            disabled={revoking}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-red-200 text-red-600 text-sm font-bold hover:bg-red-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {revoking ? <Loader2 size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
            Cerrar otras sesiones
          </button>
        </div>
      </SectionCard>
    </div>
  );
}
