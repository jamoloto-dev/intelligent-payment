'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, CartItem, Product } from '@/types';
import { DEMO_USERS } from './api';

interface AppContextType {
  user: User | null;
  token: string | null;
  role: 'USER' | 'ADMIN';
  cart: CartItem[];
  isCartOpen: boolean;
  setIsCartOpen: (open: boolean) => void;
  addToCart: (product: Product, quantity?: number) => void;
  removeFromCart: (productId: string) => void;
  updateQuantity: (productId: string, quantity: number) => void;
  clearCart: () => void;
  cartCount: number;
  cartTotal: number;
  switchUser: (role: 'USER' | 'ADMIN') => void;
  login: (user: User, token: string) => void;
  logout: () => void;
  toast: { message: string; type: 'success' | 'error' | 'info' } | null;
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(DEMO_USERS[0]);
  const [token, setToken] = useState<string | null>('demo_jwt_customer_token');
  const [cart, setCart] = useState<CartItem[]>([]);
  const [isCartOpen, setIsCartOpen] = useState<boolean>(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

  useEffect(() => {
    try {
      const savedCart = localStorage.getItem('ip_cart');
      if (savedCart) {
        setCart(JSON.parse(savedCart));
      }
      const savedUser = localStorage.getItem('ip_current_user');
      if (savedUser) {
        setUser(JSON.parse(savedUser));
      }
    } catch {
      // ignore
    }
  }, []);

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'success') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 4000);
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

  const switchUser = (role: 'USER' | 'ADMIN') => {
    const selected = DEMO_USERS.find((u) => u.role === role) || DEMO_USERS[0];
    setUser(selected);
    const mockToken = `demo_jwt_${role.toLowerCase()}_token`;
    setToken(mockToken);
    try {
      localStorage.setItem('ip_current_user', JSON.stringify(selected));
      localStorage.setItem('ip_token', mockToken);
    } catch {
      // ignore
    }
    showToast(`Switched account to: ${selected.first_name} (${selected.role})`, 'info');
  };

  const login = (newUser: User, newToken: string) => {
    setUser(newUser);
    setToken(newToken);
    try {
      localStorage.setItem('ip_current_user', JSON.stringify(newUser));
      localStorage.setItem('ip_token', newToken);
    } catch {}
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    try {
      localStorage.removeItem('ip_current_user');
      localStorage.removeItem('ip_token');
    } catch {}
    showToast('Logged out successfully', 'info');
  };

  const cartCount = cart.reduce((total, item) => total + item.quantity, 0);
  const cartTotal = cart.reduce((total, item) => total + item.product.price * item.quantity, 0);

  return (
    <AppContext.Provider
      value={{
        user,
        token,
        role: user?.role || 'USER',
        cart,
        isCartOpen,
        setIsCartOpen,
        addToCart,
        removeFromCart,
        updateQuantity,
        clearCart,
        cartCount,
        cartTotal,
        switchUser,
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
