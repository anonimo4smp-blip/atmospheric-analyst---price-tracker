import React, {useEffect} from 'react';
import {X, AlertCircle, CheckCircle2} from 'lucide-react';

export interface Toast {
  id: number;
  type: 'error' | 'info';
  message: string;
}

interface ToastContainerProps {
  toasts: Toast[];
  onDismiss: (id: number) => void;
}

const TOAST_DURATION = 3500;

function ToastItem({toast, onDismiss}: {toast: Toast; onDismiss: (id: number) => void}) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), TOAST_DURATION);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss]);

  const isError = toast.type === 'error';

  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 rounded-2xl shadow-lg text-sm font-semibold min-w-[280px] max-w-[380px] border animate-slide-in ${
        isError
          ? 'bg-error/95 text-white border-error/20'
          : 'bg-surface-container-lowest text-on-surface border-outline-variant/20'
      }`}
    >
      <span className="mt-0.5 shrink-0">
        {isError ? (
          <AlertCircle size={16} className="text-white" />
        ) : (
          <CheckCircle2 size={16} className="text-primary" />
        )}
      </span>
      <span className="flex-1 leading-snug">{toast.message}</span>
      <button
        onClick={() => onDismiss(toast.id)}
        className={`shrink-0 mt-0.5 opacity-60 hover:opacity-100 transition-opacity ${isError ? 'text-white' : 'text-on-surface-variant'}`}
      >
        <X size={14} />
      </button>
    </div>
  );
}

export function ToastContainer({toasts, onDismiss}: ToastContainerProps) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 items-end">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
