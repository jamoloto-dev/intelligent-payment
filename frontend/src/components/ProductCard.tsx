'use client';

import React from 'react';
import Image from 'next/image';
import { Product } from '@/types';
import { useApp } from '@/lib/context';
import { ShoppingCart, Check, Package, Sparkles } from 'lucide-react';

export const ProductCard: React.FC<{ product: Product }> = ({ product }) => {
  const { addToCart, cart } = useApp();

  const inCart = cart.some((item) => item.product.id === product.id);
  const isOutOfStock = product.stock_quantity <= 0;

  return (
    <div className="group rounded-2xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/90 overflow-hidden shadow-sm hover:shadow-xl hover:border-emerald-500/30 dark:hover:border-emerald-500/30 transition-all duration-300 flex flex-col justify-between">
      {/* Product Image & Badges */}
      <div className="relative aspect-video w-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
        {product.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={product.image_url}
            alt={product.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-400">
            <Package className="w-12 h-12 stroke-1" />
          </div>
        )}

        {/* Category Badge */}
        {product.category && (
          <span className="absolute top-3 left-3 px-2.5 py-1 rounded-full bg-white/90 dark:bg-slate-900/90 backdrop-blur-md text-[11px] font-semibold text-slate-700 dark:text-slate-300 shadow-sm">
            {product.category}
          </span>
        )}

        {/* Stock Badge */}
        <span
          className={`absolute top-3 right-3 px-2.5 py-1 rounded-full text-[11px] font-bold backdrop-blur-md shadow-sm ${
            isOutOfStock
              ? 'bg-rose-500/90 text-white'
              : product.stock_quantity < 20
              ? 'bg-amber-500/90 text-white'
              : 'bg-emerald-500/90 text-white'
          }`}
        >
          {isOutOfStock ? 'Sold Out' : `${product.stock_quantity} in Stock`}
        </span>
      </div>

      {/* Product Details */}
      <div className="p-5 flex-1 flex flex-col justify-between">
        <div>
          <h3 className="font-bold text-slate-900 dark:text-white text-base tracking-tight group-hover:text-emerald-500 transition-colors line-clamp-1">
            {product.name}
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 line-clamp-2 leading-relaxed">
            {product.description}
          </p>
        </div>

        {/* Pricing & Add to Cart */}
        <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-medium">Price</span>
            <div className="text-lg font-extrabold text-slate-900 dark:text-white tracking-tight">
              ${product.price.toFixed(2)} <span className="text-xs font-normal text-slate-400">{product.currency}</span>
            </div>
          </div>

          <button
            onClick={() => addToCart(product, 1)}
            disabled={isOutOfStock}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold shadow-sm transition-all ${
              isOutOfStock
                ? 'bg-slate-200 text-slate-400 dark:bg-slate-800 dark:text-slate-600 cursor-not-allowed'
                : inCart
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-300 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-700 hover:bg-emerald-100'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20 hover:shadow-emerald-600/30'
            }`}
          >
            {inCart ? (
              <>
                <Check className="w-3.5 h-3.5" />
                Added
              </>
            ) : (
              <>
                <ShoppingCart className="w-3.5 h-3.5" />
                Add to Cart
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
