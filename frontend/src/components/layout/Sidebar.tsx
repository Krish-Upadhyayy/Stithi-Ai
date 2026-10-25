'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Building2,
  Video,
  AlertTriangle,
  Boxes,
  Eye,
  ShieldCheck,
  LogOut,
  User as UserIcon,
} from 'lucide-react';
import { useAuth } from '@/lib/auth/auth-context';
import { Badge } from '@/components/ui/Badge';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  roles: string[];
}

const allNavItems: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, roles: ['ADMIN', 'CENTRE_USER', 'REVIEWER'] },
  { name: 'Centres', href: '/centres', icon: Building2, roles: ['ADMIN', 'CENTRE_USER'] },
  { name: 'Monitoring Session', href: '/monitoring', icon: Video, roles: ['ADMIN', 'CENTRE_USER'] },
  { name: 'Compliance Alerts', href: '/alerts', icon: AlertTriangle, roles: ['ADMIN', 'CENTRE_USER', 'REVIEWER'] },
  { name: 'Inventory Baseline', href: '/inventory', icon: Boxes, roles: ['ADMIN'] },
  { name: 'Evidence Viewer', href: '/evidence', icon: Eye, roles: ['ADMIN', 'REVIEWER'] },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const userRole = user?.role || 'ADMIN';
  const visibleNavItems = allNavItems.filter((item) =>
    item.roles.includes(userRole)
  );

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between shrink-0">
      <div>
        {/* App Title */}
        <div className="h-16 flex items-center px-6 border-b border-slate-800 gap-3">
          <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-wide leading-tight">Stithi AI</h1>
            <p className="text-[11px] text-slate-400">Centre Monitoring System</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* User Session & Logout Panel */}
      <div className="p-4 border-t border-slate-800 space-y-3">
        {user ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0">
                  <UserIcon className="w-3.5 h-3.5" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-medium text-white truncate">{user.name}</p>
                  <p className="text-[10px] text-slate-500 truncate">{user.email}</p>
                </div>
              </div>
              <Badge variant="outline" className="text-[10px] font-mono shrink-0">
                {user.role}
              </Badge>
            </div>

            <button
              onClick={logout}
              className="w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 border border-slate-800 hover:border-rose-500/20 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign Out</span>
            </button>
          </div>
        ) : (
          <div className="text-xs text-slate-500">
            <p>Authentication Required</p>
          </div>
        )}

        {/* Privacy Preserving Tag */}
        <div className="pt-2 border-t border-slate-800/60 text-[11px] text-slate-500 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          <span>Anonymous presence only (No Face ID)</span>
        </div>
      </div>
    </aside>
  );
}
