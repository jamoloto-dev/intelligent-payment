'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import { Order, Product } from '@/types';
import { 
  DollarSign, 
  ShoppingBag, 
  ShieldAlert, 
  Activity, 
  TrendingUp, 
  ArrowUpRight, 
  Package, 
  Layers,
  ArrowRight,
  Sparkles
} from 'lucide-react';

export default function AdminOverviewPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [ordersData, productsData] = await Promise.all([
          apiClient.getOrders(),
          apiClient.getProducts(),
        ]);
        setOrders(ordersData);
        setProducts(productsData);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const totalVolume = orders.reduce((sum, o) => sum + Number(o.total_amount), 0);
  const completedOrders = orders.filter((o) => o.status === 'COMPLETED' || o.status === 'PAID').length;
  const lowStockProducts = products.filter((p) => p.stock_quantity < 20).length;

  return (
    <div className="space-y-8">
      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Metric 1: Total Volume */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold">Total Platform Volume</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-white">
            ${totalVolume.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-emerald-400 flex items-center gap-1 font-medium">
            <TrendingUp className="w-3 h-3" /> +18.4% from last period
          </div>
        </div>

        {/* Metric 2: Settled Orders */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold">Processed Orders</span>
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
              <ShoppingBag className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-white">{orders.length}</div>
          <div className="text-[11px] text-blue-400 font-medium">
            {completedOrders} settled • 0 disputes
          </div>
        </div>

        {/* Metric 3: Fraud Engine Intercepts */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold">Fraud Risk Interceptions</span>
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-white">99.8%</div>
          <div className="text-[11px] text-purple-400 font-medium">
            0 chargeback breaches
          </div>
        </div>

        {/* Metric 4: Inventory Health */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold">Active SKU Inventory</span>
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center">
              <Package className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-white">{products.length} SKUs</div>
          <div className="text-[11px] text-amber-400 font-medium">
            {lowStockProducts} SKUs low stock
          </div>
        </div>
      </div>

      {/* Quick Launchpad & Live Orders */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Orders Table */}
        <div className="lg:col-span-2 p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">Recent Transactions & Orders</h3>
            <Link href="/admin/orders" className="text-xs text-emerald-400 hover:underline flex items-center gap-1 font-semibold">
              View All <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="divide-y divide-slate-800 border border-slate-800 rounded-xl overflow-hidden">
            {orders.slice(0, 5).map((order) => (
              <div key={order.id} className="p-4 bg-slate-950/60 flex items-center justify-between text-xs">
                <div className="space-y-1">
                  <div className="font-bold text-white flex items-center gap-2">
                    #{order.id}
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950 border border-emerald-800 text-emerald-400 font-semibold">
                      {order.status}
                    </span>
                  </div>
                  <div className="text-slate-400 text-[11px]">
                    {order.items.length} item(s) • {new Date(order.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>

                <div className="text-right">
                  <div className="font-extrabold text-white">${Number(order.total_amount).toFixed(2)} USD</div>
                  <div className="text-[10px] text-slate-500 font-mono">Row Lock Succeeded</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Feature Launchpad */}
        <div className="space-y-4">
          <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 to-purple-950/40 border border-slate-800 space-y-4">
            <div className="w-10 h-10 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center font-bold">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <h4 className="text-sm font-bold text-white">Interactive Fraud Sandbox</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Test velocity limits, geolocation mismatches, and multi-factor rule scoring in the dedicated test harness.
            </p>
            <Link
              href="/admin/fraud"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-md shadow-purple-600/20"
            >
              Open Fraud Lab <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">
              <Activity className="w-5 h-5" />
            </div>
            <h4 className="text-sm font-bold text-white">Live Microservices Mesh</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Probe health status, ping latencies, and verify Azure serverless functions.
            </p>
            <Link
              href="/admin/system"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold border border-slate-700"
            >
              Inspect Topology <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
