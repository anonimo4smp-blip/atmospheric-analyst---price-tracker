import React from 'react';
import {AlertCircle, RefreshCw} from 'lucide-react';
import {cn} from '../lib/utils';
import {Product} from '../types';

interface ProductCardProps {
  key?: React.Key;
  product: Product;
  isSelected?: boolean;
  onClick?: () => void;
}

export function ProductCard({product, isSelected, onClick}: ProductCardProps) {
  const isError = product.status === 'ERROR';
  const isPending = product.status === 'PENDING';
  const isAlert = product.status === 'DROP ALERT';

  return (
    <div
      onClick={onClick}
      className={cn(
        'bg-surface-container-lowest p-5 rounded-2xl shadow-sm border-b-4 transition-all group cursor-pointer',
        isSelected
          ? 'border-primary ring-2 ring-primary/10 shadow-md'
          : 'border-transparent hover:border-primary/50',
        isError && 'hover:border-error',
      )}
    >
      <div className="flex gap-4">
        <div
          className={cn(
            'w-24 h-24 rounded-xl bg-surface-container-low flex items-center justify-center p-2 relative overflow-hidden shrink-0',
            isError && 'opacity-50',
          )}
        >
          {isPending ? (
            <div className="w-12 h-12 rounded-full border-2 border-dashed border-outline-variant flex items-center justify-center text-outline-variant">
              <RefreshCw size={24} className="animate-spin-slow" />
            </div>
          ) : (
            <img
              src={product.imageUrl}
              alt={product.name}
              className={cn('object-contain w-full h-full', isError && 'grayscale')}
              referrerPolicy="no-referrer"
            />
          )}

          {isAlert && (
            <div className="absolute inset-0 bg-tertiary-container/10 flex items-center justify-center">
              <div className="bg-tertiary-container text-on-tertiary-container text-[10px] font-black px-2 py-1 rounded-full shadow-sm animate-pulse">
                ALERT
              </div>
            </div>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-start mb-1">
            <span className="text-[10px] font-bold text-on-surface-variant bg-surface-container-high px-2 py-0.5 rounded uppercase tracking-tighter">
              {product.store}
            </span>
            <span
              className={cn(
                'rounded-full px-2 py-0.5 text-[10px] font-bold',
                product.status === 'ACTIVE' && 'bg-primary text-white',
                product.status === 'DROP ALERT' &&
                  'bg-tertiary-container text-on-tertiary-container',
                product.status === 'ERROR' && 'bg-error text-white',
                product.status === 'PENDING' &&
                  'bg-surface-container-highest text-on-surface-variant',
              )}
            >
              {product.status}
            </span>
          </div>

          <h4 className="font-manrope font-bold text-on-surface leading-tight mb-2 group-hover:text-primary transition-colors truncate">
            {product.name}
          </h4>

          {isError ? (
            <div className="flex items-center gap-2 text-error font-bold">
              <AlertCircle size={14} />
              <span className="text-xs uppercase tracking-wider">
                {product.errorMsg || 'Error'}
              </span>
            </div>
          ) : isPending ? (
            <div className="text-xs text-on-surface-variant italic truncate">
              {product.pendingMsg}
            </div>
          ) : (
            <div className="flex items-baseline gap-2">
              <span className={cn('text-xl font-extrabold', isAlert && 'text-tertiary-container')}>
                {product.currentPrice === null
                  ? 'N/A'
                  : `${product.currentPrice.toFixed(2)} ${product.currency}`}
              </span>
              {typeof product.originalPrice === 'number' && (
                <span className="text-xs text-on-surface-variant line-through">
                  {product.originalPrice.toFixed(2)} {product.currency}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
