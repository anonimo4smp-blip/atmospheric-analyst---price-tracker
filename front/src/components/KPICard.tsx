import React from 'react';
import { LucideIcon } from 'lucide-react';
import { cn } from '../lib/utils';

interface KPICardProps {
  label: string;
  value: string | number;
  subtext?: string;
  subtextColor?: string;
  icon: LucideIcon;
  variant?: 'primary' | 'tertiary';
}

export function KPICard({ label, value, subtext, subtextColor, icon: Icon, variant = 'primary' }: KPICardProps) {
  return (
    <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm border-b-4 border-transparent hover:border-primary transition-all duration-300 group">
      <div className="flex items-center justify-between mb-4">
        <span className="text-on-surface-variant text-xs font-bold uppercase tracking-wider">{label}</span>
        <div className={cn(
          "w-10 h-10 rounded-full flex items-center justify-center transition-colors",
          variant === 'primary' ? "bg-primary/10 text-primary" : "bg-tertiary-container/20 text-tertiary-container"
        )}>
          <Icon size={20} />
        </div>
      </div>
      <div className="font-manrope text-4xl font-extrabold text-on-surface">{value}</div>
      {subtext && (
        <div className={cn(
          "mt-2 text-xs font-bold",
          subtextColor || "text-on-surface-variant"
        )}>
          {subtext}
        </div>
      )}
    </div>
  );
}
