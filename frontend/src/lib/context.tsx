'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, UserRole, CartItem, Product } from '@/types';
import { apiClient } from './api';

interface AppContextType {
  user: User | null;
  token: string | null;
  role: UserRole;
  isAuthenticated: boolean;
  isLoadingAuth: boolean;
  cart: CartItem[];
  isCartOpen: boolean;
  setIsCartOpen: (open: boolean) => void;
  addToCart: (product: Product, quantity?: number) => void;
  removeFromCart: (productId: string) => void;
  updateQuantity: (productId: string, quantity: number) => void;
  clearCart: () => void;
  cartCount: number;
  cartTotal: number;
  login: (user: User, token: string) => void;
  logout: () => void;
  toast: { message: string; type: 'success' | 'error' | 'info' } | null;
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoadingAuth, setIsLoadingAuth] = useState<boolean>(true);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [isCartOpen, setIsCartOpen] = useState<boolean>(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showToast = useCallback((message: string, type: 'success' | 'error' | 'info' = 'success') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 4000);
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    apiClient.setToken(null);
    try {
      localStorage.removeItem('ip_current_user');
      document.cookie = 'ip_token=; path=/; max-age=0; SameSite=Lax';
    } catch {}
    showToast('Logged out successfully', 'info');
  }, [showToast]);

  // Initial session hydration
  useEffect(() => {
    const initAuth = async () => {
      try {
        const savedCart = localStorage.getItem('ip_cart');
        if (savedCart) {
          setCart(JSON.parse(savedCart));
        }

        const savedToken = apiClient.getToken();
        if (savedToken) {
          setToken(savedToken);
          // Validate token with backend authority
          try {
            const me = await apiClient.getMe();
            setUser(me);
            localStorage.setItem('ip_current_user', JSON.stringify(me));
            document.cookie = `ip_token=${encodeURIComponent(savedToken)}; path=/; max-age=86400; SameSite=Lax`;
          } catch {
            // Token expired or invalid on backend
            logout();
          }
        }
      } catch {
        // storage disabled or error
      } finally {
        setIsLoadingAuth(false);
      }
    };

    initAuth();
  }, [logout]);

  const login = (newUser: User, newToken: string) => {
    setUser(newUser);
    setToken(newToken);
    apiClient.setToken(newToken);
    try {
      localStorage.setItem('ip_current_user', JSON.stringify(newUser));
      document.cookie = `ip_token=${encodeURIComponent(newToken)}; path=/; max-age=86400; SameSite=Lax`;
    } catch {}
  };

  const saveCartToStorage = (updatedCart: CartItem[]) => {
    setCart(updatedCart);
    try {
      localStorage.setItem('ip_cart', JSON.stringify(updatedCart));
    } catch (e) {
      console.error(e);
    }
  };

  const addToCart = (product: Product, quantity: number = 1) => {
    const existingIndex = cart.findIndex((item) => item.product.id === product.id);
    let updated: CartItem[];
    if (existingIndex > -1) {
      updated = [...cart];
      updated[existingIndex].quantity += quantity;
    } else {
      updated = [...cart, { product, quantity }];
    }
    saveCartToStorage(updated);
    showToast(`Added "${product.name}" to cart!`, 'success');
  };

  const removeFromCart = (productId: string) => {
    const updated = cart.filter((item) => item.product.id !== productId);
    saveCartToStorage(updated);
  };

  const updateQuantity = (productId: string, quantity: number) => {
    if (quantity <= 0) {
      removeFromCart(productId);
      return;
    }
    const updated = cart.map((item) =>
      item.product.id === productId ? { ...item, quantity } : item
    );
    saveCartToStorage(updated);
  };

  const clearCart = () => {
    saveCartToStorage([]);
  };

  const cartCount = cart.reduce((total, item) => total + item.quantity, 0);
  const cartTotal = cart.reduce((total, item) => total + item.product.price * item.quantity, 0);

  return (
    <AppContext.Provider
      value={{
        user,
        token,
        role: user?.role || 'CUSTOMER',
        isAuthenticated: !!token && !!user,
        isLoadingAuth,
        cart,
        isCartOpen,
        setIsCartOpen,
        addToCart,
        removeFromCart,
        updateQuantity,
        clearCart,
        cartCount,
        cartTotal,
        login,
        logout,
        toast,
        showToast,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
