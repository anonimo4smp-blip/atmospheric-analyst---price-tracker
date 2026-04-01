import React from 'react';
import {X, PlusCircle, Bell, RefreshCw, Settings, LineChart} from 'lucide-react';

interface HelpModalProps {
  onClose: () => void;
}

const steps: {icon: React.ElementType; title: string; body: string}[] = [
  {
    icon: PlusCircle,
    title: 'Añadir un producto',
    body: 'En el panel derecho pega la URL de un producto de Amazon ES o PCComponentes, fija el precio objetivo y haz clic en "Save product". El sistema hará la primera comprobación en breve.',
  },
  {
    icon: Bell,
    title: 'Recibir alertas',
    body: 'Cuando el precio cae por debajo de tu precio objetivo recibirás un email automático. Las alertas también quedan registradas en la sección "Alerts History" de la barra lateral.',
  },
  {
    icon: RefreshCw,
    title: 'Actualizar precios',
    body: 'Usa "Update now" en el dashboard para lanzar una comprobación manual de todos tus productos, o el botón de refresco en el panel de detalle para comprobar uno solo.',
  },
  {
    icon: Settings,
    title: 'Cambiar precio objetivo',
    body: 'Selecciona un producto en la lista, ve a la pestaña "Edit Alert" en el panel de detalle y guarda el nuevo precio. La alerta se disparará la próxima vez que el precio cruce ese umbral hacia abajo.',
  },
];

export function HelpModal({onClose}: HelpModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />

      {/* Panel */}
      <div
        className="relative z-10 w-full max-w-lg bg-surface-container-lowest rounded-3xl shadow-2xl border border-outline-variant/10 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-outline-variant/10">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl primary-gradient flex items-center justify-center text-white shadow">
              <LineChart size={18} />
            </div>
            <div>
              <h2 className="font-manrope font-extrabold text-on-surface text-base">Centro de ayuda</h2>
              <p className="text-[11px] text-on-surface-variant font-semibold">Atmospheric Analyst · Price Tracker</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-colors"
            aria-label="Cerrar ayuda"
          >
            <X size={18} />
          </button>
        </div>

        {/* Steps */}
        <div className="px-6 py-5 space-y-4">
          {steps.map(({icon: Icon, title, body}) => (
            <div key={title} className="flex gap-4">
              <div className="shrink-0 w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center mt-0.5">
                <Icon size={16} className="text-primary" />
              </div>
              <div>
                <p className="text-sm font-bold text-on-surface mb-0.5">{title}</p>
                <p className="text-xs text-on-surface-variant leading-relaxed">{body}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-outline-variant/10 bg-surface-container-low/50 flex items-center justify-between">
          <p className="text-[11px] text-on-surface-variant font-medium">
            Tiendas soportadas: <span className="font-bold text-on-surface">Amazon ES, PCComponentes</span>
          </p>
          <button
            onClick={onClose}
            className="text-xs font-bold text-primary hover:text-primary/80 transition-colors"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
}
