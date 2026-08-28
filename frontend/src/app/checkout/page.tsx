'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useApp } from '@/lib/context';
import { apiClient } from '@/lib/api';
import { 
  ShieldCheck, 
  CreditCard, 
  Lock, 
  Zap, 
  CheckCircle2, 
  AlertTriangle, 
  ArrowLeft, 
  Sparkles,
  RefreshCw,
  Globe,
  Sliders
} from 'lucide-react';
import Link from 'next/link';

export default function CheckoutPage() {
  const router = useRouter();
  const { cart, cartTotal, clearCart, showToast, user } = useApp();

  // Form State
  const [shippingAddress, setShippingAddress] = useState('123 Silicon Valley Blvd, Suite 400, San Jose, CA 95134');
  const [billingCountry, setBillingCountry] = useState('US');
  const [ipCountry, setIpCountry] = useState('US');
  const [provider, setProvider] = useState<'mock_sandbox' | 'stripe'>('mock_sandbox');
  const [idempotencyKey, setIdempotencyKey] = useState(`idem_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`);

  // Fraud Simulation triggers
  const [simulateHighVelocity, setSimulateHighVelocity] = useState(false);
  const [simulatePastFailures, setSimulatePastFailures] = useState(false);

  // Processing State
  const [isProcessing, setIsProcessing] = useState(false);
  const [stepStatus, setStepStatus] = useState<{
    orderCreated?: boolean;
    fraudEvaluated?: boolean;
    paymentCharged?: boolean;
    fraudResult?: any;
    error?: string;
  }>({});

  const generateNewIdempotencyKey = () => {
    setIdempotencyKey(`idem_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`);
  };

  const handleCheckout = async (e: React.FormEvent) => {
    e.preventDefault();
    if (cart.length === 0) {
      showToast('Your cart is empty', 'error');
      return;
    }

    setIsProcessing(true);
    setStepStatus({});

    try {
      // Step 1: Create Order with Atomic Inventory Reservation
      const orderPayload = {
        items: cart.map((item) => ({
          product_id: item.product.id,
          quantity: item.quantity,
        })),
        shipping_address: shippingAddress,
        currency: 'USD',
      };

      const order = await apiClient.createOrder(orderPayload);
      setStepStatus((prev) => ({ ...prev, orderCreated: true }));

      // Step 2: Fraud Evaluation Check
      const fraudCheckPayload = {
        transaction_id: `tx_${Date.now().toString(36)}`,
        order_id: order.id,
        user_id: user?.id || 'usr-customer-01',
        amount: Number(order.total_amount),
        currency: 'USD',
        recent_transactions_count_1h: simulateHighVelocity ? 8 : 1,
        recent_failed_payments_24h: simulatePastFailures ? 4 : 0,
        billing_country: billingCountry,
        ip_country: ipCountry,
      };

      const fraudResult = await apiClient.evaluateFraud(fraudCheckPayload);
      setStepStatus((prev) => ({ ...prev, fraudEvaluated: true, fraudResult }));

      if (fraudResult.decision === 'REJECT') {
        setStepStatus((prev) => ({
          ...prev,
          error: `Transaction Rejected by Fraud Shield: ${fraudResult.reasons.join(', ')}`,
        }));
        showToast('Payment blocked by Fraud Risk Engine', 'error');
        return;
      }

      // Step 3: Process Payment with Idempotency Key
      const paymentPayload = {
        order_id: order.id,
        amount: Number(order.total_amount),
        currency: 'USD',
        idempotency_key: idempotencyKey,
        billing_country: billingCountry,
      };

      const payment = await apiClient.processPayment(paymentPayload);
      setStepStatus((prev) => ({ ...prev, paymentCharged: true }));

      // Clear cart on success
      clearCart();
      showToast('Payment processed successfully!', 'success');

      // Navigate to order confirmation
      setTimeout(() => {
        router.push(`/orders/${order.id}`);
      }, 1500);

    } catch (err: any) {
      setStepStatus((prev) => ({ ...prev, error: err.message || 'Payment processing failed' }));
      showToast(err.message || 'Payment failed', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  if (cart.length === 0 && !isProcessing && !stepStatus.paymentCharged) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center space-y-4">
        <div className="w-16 h-16 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-slate-400">
          <CreditCard className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-white">Your Cart is Empty</h2>
        <p className="text-sm text-slate-400">Add products to your cart from the storefront to test checkout.</p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs shadow-lg shadow-emerald-600/20"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Storefront
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <Link href="/" className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white mb-2">
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Store
          </Link>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Checkout & Transaction Pipeline
          </h1>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
          <Lock className="w-3.5 h-3.5" />
          256-Bit Encrypted
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Checkout Form */}
        <div className="lg:col-span-2 space-y-6">
          <form onSubmit={handleCheckout} className="space-y-6">
            {/* Step 1: Shipping Address */}
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-xs flex items-center justify-center font-bold">1</span>
                Shipping Address
              </h3>
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">Delivery Destination</label>
                <input
                  type="text"
                  required
                  value={shippingAddress}
                  onChange={(e) => setShippingAddress(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none"
                />
              </div>
            </div>

            {/* Step 2: Payment Provider & Idempotency */}
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-xs flex items-center justify-center font-bold">2</span>
                Payment Provider & Idempotency Safeguard
              </h3>

              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setProvider('mock_sandbox')}
                  className={`p-3.5 rounded-xl border text-left transition-all ${
                    provider === 'mock_sandbox'
                      ? 'border-emerald-500 bg-emerald-950/20 text-white shadow-sm'
                      : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-emerald-400" />
                    Mock Sandbox
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">
                    Deterministic zero-failure simulator
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setProvider('stripe')}
                  className={`p-3.5 rounded-xl border text-left transition-all ${
                    provider === 'stripe'
                      ? 'border-emerald-500 bg-emerald-950/20 text-white shadow-sm'
                      : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    <CreditCard className="w-3.5 h-3.5 text-blue-400" />
                    Stripe Elements API
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">
                    Live/Test Stripe API provider
                  </div>
                </button>
              </div>

              {/* Idempotency Key display & regenerator */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <label className="font-semibold text-slate-400 flex items-center gap-1.5">
                    <Lock className="w-3 h-3 text-emerald-400" />
                    Idempotency-Key Header
                  </label>
                  <button
                    type="button"
                    onClick={generateNewIdempotencyKey}
                    className="text-[11px] text-emerald-400 hover:underline flex items-center gap-1"
                  >
                    <RefreshCw className="w-3 h-3" /> Regenerate
                  </button>
                </div>
                <input
                  type="text"
                  readOnly
                  value={idempotencyKey}
                  className="w-full font-mono text-[11px] px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 select-all"
                />
                <p className="text-[10px] text-slate-500">
                  Prevents duplicate credit card billing if network retries occur.
                </p>
              </div>
            </div>

            {/* Step 3: Fraud Risk Engine Simulator Settings */}
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-xs flex items-center justify-center font-bold">3</span>
                  Fraud Risk Engine Parameters
                </h3>
                <span className="text-[10px] uppercase font-bold text-amber-400 bg-amber-950/40 border border-amber-800/60 px-2 py-0.5 rounded-full">
                  Interactive Simulator
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Billing Country</label>
                  <select
                    value={billingCountry}
                    onChange={(e) => setBillingCountry(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white outline-none"
                  >
                    <option value="US">United States (US)</option>
                    <option value="GB">United Kingdom (GB)</option>
                    <option value="DE">Germany (DE)</option>
                    <option value="CA">Canada (CA)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Detected IP Country</label>
                  <select
                    value={ipCountry}
                    onChange={(e) => setIpCountry(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white outline-none"
                  >
                    <option value="US">United States (US)</option>
                    <option value="RU">Russia (RU) [Mismatch Trigger]</option>
                    <option value="NG">Nigeria (NG) [Mismatch Trigger]</option>
                    <option value="GB">United Kingdom (GB)</option>
                  </select>
                </div>
              </div>

              <div className="space-y-2 pt-2 border-t border-slate-800">
                <label className="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={simulateHighVelocity}
                    onChange={(e) => setSimulateHighVelocity(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-950 text-emerald-500 focus:ring-0"
                  />
                  <span>Simulate High Velocity (8 transactions in past 1 hour)</span>
                </label>

                <label className="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={simulatePastFailures}
                    onChange={(e) => setSimulatePastFailures(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-950 text-emerald-500 focus:ring-0"
                  />
                  <span>Simulate Multiple Card Decline Failures in 24h</span>
                </label>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isProcessing}
              className={`w-full py-4 rounded-2xl text-sm font-bold flex items-center justify-center gap-2 shadow-xl transition-all ${
                isProcessing
                  ? 'bg-slate-800 text-slate-400 cursor-wait'
                  : 'bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white shadow-emerald-600/30'
              }`}
            >
              {isProcessing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Executing Transaction Pipeline...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 fill-white" />
                  Authorize & Pay ${cartTotal.toFixed(2)} USD
                </>
              )}
            </button>
          </form>
        </div>

        {/* Order Summary & Pipeline Monitor */}
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
            <h3 className="text-sm font-bold text-white">Order Summary</h3>
            <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
              {cart.map((item) => (
                <div key={item.product.id} className="flex justify-between text-xs">
                  <div>
                    <div className="font-semibold text-white line-clamp-1">{item.product.name}</div>
                    <div className="text-slate-400 text-[11px]">Qty: {item.quantity} × ${item.product.price.toFixed(2)}</div>
                  </div>
                  <div className="font-bold text-white">${(item.product.price * item.quantity).toFixed(2)}</div>
                </div>
              ))}
            </div>

            <div className="pt-4 border-t border-slate-800 space-y-2 text-xs">
              <div className="flex justify-between text-slate-400">
                <span>Subtotal</span>
                <span>${cartTotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Inventory Pessimistic Lock</span>
                <span className="text-emerald-400 font-medium">Acquired (0ms)</span>
              </div>
              <div className="flex justify-between text-sm font-extrabold text-white pt-2 border-t border-slate-800">
                <span>Total Charge</span>
                <span className="text-emerald-400">${cartTotal.toFixed(2)} USD</span>
              </div>
            </div>
          </div>

          {/* Real-time Pipeline Step Indicator */}
          {(isProcessing || stepStatus.orderCreated || stepStatus.error) && (
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-3 animate-in fade-in">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Pipeline Orchestrator
              </h4>

              <div className="space-y-2.5 text-xs">
                {/* Step 1 */}
                <div className="flex items-center gap-2.5">
                  {stepStatus.orderCreated ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <RefreshCw className="w-4 h-4 text-slate-500 animate-spin" />
                  )}
                  <span className={stepStatus.orderCreated ? 'text-white' : 'text-slate-500'}>
                    Atomic Stock Reservation (Order Created)
                  </span>
                </div>

                {/* Step 2 */}
                <div className="flex items-center gap-2.5">
                  {stepStatus.fraudEvaluated ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-slate-700" />
                  )}
                  <span className={stepStatus.fraudEvaluated ? 'text-white' : 'text-slate-500'}>
                    Heuristic Risk Scoring ({stepStatus.fraudResult?.risk_level || 'Checking...'})
                  </span>
                </div>

                {/* Step 3 */}
                <div className="flex items-center gap-2.5">
                  {stepStatus.paymentCharged ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-slate-700" />
                  )}
                  <span className={stepStatus.paymentCharged ? 'text-white' : 'text-slate-500'}>
                    Idempotent Provider Charge
                  </span>
                </div>
              </div>

              {/* Fraud Warning / Rejection Alert */}
              {stepStatus.error && (
                <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-300 text-xs space-y-1 mt-3">
                  <div className="font-bold flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4" />
                    Checkout Pipeline Halted
                  </div>
                  <p className="text-[11px] opacity-90">{stepStatus.error}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
