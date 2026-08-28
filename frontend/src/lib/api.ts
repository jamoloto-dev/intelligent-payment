import { Product, User, Order, Payment, FraudCheckRequest, FraudCheckResponse, ServiceHealth } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000';

// Default initial catalog
export const INITIAL_PRODUCTS: Product[] = [
  {
    id: 'prod-001',
    name: 'Quantum Sound ANC Headphones',
    description: 'Spatial audio with 45dB hybrid active noise cancellation, 40-hour battery life and multi-point Bluetooth 5.4.',
    price: 299.99,
    currency: 'USD',
    stock_quantity: 42,
    category: 'Audio',
    image_url: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&auto=format&fit=crop&q=80'
  },
  {
    id: 'prod-002',
    name: 'UltraWide Curved 34" Monitor',
    description: '144Hz WQHD IPS Nano-display, 1ms response time, USB-C 90W power delivery for seamless workstation productivity.',
    price: 649.50,
    currency: 'USD',
    stock_quantity: 18,
    category: 'Displays',
    image_url: 'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=800&auto=format&fit=crop&q=80'
  },
  {
    id: 'prod-003',
    name: 'Mechanical RGB Developer Keyboard',
    description: 'Hot-swappable tactile switches, gasket-mounted sound dampening, CNC anodized aluminum case with PBT keycaps.',
    price: 189.00,
    currency: 'USD',
    stock_quantity: 65,
    category: 'Peripherals',
    image_url: 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=800&auto=format&fit=crop&q=80'
  },
  {
    id: 'prod-004',
    name: 'Ergonomic Precision Wireless Mouse',
    description: 'Dual sensor 26,000 DPI optical tracking with magnetic hyper-scroll wheel and ergonomic thumb rest.',
    price: 99.99,
    currency: 'USD',
    stock_quantity: 90,
    category: 'Peripherals',
    image_url: 'https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=800&auto=format&fit=crop&q=80'
  },
  {
    id: 'prod-005',
    name: 'Titanium Smartwatch Pro Ultra',
    description: 'ECG heart rate sensor, dual-frequency GPS, sapphire crystal glass with 100m water resistance rating.',
    price: 499.00,
    currency: 'USD',
    stock_quantity: 24,
    category: 'Wearables',
    image_url: 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&auto=format&fit=crop&q=80'
  },
  {
    id: 'prod-006',
    name: '4K AI HDR Streaming Webcam',
    description: 'Sony STARVIS CMOS sensor, automatic subject tracking, integrated dual noise-canceling stereo microphones.',
    price: 149.95,
    currency: 'USD',
    stock_quantity: 35,
    category: 'Video',
    image_url: 'https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=800&auto=format&fit=crop&q=80'
  }
];

export const DEMO_USERS: User[] = [
  {
    id: 'usr-customer-01',
    email: 'customer@intelligentpay.io',
    first_name: 'Alex',
    last_name: 'Morgan',
    role: 'USER',
    is_active: true
  },
  {
    id: 'usr-admin-01',
    email: 'admin@intelligentpay.io',
    first_name: 'Sarah',
    last_name: 'Connor',
    role: 'ADMIN',
    is_active: true
  }
];

// In-browser mock storage helpers for fallback
const getStored = <T>(key: string, defaultVal: T): T => {
  if (typeof window === 'undefined') return defaultVal;
  try {
    const item = localStorage.getItem(`ip_${key}`);
    return item ? JSON.parse(item) : defaultVal;
  } catch {
    return defaultVal;
  }
};

const setStored = <T>(key: string, val: T): void => {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(`ip_${key}`, JSON.stringify(val));
  } catch (e) {
    console.error('Storage write error', e);
  }
};

export const apiClient = {
  getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('ip_token');
  },

  setToken(token: string | null): void {
    if (typeof window === 'undefined') return;
    if (token) {
      localStorage.setItem('ip_token', token);
    } else {
      localStorage.removeItem('ip_token');
    }
  },

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...((options.headers as Record<string, string>) || {}),
    };

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
      });

      if (!res.ok) {
        const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errorBody.detail || `Request failed with status ${res.status}`);
      }

      return await res.json();
    } catch (err: any) {
      console.warn(`Gateway live call to ${endpoint} failed (${err.message}). Using local engine fallback.`);
      throw err;
    }
  },

  // Products
  async getProducts(): Promise<Product[]> {
    try {
      return await this.request<Product[]>('/products');
    } catch {
      const stored = getStored<Product[]>('products', INITIAL_PRODUCTS);
      return stored;
    }
  },

  async getProductById(id: string): Promise<Product | null> {
    try {
      return await this.request<Product>(`/products/${id}`);
    } catch {
      const products = getStored<Product[]>('products', INITIAL_PRODUCTS);
      return products.find(p => p.id === id) || null;
    }
  },

  async createProduct(productData: Omit<Product, 'id'>): Promise<Product> {
    try {
      return await this.request<Product>('/products', {
        method: 'POST',
        body: JSON.stringify(productData),
      });
    } catch {
      const products = getStored<Product[]>('products', INITIAL_PRODUCTS);
      const newProduct: Product = {
        ...productData,
        id: `prod-${Date.now().toString().slice(-4)}`,
      };
      products.unshift(newProduct);
      setStored('products', products);
      return newProduct;
    }
  },

  async updateStock(productId: string, newStock: number): Promise<Product> {
    const products = getStored<Product[]>('products', INITIAL_PRODUCTS);
    const index = products.findIndex(p => p.id === productId);
    if (index !== -1) {
      products[index].stock_quantity = newStock;
      setStored('products', products);
      return products[index];
    }
    throw new Error('Product not found');
  },

  // Orders
  async getOrders(): Promise<Order[]> {
    try {
      return await this.request<Order[]>('/orders');
    } catch {
      return getStored<Order[]>('orders', [
        {
          id: 'ord-8921-a',
          user_id: 'usr-customer-01',
          status: 'COMPLETED',
          total_amount: 599.98,
          currency: 'USD',
          shipping_address: '742 Evergreen Terrace, Springfield, OR',
          items: [
            {
              product_id: 'prod-001',
              product_name: 'Quantum Sound ANC Headphones',
              quantity: 2,
              unit_price: 299.99,
              subtotal: 599.98
            }
          ],
          created_at: new Date(Date.now() - 3600000 * 5).toISOString()
        },
        {
          id: 'ord-8922-b',
          user_id: 'usr-customer-01',
          status: 'PAID',
          total_amount: 649.50,
          currency: 'USD',
          shipping_address: '100 Market St, San Francisco, CA',
          items: [
            {
              product_id: 'prod-002',
              product_name: 'UltraWide Curved 34" Monitor',
              quantity: 1,
              unit_price: 649.50,
              subtotal: 649.50
            }
          ],
          created_at: new Date(Date.now() - 3600000 * 2).toISOString()
        }
      ]);
    }
  },

  async createOrder(payload: { items: { product_id: string; quantity: number }[]; shipping_address: string; currency?: string }): Promise<Order> {
    try {
      return await this.request<Order>('/orders', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    } catch {
      const products = getStored<Product[]>('products', INITIAL_PRODUCTS);
      const orders = getStored<Order[]>('orders', []);
      
      const orderItems = payload.items.map(item => {
        const prod = products.find(p => p.id === item.product_id);
        const price = prod ? prod.price : 100;
        return {
          id: `item-${Math.random().toString(36).slice(2, 7)}`,
          product_id: item.product_id,
          product_name: prod ? prod.name : 'Selected Product',
          quantity: item.quantity,
          unit_price: price,
          subtotal: price * item.quantity,
        };
      });

      const total = orderItems.reduce((sum, it) => sum + Number(it.subtotal), 0);

      // Decrement inventory
      payload.items.forEach(it => {
        const prod = products.find(p => p.id === it.product_id);
        if (prod) {
          prod.stock_quantity = Math.max(0, prod.stock_quantity - it.quantity);
        }
      });
      setStored('products', products);

      const newOrder: Order = {
        id: `ord-${Math.floor(1000 + Math.random() * 9000)}-${Date.now().toString(36).slice(-3)}`,
        user_id: 'usr-customer-01',
        status: 'PENDING',
        total_amount: total,
        currency: payload.currency || 'USD',
        shipping_address: payload.shipping_address,
        items: orderItems,
        created_at: new Date().toISOString(),
      };

      orders.unshift(newOrder);
      setStored('orders', orders);
      return newOrder;
    }
  },

  // Payments
  async processPayment(payload: { order_id: string; amount: number; currency: string; idempotency_key: string; billing_country?: string }): Promise<Payment> {
    try {
      return await this.request<Payment>('/payments', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    } catch {
      const orders = getStored<Order[]>('orders', []);
      const payments = getStored<Payment[]>('payments', []);

      // Check idempotency
      const existing = payments.find(p => p.idempotency_key === payload.idempotency_key);
      if (existing) {
        return existing;
      }

      const payment: Payment = {
        id: `pay-${Math.random().toString(36).slice(2, 10)}`,
        order_id: payload.order_id,
        user_id: 'usr-customer-01',
        amount: payload.amount,
        currency: payload.currency,
        provider: 'mock_sandbox',
        provider_transaction_id: `ch_mock_${Math.random().toString(36).slice(2, 12)}`,
        status: 'SUCCEEDED',
        idempotency_key: payload.idempotency_key,
        created_at: new Date().toISOString(),
      };

      payments.unshift(payment);
      setStored('payments', payments);

      // Update Order Status
      const order = orders.find(o => o.id === payload.order_id);
      if (order) {
        order.status = 'PAID';
        setStored('orders', orders);
      }

      return payment;
    }
  },

  async refundPayment(paymentId: string, reason: string): Promise<Payment> {
    try {
      return await this.request<Payment>(`/payments/${paymentId}/refund`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      });
    } catch {
      const payments = getStored<Payment[]>('payments', []);
      const pay = payments.find(p => p.id === paymentId);
      if (pay) {
        pay.status = 'REFUNDED';
        setStored('payments', payments);
        return pay;
      }
      throw new Error('Payment not found');
    }
  },

  // Fraud Engine
  async evaluateFraud(data: FraudCheckRequest): Promise<FraudCheckResponse> {
    try {
      return await this.request<FraudCheckResponse>('/fraud/check', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    } catch {
      // Deterministic client-side evaluation matching backend rules
      let score = 0;
      const reasons: string[] = [];
      const rules: string[] = [];

      if (data.amount > 5000) {
        score += 50;
        reasons.push(`Critical transaction amount ($${data.amount.toFixed(2)}) exceeds $5,000 threshold`);
        rules.push('CriticalAmountRule');
      } else if (data.amount > 1500) {
        score += 25;
        reasons.push(`High transaction amount ($${data.amount.toFixed(2)}) requires additional verification`);
        rules.push('HighAmountRule');
      }

      if (data.recent_transactions_count_1h > 5) {
        score += 40;
        reasons.push(`Velocity alert: ${data.recent_transactions_count_1h} transactions in 1 hour (limit: 5)`);
        rules.push('HighVelocityRule');
      }

      if (data.recent_failed_payments_24h >= 3) {
        score += 35;
        reasons.push(`Repeated payment failures: ${data.recent_failed_payments_24h} failures in 24 hours`);
        rules.push('RepeatedFailuresRule');
      }

      if (data.billing_country && data.ip_country && data.billing_country !== data.ip_country) {
        score += 30;
        reasons.push(`Geolocation mismatch: Billing '${data.billing_country}' != IP '${data.ip_country}'`);
        rules.push('GeolocationMismatchRule');
      }

      score = Math.min(100, Math.max(0, score));

      let level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' = 'LOW';
      let decision: 'APPROVE' | 'REVIEW' | 'REJECT' = 'APPROVE';

      if (score >= 75) {
        level = 'CRITICAL';
        decision = 'REJECT';
      } else if (score >= 45) {
        level = 'HIGH';
        decision = 'REVIEW';
      } else if (score >= 20) {
        level = 'MEDIUM';
        decision = 'REVIEW';
      } else {
        level = 'LOW';
        decision = 'APPROVE';
      }

      return {
        transaction_id: data.transaction_id,
        order_id: data.order_id,
        user_id: data.user_id,
        risk_score: score,
        risk_level: level,
        decision,
        reasons: reasons.length > 0 ? reasons : ['Transaction passes all baseline fraud heuristic rules'],
        rules_triggered: rules,
      };
    }
  },

  // Microservices Health Monitor
  async checkServicesHealth(): Promise<ServiceHealth[]> {
    const services = [
      { name: 'API Gateway', port: 8000, path: '/health' },
      { name: 'User Service', port: 8001, path: '/health' },
      { name: 'Product Service', port: 8002, path: '/health' },
      { name: 'Order Service', port: 8003, path: '/health' },
      { name: 'Fraud Service', port: 8004, path: '/health' },
      { name: 'Payment Service', port: 8005, path: '/health' },
      { name: 'Notification Service', port: 8006, path: '/health' },
    ];

    const results: ServiceHealth[] = await Promise.all(
      services.map(async (s) => {
        const start = performance.now();
        try {
          const res = await fetch(`http://localhost:${s.port}${s.path}`, {
            method: 'GET',
            signal: AbortSignal.timeout(1500),
          });
          const latency = Math.round(performance.now() - start);
          if (res.ok) {
            return { name: s.name, port: s.port, path: s.path, status: 'HEALTHY', latencyMs: latency, details: 'Active & Responding' };
          }
          return { name: s.name, port: s.port, path: s.path, status: 'UNHEALTHY', latencyMs: latency, details: `HTTP ${res.status}` };
        } catch {
          return { name: s.name, port: s.port, path: s.path, status: 'UNHEALTHY', latencyMs: 0, details: 'Service Offline / Unreachable' };
        }
      })
    );

    return results;
  }
};
