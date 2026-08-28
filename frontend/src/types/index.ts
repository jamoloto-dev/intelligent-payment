export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: 'USER' | 'ADMIN';
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
}

export interface Product {
  id: string;
  name: string;
  description: string;
  price: number;
  currency: string;
  stock_quantity: number;
  image_url?: string;
  category?: string;
}

export interface CartItem {
  product: Product;
  quantity: number;
}

export interface OrderItem {
  id?: string;
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number | string;
  subtotal: number | string;
}

export interface Order {
  id: string;
  user_id: string;
  status: 'PENDING' | 'PAID' | 'PROCESSING' | 'COMPLETED' | 'CANCELLED' | 'REFUNDED';
  total_amount: number | string;
  currency: string;
  shipping_address: string;
  items: OrderItem[];
  created_at: string;
  updated_at?: string;
}

export interface PaymentRequest {
  order_id: string;
  amount: number;
  currency: string;
  payment_method_id?: string;
  idempotency_key: string;
  billing_country?: string;
}

export interface Payment {
  id: string;
  order_id: string;
  user_id: string;
  amount: number | string;
  currency: string;
  provider: string;
  provider_transaction_id: string;
  status: 'PENDING' | 'SUCCEEDED' | 'FAILED' | 'REFUNDED';
  idempotency_key?: string;
  created_at: string;
  updated_at?: string;
}

export interface FraudCheckRequest {
  transaction_id: string;
  order_id: string;
  user_id: string;
  amount: number;
  currency: string;
  recent_transactions_count_1h: number;
  recent_failed_payments_24h: number;
  billing_country: string;
  ip_country: string;
}

export interface FraudCheckResponse {
  transaction_id: string;
  order_id: string;
  user_id: string;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  decision: 'APPROVE' | 'REVIEW' | 'REJECT';
  reasons: string[];
  rules_triggered: string[];
}

export interface ServiceHealth {
  name: string;
  port: number;
  path: string;
  status: 'HEALTHY' | 'UNHEALTHY' | 'CHECKING';
  latencyMs?: number;
  details?: string;
}
