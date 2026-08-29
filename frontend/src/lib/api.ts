import { Product, User, Order, Payment, FraudCheckRequest, FraudCheckResponse, ServiceHealth, TokenResponse } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000';

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

    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({ message: res.statusText }));
      const msg = errorBody.message || (typeof errorBody.detail === 'string' ? errorBody.detail : (errorBody.detail?.message || errorBody.error || `HTTP ${res.status}`));
      throw new Error(msg);
    }

    // Handle 204 No Content
    if (res.status === 204) {
      return {} as T;
    }

    return await res.json();
  },

  // Authentication
  async login(credentials: { email: string; password: string }): Promise<TokenResponse> {
    const data = await this.request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    if (data?.access_token) {
      this.setToken(data.access_token);
    }
    return data;
  },

  async register(userData: { email: string; password: string; first_name: string; last_name: string; role?: string }): Promise<User> {
    return await this.request<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  },

  async getMe(): Promise<User> {
    return await this.request<User>('/auth/me');
  },

  // Products
  async getProducts(params: { page?: number; page_size?: number; category?: string } = {}): Promise<Product[]> {
    const search = new URLSearchParams();
    if (params.page) search.set('page', params.page.toString());
    if (params.page_size) search.set('page_size', params.page_size.toString());
    if (params.category) search.set('category', params.category);

    const query = search.toString() ? `?${search.toString()}` : '';
    const res = await this.request<any>(`/products${query}`);
    return Array.isArray(res) ? res : res.items || [];
  },

  async getProductById(id: string): Promise<Product> {
    return await this.request<Product>(`/products/${id}`);
  },

  async createProduct(productData: Omit<Product, 'id'>): Promise<Product> {
    return await this.request<Product>('/products', {
      method: 'POST',
      body: JSON.stringify(productData),
    });
  },

  async updateStock(productId: string, newStock: number): Promise<Product> {
    return await this.request<Product>(`/products/${productId}/stock`, {
      method: 'PATCH',
      body: JSON.stringify({ quantity: newStock }),
    }).catch(async () => {
      return await this.request<Product>(`/products/${productId}`, {
        method: 'PUT',
        body: JSON.stringify({ stock_quantity: newStock }),
      });
    });
  },

  // Orders
  async getOrders(params: { page?: number; page_size?: number; status?: string } = {}): Promise<Order[]> {
    const search = new URLSearchParams();
    if (params.page) search.set('page', params.page.toString());
    if (params.page_size) search.set('page_size', params.page_size.toString());
    if (params.status && params.status !== 'ALL') search.set('status', params.status);

    const query = search.toString() ? `?${search.toString()}` : '';
    const res = await this.request<any>(`/orders${query}`);
    return Array.isArray(res) ? res : res.items || [];
  },

  async getOrderById(id: string): Promise<Order> {
    return await this.request<Order>(`/orders/${id}`);
  },

  async createOrder(payload: { items: { product_id: string; quantity: number }[]; shipping_address: string; currency?: string }): Promise<Order> {
    return await this.request<Order>('/orders', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Payments
  async getPaymentsForOrder(orderId: string): Promise<Payment[]> {
    return await this.request<Payment[]>(`/payments/order/${orderId}`);
  },

  async processPayment(payload: { order_id: string; amount: number; currency: string; idempotency_key: string; billing_country?: string; payment_method_id?: string }): Promise<Payment> {
    return await this.request<Payment>('/payments', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async refundPayment(paymentId: string, payload: { reason: string; amount?: number; idempotency_key?: string }): Promise<Payment> {
    return await this.request<Payment>(`/payments/${paymentId}/refund`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Fraud Engine
  async evaluateFraud(data: FraudCheckRequest): Promise<FraudCheckResponse> {
    return await this.request<FraudCheckResponse>('/fraud/check', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Microservices Health Monitor (Backend authority query)
  async checkServicesHealth(): Promise<ServiceHealth[]> {
    const start = performance.now();
    try {
      const res = await this.request<{ service: string; status: string; dependencies?: Record<string, string> }>('/ready');
      const latency = Math.round(performance.now() - start);

      const serviceList: ServiceHealth[] = [
        {
          name: 'API Gateway',
          port: 8000,
          path: '/health',
          status: res.status === 'HEALTHY' ? 'HEALTHY' : 'UNHEALTHY',
          latencyMs: latency,
          details: 'Unified Entrypoint & Router',
        },
      ];

      const portMapping: Record<string, { port: number; path: string; label: string }> = {
        'user-service': { port: 8001, path: '/health', label: 'User & Auth Service' },
        'product-service': { port: 8002, path: '/health', label: 'Product & Stock Service' },
        'order-service': { port: 8003, path: '/health', label: 'Order Orchestrator' },
        'fraud-service': { port: 8004, path: '/health', label: 'Fraud Risk Engine' },
        'payment-service': { port: 8005, path: '/health', label: 'Payment & Outbox Service' },
        'notification-service': { port: 8006, path: '/health', label: 'Notification Service' },
      };

      if (res.dependencies) {
        for (const [svcName, svcStatus] of Object.entries(res.dependencies)) {
          const mapping = portMapping[svcName] || { port: 8080, path: '/health', label: svcName };
          serviceList.push({
            name: mapping.label,
            port: mapping.port,
            path: mapping.path,
            status: svcStatus === 'reachable' ? 'HEALTHY' : 'UNHEALTHY',
            latencyMs: latency,
            details: svcStatus === 'reachable' ? 'Backend Live & Operational' : `Status: ${svcStatus}`,
          });
        }
      }

      return serviceList;
    } catch (err: any) {
      return [
        {
          name: 'API Gateway',
          port: 8000,
          path: '/health',
          status: 'UNHEALTHY',
          latencyMs: 0,
          details: `Gateway unreachable: ${err.message}`,
        },
      ];
    }
  },
};
