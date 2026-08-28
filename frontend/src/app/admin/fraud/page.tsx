'use client';

import React, { useState } from 'react';
import { apiClient } from '@/lib/api';
import { FraudCheckRequest, FraudCheckResponse } from '@/types';
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  XCircle, 
  Zap, 
  RefreshCw, 
  Sliders, 
  CheckCircle2,
  Info
} from 'lucide-react';

export default function FraudIntelligencePage() {
  const [formData, setFormData] = useState<FraudCheckRequest>({
    transaction_id: `tx_${Date.now().toString(36)}`,
    order_id: `ord_${Math.floor(1000 + Math.random() * 9000)}`,
    user_id: 'usr_test_evaluator',
    amount: 2500.0,
    currency: 'USD',
    recent_transactions_count_1h: 6,
    recent_failed_payments_24h: 2,
    billing_country: 'US',
    ip_country: 'RU',
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FraudCheckResponse | null>(null);

  const runFraudCheck = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await apiClient.evaluateFraud(formData);
      setResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getDecisionBadge = (decision: string) => {
    switch (decision) {
      case 'APPROVE':
        return (
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-950/80 border border-emerald-800 text-emerald-300 font-bold text-sm">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            Decision: AUTOMATIC APPROVE
          </div>
        );
      case 'REVIEW':
        return (
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-950/80 border border-amber-800 text-amber-300 font-bold text-sm">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            Decision: MANUAL FRAUD REVIEW REQUIRED
          </div>
        );
      case 'REJECT':
        return (
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-300 font-bold text-sm">
            <XCircle className="w-4 h-4 text-rose-400" />
            Decision: HARD BLOCK / REJECT
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header Info */}
      <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-purple-400" />
            Deterministic Real-Time Fraud Intelligence Engine
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Simulate incoming transaction payloads against the 5 production rule heuristics.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Input Form Simulator */}
        <form onSubmit={runFraudCheck} className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Sliders className="w-4 h-4 text-emerald-400" />
            Transaction Evaluation Parameters
          </h3>

          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-slate-400 font-semibold mb-1">Transaction Amount ($)</label>
              <input
                type="number"
                step="0.01"
                required
                value={formData.amount}
                onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white font-mono outline-none focus:border-emerald-500"
              />
              <span className="text-[10px] text-slate-500">Threshold: $1,500 review, $5,000 reject</span>
            </div>

            <div>
              <label className="block text-slate-400 font-semibold mb-1">Currency</label>
              <input
                type="text"
                value={formData.currency}
                disabled
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/60 border border-slate-800 text-slate-400 font-mono"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-slate-400 font-semibold mb-1">Recent Velocity (1h)</label>
              <input
                type="number"
                required
                value={formData.recent_transactions_count_1h}
                onChange={(e) => setFormData({ ...formData, recent_transactions_count_1h: parseInt(e.target.value) || 0 })}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white font-mono outline-none focus:border-emerald-500"
              />
              <span className="text-[10px] text-slate-500">Limit: 5 attempts/hour</span>
            </div>

            <div>
              <label className="block text-slate-400 font-semibold mb-1">Failed Payments (24h)</label>
              <input
                type="number"
                required
                value={formData.recent_failed_payments_24h}
                onChange={(e) => setFormData({ ...formData, recent_failed_payments_24h: parseInt(e.target.value) || 0 })}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white font-mono outline-none focus:border-emerald-500"
              />
              <span className="text-[10px] text-slate-500">Threshold: ≥ 3 failures</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-slate-400 font-semibold mb-1">Billing Country</label>
              <select
                value={formData.billing_country}
                onChange={(e) => setFormData({ ...formData, billing_country: e.target.value })}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white outline-none"
              >
                <option value="US">United States (US)</option>
                <option value="GB">United Kingdom (GB)</option>
                <option value="DE">Germany (DE)</option>
                <option value="CA">Canada (CA)</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-400 font-semibold mb-1">Client IP Geolocation</label>
              <select
                value={formData.ip_country}
                onChange={(e) => setFormData({ ...formData, ip_country: e.target.value })}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white outline-none"
              >
                <option value="US">United States (US)</option>
                <option value="RU">Russia (RU) [Country Mismatch]</option>
                <option value="NG">Nigeria (NG) [Country Mismatch]</option>
                <option value="GB">United Kingdom (GB)</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-purple-600/20 transition-all"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4 fill-white" />}
            Evaluate Transaction Risk
          </button>
        </form>

        {/* Evaluation Output / Intelligence Report */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-6">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Heuristic Risk Assessment Report
          </h3>

          {!result ? (
            <div className="h-72 flex flex-col items-center justify-center text-center text-slate-500 space-y-2">
              <ShieldAlert className="w-12 h-12 stroke-1 text-slate-600" />
              <p className="text-xs">Adjust parameters and click &quot;Evaluate Transaction Risk&quot; to inspect rule triggers.</p>
            </div>
          ) : (
            <div className="space-y-5 animate-in fade-in">
              {/* Score Gauge & Level */}
              <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 flex items-center justify-between">
                <div>
                  <div className="text-xs text-slate-400 font-semibold">Calculated Risk Score</div>
                  <div className="text-3xl font-black text-white mt-1">
                    {result.risk_score} <span className="text-xs font-normal text-slate-500">/ 100</span>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-xs text-slate-400 font-semibold">Assigned Risk Level</div>
                  <div
                    className={`text-sm font-extrabold mt-1 px-3 py-1 rounded-full border ${
                      result.risk_level === 'CRITICAL'
                        ? 'bg-rose-950/80 border-rose-800 text-rose-300'
                        : result.risk_level === 'HIGH'
                        ? 'bg-orange-950/80 border-orange-800 text-orange-300'
                        : result.risk_level === 'MEDIUM'
                        ? 'bg-amber-950/80 border-amber-800 text-amber-300'
                        : 'bg-emerald-950/80 border-emerald-800 text-emerald-300'
                    }`}
                  >
                    {result.risk_level}
                  </div>
                </div>
              </div>

              {/* Automated Decision */}
              <div>{getDecisionBadge(result.decision)}</div>

              {/* Reasons & Rule Breakdown */}
              <div className="space-y-2">
                <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Evaluated Heuristic Rules ({result.rules_triggered.length} Triggered)
                </div>
                <div className="space-y-1.5">
                  {result.reasons.map((r, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 text-xs text-slate-300 flex items-start gap-2.5"
                    >
                      <Info className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
                      <span>{r}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
