import React, {useState} from 'react';
import {X, ExternalLink, Edit3, Trash2, Loader2, RefreshCw} from 'lucide-react';
import {PriceChart} from './PriceChart';
import {PriceHistoryPoint, Product} from '../types';

interface DetailsPanelProps {
  product: Product | null;
  history: PriceHistoryPoint[];
  historyLoading: boolean;
  deleting: boolean;
  savingEdit: boolean;
  checkingProduct: boolean;
  onClose: () => void;
  onDelete: (product: Product) => void;
  onEditAlert: (newPrice: number) => Promise<void>;
  onCheckNow: () => Promise<void>;
}

export function DetailsPanel({
  product,
  history,
  historyLoading,
  deleting,
  savingEdit,
  checkingProduct,
  onClose,
  onDelete,
  onEditAlert,
  onCheckNow,
}: DetailsPanelProps) {
  const [editMode, setEditMode] = useState(false);
  const [editPriceInput, setEditPriceInput] = useState('');

  if (!product) return null;

  const enterEdit = () => {
    setEditPriceInput(product.targetPrice.toFixed(2));
    setEditMode(true);
  };

  const cancelEdit = () => {
    setEditMode(false);
    setEditPriceInput('');
  };

  const saveEdit = async () => {
    const parsed = Number.parseFloat(editPriceInput);
    if (!Number.isFinite(parsed) || parsed <= 0) return;
    await onEditAlert(parsed);
    setEditMode(false);
    setEditPriceInput('');
  };

  return (
    <aside className="w-[400px] fixed right-0 top-0 h-screen bg-surface-container-low border-l border-outline-variant/10 p-8 overflow-y-auto hide-scrollbar z-40 font-manrope">
      <div className="flex items-center justify-between mb-8">
        <h3 className="text-lg font-extrabold uppercase tracking-tight text-on-surface">
          Product Details
        </h3>
        <button
          onClick={onClose}
          className="p-2 rounded-full hover:bg-surface-container-high transition-colors"
        >
          <X size={20} />
        </button>
      </div>

      <div className="mb-10 text-center">
        <div className="w-full aspect-square bg-surface-container-lowest rounded-3xl p-6 shadow-sm mb-6 flex items-center justify-center">
          <img
            src={product.imageUrl}
            alt={product.name}
            className="max-h-full max-w-full object-contain"
            referrerPolicy="no-referrer"
          />
        </div>

        <div className="inline-flex items-center gap-2 bg-primary/10 text-primary px-3 py-1 rounded-full text-xs font-bold mb-3">
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          LIVE MONITORING
        </div>

        <h2 className="text-2xl font-extrabold text-on-surface mb-2 leading-tight">
          {product.name}
        </h2>
        <p className="text-sm text-on-surface-variant font-medium">
          Tracking on {product.store} since {product.trackingSince}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-10">
        <div className="bg-surface-container-lowest p-4 rounded-2xl shadow-sm">
          <span className="text-[10px] font-bold text-on-surface-variant uppercase block mb-1">
            Current Price
          </span>
          <div className="text-2xl font-extrabold text-on-surface">
            {product.currentPrice === null
              ? 'N/A'
              : `${product.currentPrice.toFixed(2)} ${product.currency}`}
          </div>
        </div>
        <div className="bg-surface-container-lowest p-4 rounded-2xl shadow-sm">
          <span className="text-[10px] font-bold text-on-surface-variant uppercase block mb-1">
            Target Price
          </span>
          {editMode ? (
            <div className="flex items-center gap-1 mt-1">
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={editPriceInput}
                onChange={(e) => setEditPriceInput(e.target.value)}
                className="w-full text-lg font-extrabold text-primary border border-primary/40 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-primary/30"
                autoFocus
              />
              <span className="text-sm text-on-surface-variant shrink-0">{product.currency}</span>
            </div>
          ) : (
            <div className="text-2xl font-extrabold text-primary">
              {product.targetPrice.toFixed(2)} {product.currency}
            </div>
          )}
        </div>
      </div>

      <div className="bg-surface-container-lowest p-6 rounded-3xl shadow-sm mb-8">
        <div className="flex items-center justify-between mb-6">
          <span className="text-xs font-bold text-on-surface uppercase tracking-wider">
            Price History
          </span>
          {historyLoading && <Loader2 size={14} className="animate-spin text-on-surface-variant" />}
        </div>

        {history.length > 0 ? (
          <PriceChart targetPrice={product.targetPrice} history={history} />
        ) : (
          <div className="h-48 flex items-center justify-center text-sm text-on-surface-variant">
            No history data yet.
          </div>
        )}
      </div>

      <div className="space-y-3">
        <a
          href={product.url}
          target="_blank"
          rel="noreferrer"
          className="w-full bg-surface-container-highest text-on-surface font-bold py-4 rounded-2xl flex items-center justify-center gap-3 hover:bg-surface-variant transition-colors"
        >
          <ExternalLink size={18} />
          View on Store
        </a>
        <button
          onClick={onCheckNow}
          disabled={checkingProduct}
          className="w-full bg-primary/10 text-primary font-bold py-4 rounded-2xl flex items-center justify-center gap-2 hover:bg-primary/20 transition-colors disabled:opacity-60"
        >
          {checkingProduct ? <Loader2 size={18} className="animate-spin" /> : <RefreshCw size={18} />}
          {checkingProduct ? 'Checking...' : 'Check price now'}
        </button>
        <div className="flex gap-3">
          {editMode ? (
            <>
              <button
                onClick={cancelEdit}
                disabled={savingEdit}
                className="flex-1 bg-surface-container-lowest border border-outline-variant/30 text-on-surface-variant font-bold py-4 rounded-2xl flex items-center justify-center gap-2 hover:bg-surface-container transition-colors disabled:opacity-60"
              >
                Cancel
              </button>
              <button
                onClick={saveEdit}
                disabled={savingEdit || !Number.isFinite(Number.parseFloat(editPriceInput)) || Number.parseFloat(editPriceInput) <= 0}
                className="flex-1 bg-primary text-on-primary font-bold py-4 rounded-2xl flex items-center justify-center gap-2 hover:bg-primary/90 transition-colors disabled:opacity-60"
              >
                {savingEdit ? <Loader2 size={18} className="animate-spin" /> : <Edit3 size={18} />}
                Save
              </button>
            </>
          ) : (
          <button
            onClick={enterEdit}
            className="flex-1 bg-surface-container-lowest border border-outline-variant/30 text-on-surface font-bold py-4 rounded-2xl flex items-center justify-center gap-2 hover:bg-surface-container transition-colors"
          >
            <Edit3 size={18} className="text-on-surface-variant" />
            Edit Alert
          </button>
          )}
          <button
            onClick={() => onDelete(product)}
            disabled={deleting}
            className="flex-1 bg-surface-container-lowest border border-error/20 text-error font-bold py-4 rounded-2xl flex items-center justify-center gap-2 hover:bg-error/5 transition-colors disabled:opacity-70"
          >
            {deleting ? <Loader2 size={18} className="animate-spin" /> : <Trash2 size={18} />}
            Remove
          </button>
        </div>
      </div>
    </aside>
  );
}
