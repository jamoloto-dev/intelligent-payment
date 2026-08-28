'use client';

import React, { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { Product } from '@/types';
import { useApp } from '@/lib/context';
import { 
  Package, 
  Plus, 
  PlusCircle, 
  MinusCircle, 
  Sparkles, 
  Lock, 
  X, 
  RefreshCw,
  Search
} from 'lucide-react';

export default function AdminProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [search, setSearch] = useState('');
  const { showToast } = useApp();

  // Add Product Form
  const [newProduct, setNewProduct] = useState({
    name: '',
    description: '',
    price: 99.99,
    currency: 'USD',
    stock_quantity: 50,
    category: 'Audio',
    image_url: '',
  });

  const loadProducts = async () => {
    setLoading(true);
    try {
      const data = await apiClient.getProducts();
      setProducts(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProducts();
  }, []);

  const handleAdjustStock = async (productId: string, delta: number) => {
    const target = products.find((p) => p.id === productId);
    if (!target) return;
    const newStock = Math.max(0, target.stock_quantity + delta);
    try {
      await apiClient.updateStock(productId, newStock);
      setProducts(products.map((p) => (p.id === productId ? { ...p, stock_quantity: newStock } : p)));
      showToast(`Stock updated for ${target.name}`, 'success');
    } catch (e: any) {
      showToast(e.message || 'Failed to update stock', 'error');
    }
  };

  const handleAddProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await apiClient.createProduct(newProduct);
      setProducts([created, ...products]);
      setIsAddModalOpen(false);
      setNewProduct({
        name: '',
        description: '',
        price: 99.99,
        currency: 'USD',
        stock_quantity: 50,
        category: 'Audio',
        image_url: '',
      });
      showToast(`Product "${created.name}" created successfully!`, 'success');
    } catch (e: any) {
      showToast(e.message || 'Failed to create product', 'error');
    }
  };

  const filtered = products.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.category?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-slate-900 border border-slate-800">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Package className="w-5 h-5 text-emerald-400" />
            Inventory & Catalog Management
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time stock controls secured with row-level pessimistic locking (`with_for_update()`).
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative w-48 sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search catalog..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white outline-none"
            />
          </div>

          <button
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md shadow-emerald-600/20"
          >
            <Plus className="w-4 h-4" />
            Add Product
          </button>
        </div>
      </div>

      {/* Products Inventory Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="px-6 py-4">Product & Category</th>
                <th className="px-6 py-4">Price</th>
                <th className="px-6 py-4">Inventory Level</th>
                <th className="px-6 py-4">Concurrency Lock</th>
                <th className="px-6 py-4 text-right">Quick Stock Adjustment</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-800/80">
              {filtered.map((prod) => (
                <tr key={prod.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-slate-800 overflow-hidden shrink-0">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={prod.image_url || ''} alt="" className="w-full h-full object-cover" />
                      </div>
                      <div>
                        <div className="font-bold text-white line-clamp-1">{prod.name}</div>
                        <span className="text-[10px] text-slate-400">{prod.category || 'General'}</span>
                      </div>
                    </div>
                  </td>

                  <td className="px-6 py-4 font-bold text-white">
                    ${prod.price.toFixed(2)} <span className="text-slate-400 text-[10px] font-normal">{prod.currency}</span>
                  </td>

                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-bold border ${
                        prod.stock_quantity === 0
                          ? 'bg-rose-950/80 border-rose-800 text-rose-300'
                          : prod.stock_quantity < 20
                          ? 'bg-amber-950/80 border-amber-800 text-amber-300'
                          : 'bg-emerald-950/80 border-emerald-800 text-emerald-300'
                      }`}
                    >
                      {prod.stock_quantity} units
                    </span>
                  </td>

                  <td className="px-6 py-4">
                    <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-mono">
                      <Lock className="w-3 h-3" /> Atomic Safe
                    </span>
                  </td>

                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => handleAdjustStock(prod.id, -5)}
                        className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                        title="Reduce stock by 5"
                      >
                        -5
                      </button>
                      <button
                        onClick={() => handleAdjustStock(prod.id, 5)}
                        className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                        title="Increase stock by 5"
                      >
                        +5
                      </button>
                      <button
                        onClick={() => handleAdjustStock(prod.id, 25)}
                        className="px-2.5 py-1 rounded-lg bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-800 text-emerald-300 text-xs font-semibold"
                        title="Restock +25"
                      >
                        +25
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Product Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="relative w-full max-w-lg rounded-3xl bg-slate-900 border border-slate-800 p-6 space-y-5 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Plus className="w-4 h-4 text-emerald-400" />
                Add New Product SKU
              </h3>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddProduct} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-400 font-semibold mb-1">Product Title</label>
                <input
                  type="text"
                  required
                  value={newProduct.name}
                  onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
                  placeholder="e.g. Mechanical Studio Headphones"
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 font-semibold mb-1">Description</label>
                <textarea
                  required
                  rows={3}
                  value={newProduct.description}
                  onChange={(e) => setNewProduct({ ...newProduct, description: e.target.value })}
                  placeholder="Technical specs and product features..."
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white outline-none focus:border-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Unit Price ($ USD)</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={newProduct.price}
                    onChange={(e) => setNewProduct({ ...newProduct, price: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white outline-none focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Initial Stock Qty</label>
                  <input
                    type="number"
                    required
                    value={newProduct.stock_quantity}
                    onChange={(e) => setNewProduct({ ...newProduct, stock_quantity: parseInt(e.target.value) || 0 })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Category</label>
                  <select
                    value={newProduct.category}
                    onChange={(e) => setNewProduct({ ...newProduct, category: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white outline-none"
                  >
                    <option value="Audio">Audio</option>
                    <option value="Displays">Displays</option>
                    <option value="Peripherals">Peripherals</option>
                    <option value="Wearables">Wearables</option>
                    <option value="Video">Video</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Image URL (Unsplash/Direct)</label>
                  <input
                    type="url"
                    value={newProduct.image_url}
                    onChange={(e) => setNewProduct({ ...newProduct, image_url: e.target.value })}
                    placeholder="https://images.unsplash.com/..."
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white outline-none"
                  />
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  className="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-lg shadow-emerald-600/20"
                >
                  Create SKU in Catalog
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
