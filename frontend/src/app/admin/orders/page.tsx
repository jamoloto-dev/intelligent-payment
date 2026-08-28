'use client';

import React, { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { Order } from '@/types';
import { useApp } from '@/lib/context';
import { 
  ShoppingBag, 
  RotateCcw, 
  Search, 
  CheckCircle2, 
  AlertCircle, 
  Filter,
  RefreshCw,
  ExternalLink
} from 'lucide-react';
import Link from 'next/link';

export default function AdminOrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [refundingId, setRefundingId] = useState<string | null>(null);
  const { showToast } = useApp();

  const loadOrders = async () => {
    setLoading(true);
    try {
      const data = await apiClient.getOrders();
      setOrders(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrders();
  }, []);

  const handleRefund = async (orderId: string) => {
    setRefundingId(orderId);
    try {
      // Execute refund
      await apiClient.refundPayment(`pay-${orderId}`, 'Admin initiated refund');
      const updated = orders.map((o) => (o.id === orderId ? { ...o, status: 'REFUNDED' as const } : o));
      setOrders(updated);
      showToast(`Order #${orderId} has been successfully refunded`, 'success');
    } catch (err: any) {
      showToast(err.message || 'Refund failed', 'error');
    } finally {
      setRefundingId(null);
    }
  };

  const filteredOrders = orders.filter((o) => {
    if (statusFilter === 'ALL') return true;
    return o.status === statusFilter;
  });

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-slate-900 border border-slate-800">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <ShoppingBag className="w-5 h-5 text-emerald-400" />
            Order Ledger & Idempotent Refunds
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Manage transactions, check item-level row locks, and issue compliant refunds.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white outline-none"
          >
            <option value="ALL">All Statuses</option>
            <option value="PAID">PAID</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="PENDING">PENDING</option>
            <option value="REFUNDED">REFUNDED</option>
          </select>

          <button
            onClick={loadOrders}
            className="p-2.5 rounded-xl bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Orders Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="px-6 py-4">Order ID & Date</th>
                <th className="px-6 py-4">Customer & Address</th>
                <th className="px-6 py-4">Line Items</th>
                <th className="px-6 py-4">Total Amount</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-800/80">
              {filteredOrders.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                    No orders found matching your filter criteria.
                  </td>
                </tr>
              ) : (
                filteredOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-bold text-white font-mono">{order.id}</div>
                      <div className="text-[11px] text-slate-500">{new Date(order.created_at).toLocaleDateString()}</div>
                    </td>

                    <td className="px-6 py-4">
                      <div className="text-slate-300 font-medium line-clamp-1">{order.shipping_address}</div>
                      <div className="text-[10px] text-slate-500 font-mono">{order.user_id}</div>
                    </td>

                    <td className="px-6 py-4">
                      <div className="space-y-0.5">
                        {order.items.map((it, idx) => (
                          <div key={idx} className="text-slate-300 text-[11px]">
                            {it.quantity}x {it.product_name}
                          </div>
                        ))}
                      </div>
                    </td>

                    <td className="px-6 py-4">
                      <div className="font-extrabold text-white">
                        ${Number(order.total_amount).toFixed(2)} {order.currency}
                      </div>
                    </td>

                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold border ${
                          order.status === 'REFUNDED'
                            ? 'bg-rose-950/80 border-rose-800 text-rose-300'
                            : order.status === 'COMPLETED' || order.status === 'PAID'
                            ? 'bg-emerald-950/80 border-emerald-800 text-emerald-300'
                            : 'bg-amber-950/80 border-amber-800 text-amber-300'
                        }`}
                      >
                        {order.status}
                      </span>
                    </td>

                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          href={`/orders/${order.id}`}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white"
                          title="View Receipt"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </Link>

                        {order.status !== 'REFUNDED' && (
                          <button
                            onClick={() => handleRefund(order.id)}
                            disabled={refundingId === order.id}
                            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 text-[11px] font-semibold transition-colors"
                          >
                            <RotateCcw className={`w-3 h-3 ${refundingId === order.id ? 'animate-spin' : ''}`} />
                            Refund
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
