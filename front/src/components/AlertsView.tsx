import React from 'react';
import {Bell, Loader2, CheckCircle2, Clock, AlertTriangle, ExternalLink, RefreshCw} from 'lucide-react';
import {ApiAlert} from '../types';

interface AlertsViewProps {
  alerts: ApiAlert[];
  loading: boolean;
  onRefresh: () => void;
}

function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '-';
  return new Intl.DateTimeFormat('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function StatusBadge({status}: {status: string}) {
  if (status === 'sent') {
    return (
      <span className="inline-flex items-center gap-1 bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide">
        <CheckCircle2 size={10} />
        Sent
      </span>
    );
  }
  if (status === 'pending') {
    return (
      <span className="inline-flex items-center gap-1 bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide">
        <Clock size={10} />
        Pending
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide">
      <AlertTriangle size={10} />
      {status}
    </span>
  );
}

export function AlertsView({alerts, loading, onRefresh}: AlertsViewProps) {
  if (loading) {
    return (
      <div className="flex items-center gap-3 text-on-surface-variant font-semibold p-8">
        <Loader2 size={18} className="animate-spin" />
        Loading alerts...
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className="bg-surface-container-lowest rounded-3xl p-12 flex flex-col items-center justify-center gap-4 text-center">
        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
          <Bell size={32} className="text-primary" />
        </div>
        <div>
          <p className="text-lg font-extrabold text-on-surface mb-1">No alerts yet</p>
          <p className="text-sm text-on-surface-variant font-medium">
            Alerts will appear here when a tracked product drops to your target price.
          </p>
        </div>
        <button
          onClick={onRefresh}
          className="mt-2 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-white text-sm font-semibold hover:bg-primary/90 transition-colors"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {alerts.map((alert) => {
        const title = alert.product_title || alert.product_url;
        const savings = (alert.desired_price - alert.triggered_price).toFixed(2);
        return (
          <div
            key={alert.id}
            className="bg-surface-container-lowest rounded-2xl p-5 shadow-sm flex items-start justify-between gap-4"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <StatusBadge status={alert.status} />
                <span className="text-[10px] text-on-surface-variant font-semibold">
                  {formatDateTime(alert.triggered_at)}
                </span>
              </div>
              <p className="text-sm font-bold text-on-surface truncate mb-2" title={title}>
                {title}
              </p>
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-xs text-on-surface-variant font-medium">
                  Target:{' '}
                  <span className="font-bold text-primary">
                    {alert.desired_price.toFixed(2)} {alert.currency}
                  </span>
                </span>
                <span className="text-xs text-on-surface-variant font-medium">
                  Triggered:{' '}
                  <span className="font-bold text-on-surface">
                    {alert.triggered_price.toFixed(2)} {alert.currency}
                  </span>
                </span>
                {parseFloat(savings) > 0 && (
                  <span className="text-xs font-bold text-green-600">
                    -{savings} {alert.currency}
                  </span>
                )}
              </div>
            </div>
            <a
              href={alert.product_url}
              target="_blank"
              rel="noreferrer"
              className="shrink-0 p-2 rounded-xl bg-surface-container-high text-on-surface-variant hover:text-primary hover:bg-primary/10 transition-colors"
              title="View product"
            >
              <ExternalLink size={16} />
            </a>
          </div>
        );
      })}
    </div>
  );
}
