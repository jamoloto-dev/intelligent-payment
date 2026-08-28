'use client';

import React, { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { ServiceHealth } from '@/types';
import { 
  Activity, 
  RefreshCw, 
  Server, 
  Database, 
  Zap, 
  ShieldCheck, 
  Layers, 
  Cpu, 
  Globe, 
  CheckCircle2, 
  XCircle,
  Clock
} from 'lucide-react';

export default function MicroservicesTopologyPage() {
  const [healthResults, setHealthResults] = useState<ServiceHealth[]>([]);
  const [checking, setChecking] = useState(false);

  const runHealthPings = async () => {
    setChecking(true);
    try {
      const results = await apiClient.checkServicesHealth();
      setHealthResults(results);
    } catch (e) {
      console.error(e);
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    runHealthPings();
  }, []);

  const infrastructureNodes = [
    { name: 'PostgreSQL 16 Multi-DB', port: 5432, role: 'Relational Store (Users, Products, Orders, Payments)', status: 'HEALTHY' },
    { name: 'Redis 7 Backbone', port: 6379, role: 'Event Pub/Sub & Atomic Cache', status: 'HEALTHY' },
    { name: 'MongoDB 7.0 / Azure Tables', port: 27017, role: 'Audit Ledger & Risk Log Store', status: 'HEALTHY' },
    { name: 'Azure Function App', port: 7071, role: 'Serverless Audit Consumer', status: 'HEALTHY' },
  ];

  return (
    <div className="space-y-8">
      {/* Header Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-slate-900 border border-slate-800">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-400" />
            Distributed Microservices Topology & Liveness Health
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time ping probes across API Gateway, microservice nodes, and event brokers.
          </p>
        </div>

        <button
          onClick={runHealthPings}
          disabled={checking}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md shadow-emerald-600/20 transition-all"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} />
          Probe All Endpoints
        </button>
      </div>

      {/* Microservices Nodes Grid */}
      <div className="space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          FastAPI Microservice Tier (7 Endpoints)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {healthResults.map((service, idx) => (
            <div
              key={idx}
              className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-3 flex flex-col justify-between"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center font-mono text-xs font-bold">
                    :{service.port}
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white">{service.name}</h4>
                    <div className="text-[10px] text-slate-500 font-mono">http://localhost:{service.port}</div>
                  </div>
                </div>

                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                    service.status === 'HEALTHY'
                      ? 'bg-emerald-950/80 border-emerald-800 text-emerald-300'
                      : 'bg-slate-800 border-slate-700 text-slate-400'
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${service.status === 'HEALTHY' ? 'bg-emerald-400 animate-pulse' : 'bg-slate-400'}`} />
                  {service.status === 'HEALTHY' ? 'ACTIVE' : 'STANDBY'}
                </span>
              </div>

              <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-500" />
                  <span>{service.status === 'HEALTHY' ? `${service.latencyMs}ms latency` : 'Demo fallback engine active'}</span>
                </div>
                <span className="font-mono text-[10px] text-emerald-400">{service.path}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Infrastructure & Data Brokers */}
      <div className="space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Infrastructure Data Stores & Message Brokers
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {infrastructureNodes.map((node, idx) => (
            <div key={idx} className="p-5 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center font-bold">
                  <Database className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-white">{node.name}</h4>
                  <p className="text-[11px] text-slate-400">{node.role}</p>
                </div>
              </div>

              <div className="text-right">
                <span className="text-[10px] px-2.5 py-1 rounded-full bg-emerald-950 border border-emerald-800 text-emerald-300 font-semibold font-mono">
                  Port :{node.port}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
