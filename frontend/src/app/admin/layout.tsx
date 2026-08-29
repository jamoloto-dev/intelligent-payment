'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useApp } from '@/lib/context';
import { 
  BarChart3, 
  ShieldAlert, 
  ShoppingBag, 
  Package, 
  Activity, 
  SlidersHorizontal,
  ShieldCheck,
  Lock,
  Loader2,
  ArrowRight
} from 'lucide-react';

const ADMIN_ALLOWED_ROLES = [
  'ADMIN',
  'OWNER',
  'FINANCE',
  'OPERATIONS',
  'FRAUD_ANALYST',
  'SUPPORT',
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, token, role, isLoadingAuth } = useApp();

  const navItems = [
    { label: 'Overview & Metrics', href: '/admin', icon: <BarChart3 className="w-4 h-4" /> },
    { label: 'Fraud Intelligence Lab', href: '/admin/fraud', icon: <ShieldAlert className="w-4 h-4" /> },
    { label: 'Orders & Refunds', href: '/admin/orders', icon: <ShoppingBag className="w-4 h-4" /> },
    { label: 'Inventory & Products', href: '/admin/products', icon: <Package className="w-4 h-4" /> },
    { label: 'Microservices Topology', href: '/admin/system', icon: <Activity className="w-4 h-4" /> },
  ];

  if (isLoadingAuth) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center space-y-3">
        <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
        <p className="text-xs text-slate-400">Verifying session authority...</p>
      </div>
    );
  }

  if (!token || !user) {
    return (
      <div className="max-w-lg mx-auto my-12 p-8 rounded-3xl bg-slate-900 border border-slate-800 text-center space-y-4 shadow-2xl">
        <div className="w-12 h-12 rounded-2xl bg-rose-500/10 text-rose-400 flex items-center justify-center mx-auto">
          <Lock className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-white">Authentication Required</h2>
        <p className="text-xs text-slate-400 leading-relaxed">
          The Admin & Operations Control Center is restricted to authorized personnel. Please sign in with an administrative, finance, operations, or analyst account.
        </p>
        <Link
          href={`/login?redirect=${encodeURIComponent(pathname)}`}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg transition-all"
        >
          Sign In Now <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    );
  }

  const isAuthorized = ADMIN_ALLOWED_ROLES.includes(role.toUpperCase());

  if (!isAuthorized) {
    return (
      <div className="max-w-lg mx-auto my-12 p-8 rounded-3xl bg-slate-900 border border-slate-800 text-center space-y-4 shadow-2xl">
        <div className="w-12 h-12 rounded-2xl bg-amber-500/10 text-amber-400 flex items-center justify-center mx-auto">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-white">Access Denied (HTTP 403)</h2>
        <p className="text-xs text-slate-400 leading-relaxed">
          Your current role (<span className="font-mono font-bold text-amber-300">{role}</span>) does not have sufficient permissions to access administrative management tools.
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-all"
        >
          Return to Storefront
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Admin Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center font-bold">
            <SlidersHorizontal className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Admin & Operations Control Center</h1>
            <p className="text-xs text-slate-400">Live monitoring, deterministic risk heuristics & distributed microservice orchestration</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-400 text-xs font-semibold">
            <ShieldCheck className="w-3.5 h-3.5" />
            RBAC: Role {role}
          </span>
        </div>
      </div>

      {/* Admin Navigation Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-slate-800">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/20'
                  : 'bg-slate-900/60 text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800'
              }`}
            >
              {item.icon}
              {item.label}
            </Link>
          );
        })}
      </div>

      {/* Page Content */}
      <div>{children}</div>
    </div>
  );
}
