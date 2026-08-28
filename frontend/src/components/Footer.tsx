'use client';

import React from 'react';
import { ShieldCheck, Cpu, Database, Network, GitBranch } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-950/50 mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-500" />
              <span className="font-bold text-slate-900 dark:text-white">IntelligentPay Platform</span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              Clean Architecture microservices suite powered by FastAPI, PostgreSQL, Redis, MongoDB, and Azure Functions.
            </p>
          </div>

          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white mb-3">
              Microservices Tier
            </h4>
            <ul className="text-xs space-y-2 text-slate-500 dark:text-slate-400">
              <li className="flex items-center gap-1.5"><Network className="w-3.5 h-3.5 text-emerald-500" /> API Gateway (:8000)</li>
              <li className="flex items-center gap-1.5"><Cpu className="w-3.5 h-3.5 text-blue-500" /> User & Product Services</li>
              <li className="flex items-center gap-1.5"><Database className="w-3.5 h-3.5 text-purple-500" /> Order & Payment Engines</li>
              <li className="flex items-center gap-1.5"><ShieldCheck className="w-3.5 h-3.5 text-amber-500" /> Real-time Fraud Scorer</li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white mb-3">
              Security & Reliability
            </h4>
            <ul className="text-xs space-y-2 text-slate-500 dark:text-slate-400">
              <li>• Idempotent Payment Charges</li>
              <li>• Zero-Race Row Locks (Pessimistic)</li>
              <li>• Asynchronous Redis Pub/Sub</li>
              <li>• Serverless Azure Audit Ledger</li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white mb-3">
              Environment
            </h4>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-mono text-slate-600 dark:text-slate-400">
              <GitBranch className="w-3.5 h-3.5 text-emerald-500" />
              v1.0.0-production-ready
            </div>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-slate-200/60 dark:border-slate-800/60 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
          <p>© 2026 Intelligent Payment & Order Platform. All rights reserved.</p>
          <p className="font-mono">FastAPI • Next.js • Tailwind CSS • Docker</p>
        </div>
      </div>
    </footer>
  );
};
