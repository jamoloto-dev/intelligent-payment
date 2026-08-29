'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { Order } from '@/types';
import { 
  CheckCircle2, 
  Package, 
  Truck, 
  ShieldCheck, 
  ArrowLeft, 
  Clock, 
  CreditCard,
  Building,
  Sparkles
} from 'lucide-react';

export default function OrderTrackingPage() {
  const params = useParams();
  const orderId = params.id as string;
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadOrder() {
      try {
        const found = await apiClient.getOrderById(orderId);
        setOrder(found);
      } catch (err) {
        console.error('Failed to retrieve order from backend:', err);
      } finally {
        setLoading(false);
      }
    }
    if (orderId) {
      loadOrder();
    }
  }, [orderId]);

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center space-y-4">
        <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-xs text-slate-400">Loading Order Ledger...</p>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center space-y-4">
        <h2 className="text-xl font-bold text-white">Order Not Found</h2>
        <Link href="/" className="inline-flex items-center gap-2 text-xs text-emerald-400 hover:underline">
          <ArrowLeft className="w-4 h-4" /> Back to Store
        </Link>
      </div>
    );
  }

  const steps = [
    { label: 'Order Placed', status: 'completed', icon: <Package className="w-4 h-4" /> },
    { label: 'Payment Settled', status: 'completed', icon: <CreditCard className="w-4 h-4" /> },
    { label: 'Fraud Shield Cleared', status: 'completed', icon: <ShieldCheck className="w-4 h-4" /> },
    { label: 'Dispatched to Delivery', status: order.status === 'COMPLETED' ? 'completed' : 'active', icon: <Truck className="w-4 h-4" /> },
  ];

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <Link href="/" className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white">
        <ArrowLeft className="w-3.5 h-3.5" /> Return to Catalog
      </Link>

      <div className="p-8 rounded-3xl bg-slate-900 border border-slate-800 space-y-6 shadow-2xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[11px] uppercase font-bold text-emerald-400 tracking-wider">
                Transaction Successful
              </span>
              <h1 className="text-xl font-extrabold text-white">Order #{order.id}</h1>
            </div>
          </div>

          <div className="px-3.5 py-1.5 rounded-full bg-emerald-950/80 border border-emerald-800 text-emerald-300 text-xs font-semibold self-start sm:self-auto">
            Status: {order.status}
          </div>
        </div>

        <div className="py-6 border-y border-slate-800 grid grid-cols-2 sm:grid-cols-4 gap-4">
          {steps.map((step, idx) => (
            <div key={idx} className="flex flex-col items-center text-center space-y-2">
              <div
                className={`w-9 h-9 rounded-xl flex items-center justify-center ${
                  step.status === 'completed'
                    ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30'
                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                }`}
              >
                {step.icon}
              </div>
              <span className="text-xs font-semibold text-slate-200">{step.label}</span>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-xs">
          <div className="space-y-1.5 p-4 rounded-xl bg-slate-950 border border-slate-800">
            <div className="text-slate-400 font-semibold">Shipping Destination</div>
            <div className="text-white font-medium">{order.shipping_address}</div>
          </div>

          <div className="space-y-1.5 p-4 rounded-xl bg-slate-950 border border-slate-800">
            <div className="text-slate-400 font-semibold">Ledger Timestamp</div>
            <div className="text-white font-medium">{new Date(order.created_at).toLocaleString()}</div>
          </div>
        </div>

        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Order Items</h3>
          <div className="divide-y divide-slate-800 border border-slate-800 rounded-2xl overflow-hidden">
            {order.items.map((item, idx) => (
              <div key={idx} className="p-4 bg-slate-950/60 flex items-center justify-between text-xs">
                <div>
                  <div className="font-bold text-white">{item.product_name}</div>
                  <div className="text-slate-400 text-[11px]">Qty: {item.quantity} × ${Number(item.unit_price).toFixed(2)}</div>
                </div>
                <div className="font-bold text-white">${Number(item.subtotal).toFixed(2)} USD</div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between p-4 rounded-2xl bg-emerald-950/20 border border-emerald-800/40">
          <div className="flex items-center gap-2 text-xs text-emerald-300">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Azure Serverless Audit Trail Recorded</span>
          </div>
          <div className="text-base font-extrabold text-emerald-400">
            Total: ${Number(order.total_amount).toFixed(2)} {order.currency}
          </div>
        </div>
      </div>
    </div>
  );
}
