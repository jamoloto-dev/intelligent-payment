'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/lib/api';
import { Order, Payment } from '@/types';
import { useApp } from '@/lib/context';
import { 
  ShoppingBag, 
  RotateCcw, 
  Search, 
  CheckCircle2, 
  AlertCircle, 
  Filter,
  RefreshCw,
  ExternalLink,
  X,
  Loader2,
  ShieldCheck
} from 'lucide-react';
import Link from 'next/link';

export default function AdminOrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  
  // Refund Modal State
  const [activeRefundOrder, setActiveRefundOrder] = useState<Order | null>(null);
  const [orderPayments, setOrderPayments] = useState<Payment[]>([]);
  const [selectedPaymentId, setSelectedPaymentId] = useState<string>('');
  const [refundReason, setRefundReason] = useState<string>('');
  const [fetchingPayments, setFetchingPayments] = useState<boolean>(false);
  const [submittingRefund, setSubmittingRefund] = useState<boolean>(false);

  const { showToast } = useApp();

  const loadOrders = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.getOrders({ status: statusFilter });
      setOrders(data);
    } catch (e: any) {
      showToast(e.message || 'Failed to load orders', 'error');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, showToast]);

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  const openRefundModal = async (order: Order) => {
    setActiveRefundOrder(order);
    setRefundReason('');
    setFetchingPayments(true);
    try {
      // 1. Fetch real server-side payment relationship
      const payments = await apiClient.getPaymentsForOrder(order.id);
      const successfulPayments = payments.filter((p) => p.status === 'SUCCEEDED');
      setOrderPayments(successfulPayments);
      if (successfulPayments.length > 0) {
        setSelectedPaymentId(successfulPayments[0].id);
      } else {
        setSelectedPaymentId('');
      }
    } catch (e: any) {
      showToast(e.message || 'Could not fetch payments for this order', 'error');
    } finally {
      setFetchingPayments(false);
    }
  };

  const handleExecuteRefund = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeRefundOrder || !selectedPaymentId) {
      showToast('No valid payment selected for refund', 'error');
      return;
    }
    if (!refundReason.trim() || refundReason.length < 3) {
      showToast('A valid audit reason is required (minimum 3 characters)', 'error');
      return;
    }

    setSubmittingRefund(true);
    try {
      const idempotencyKey = `idemp_ref_${selectedPaymentId}_${Date.now()}`;
      await apiClient.refundPayment(selectedPaymentId, {
        reason: refundReason.trim(),
        idempotency_key: idempotencyKey,
      });

      showToast(`Payment #${selectedPaymentId} successfully refunded`, 'success');
      setActiveRefundOrder(null);
      await loadOrders();
    } catch (err: any) {
      showToast(err.message || 'Refund failed at backend authority', 'error');
    } finally {
      setSubmittingRefund(false);
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
            Manage transactions, check item-level row locks, and issue compliant server-verified refunds.
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
            title="Refresh Orders"
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
                          title="View Customer Receipt"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </Link>

                        {order.status !== 'REFUNDED' && (
                          <button
                            onClick={() => openRefundModal(order)}
                            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 text-[11px] font-semibold transition-colors"
                          >
                            <RotateCcw className="w-3 h-3" />
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

      {/* Refund Execution Modal */}
      {activeRefundOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in">
          <div className="max-w-md w-full rounded-3xl bg-slate-900 border border-slate-800 p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-rose-400">
                <RotateCcw className="w-5 h-5" />
                <h3 className="text-sm font-bold text-white">Issue Order Refund</h3>
              </div>
              <button
                onClick={() => setActiveRefundOrder(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1">
              <div className="flex justify-between text-slate-400">
                <span>Order ID:</span>
                <span className="font-mono text-white font-semibold">{activeRefundOrder.id}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Total Amount:</span>
                <span className="text-emerald-400 font-bold">
                  ${Number(activeRefundOrder.total_amount).toFixed(2)} {activeRefundOrder.currency}
                </span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Customer:</span>
                <span className="font-mono text-slate-300">{activeRefundOrder.user_id}</span>
              </div>
            </div>

            {fetchingPayments ? (
              <div className="py-6 flex flex-col items-center justify-center space-y-2">
                <Loader2 className="w-6 h-6 text-emerald-400 animate-spin" />
                <p className="text-xs text-slate-400">Fetching server payment relationship...</p>
              </div>
            ) : orderPayments.length === 0 ? (
              <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300 space-y-1">
                <p className="font-bold flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4" /> No eligible payment transaction found
                </p>
                <p className="opacity-80">
                  This order has not been completed with a settled payment charge or is already refunded.
                </p>
              </div>
            ) : (
              <form onSubmit={handleExecuteRefund} className="space-y-4 text-xs">
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">
                    Select Target Payment Transaction
                  </label>
                  <select
                    value={selectedPaymentId}
                    onChange={(e) => setSelectedPaymentId(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white font-mono outline-none focus:border-rose-500"
                  >
                    {orderPayments.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.id} — ${Number(p.amount).toFixed(2)} ({p.provider})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">
                    Audit Justification / Refund Reason <span className="text-rose-400">*</span>
                  </label>
                  <textarea
                    required
                    rows={3}
                    placeholder="e.g. Customer returned defective merchandise under RMA-9821."
                    value={refundReason}
                    onChange={(e) => setRefundReason(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white outline-none focus:border-rose-500 resize-none"
                  />
                </div>

                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 text-[11px] text-slate-400 space-y-1">
                  <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Server-side Security Safeguards:
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 opacity-80">
                    <li>Requires <code className="text-emerald-400">payments:refund</code> RBAC permission</li>
                    <li>Records immutable audit ledger event with actor ID and IP</li>
                    <li>Protected with deterministic client idempotency key</li>
                  </ul>
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setActiveRefundOrder(null)}
                    className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingRefund || !selectedPaymentId}
                    className="flex items-center gap-2 px-5 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white text-xs font-bold shadow-lg shadow-rose-600/20"
                  >
                    {submittingRefund ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" /> Processing Refund...
                      </>
                    ) : (
                      <>
                        <RotateCcw className="w-3.5 h-3.5" /> Confirm & Issue Refund
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
