import React from 'react';
import {
  LayoutDashboard,
  Package,
  Bell,
  Settings,
  Plus,
  LifeBuoy,
  LogOut,
  LogIn,
  LineChart,
} from 'lucide-react';
import {cn} from '../lib/utils';

export type SidebarPage = 'dashboard' | 'alerts' | 'settings';

interface SidebarProps {
  userEmail?: string | null;
  isAuthenticated?: boolean;
  activePage?: SidebarPage;
  alertsBadge?: number;
  onNavigate?: (page: SidebarPage) => void;
  onHelp?: () => void;
  onShowLogin?: () => void;
  onLogout?: () => void;
}

export function Sidebar({userEmail, isAuthenticated, activePage = 'dashboard', alertsBadge, onNavigate, onHelp, onShowLogin, onLogout}: SidebarProps) {
  const navItems: {icon: React.ElementType; label: string; page: SidebarPage; badge?: number}[] = [
    {icon: LayoutDashboard, label: 'Dashboard', page: 'dashboard'},
    {icon: Package, label: 'Tracked Products', page: 'dashboard'},
    {icon: Bell, label: 'Alerts', page: 'alerts', badge: alertsBadge},
    {icon: Settings, label: 'Settings', page: 'settings'},
  ];

  return (
    <aside className="w-64 h-screen fixed left-0 top-0 bg-surface-container-low border-r border-outline-variant/10 flex flex-col p-6 font-manrope">
      <div className="flex items-center gap-3 mb-10 px-2">
        <div className="w-10 h-10 rounded-xl primary-gradient flex items-center justify-center text-white shadow-lg">
          <LineChart size={24} />
        </div>
        <div>
          <h1 className="text-lg font-extrabold text-primary tracking-tight">Atmospheric Analyst</h1>
          <p className="text-[10px] text-on-surface-variant font-bold uppercase tracking-widest">Premium SaaS</p>
        </div>
      </div>

      <nav className="flex-1 space-y-2">
        {navItems.map((item) => {
          const isActive = item.page === activePage;
          return (
            <button
              key={item.label}
              onClick={() => onNavigate?.(item.page)}
              className={cn(
                'w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 text-sm font-semibold',
                isActive
                  ? 'bg-surface-container-lowest text-primary shadow-sm'
                  : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface',
              )}
            >
              <item.icon size={20} />
              <span className="flex-1 text-left">{item.label}</span>
              {item.badge != null && item.badge > 0 && (
                <span className="ml-auto bg-primary text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center leading-tight">
                  {item.badge > 99 ? '99+' : item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="mt-auto space-y-4">
        <button className="w-full primary-gradient text-white font-bold py-3 rounded-xl shadow-md flex items-center justify-center gap-2 transition-transform active:scale-95">
          <Plus size={18} />
          <span>Add New Product</span>
        </button>

        <div className="pt-4 border-t border-outline-variant/10 space-y-1">
          {isAuthenticated && userEmail && (
            <div className="px-4 py-2 text-xs font-semibold text-on-surface-variant truncate">
              {userEmail}
            </div>
          )}
          <button
            onClick={onHelp}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-semibold text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-all"
          >
            <LifeBuoy size={20} />
            <span>Help Center</span>
          </button>
          {isAuthenticated ? (
            <button
              onClick={onLogout}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-semibold text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-all"
            >
              <LogOut size={20} />
              <span>Logout</span>
            </button>
          ) : (
            <button
              onClick={onShowLogin}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-semibold text-primary hover:bg-primary/10 transition-all"
            >
              <LogIn size={20} />
              <span>Iniciar sesión</span>
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
