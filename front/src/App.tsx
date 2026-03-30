import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {
  BarChart3,
  Activity,
  AlertTriangle,
  PlusCircle,
  Filter,
  LayoutGrid,
  Loader2,
  RefreshCw,
  LineChart,
  LogIn,
  UserPlus,
  ShieldCheck,
} from 'lucide-react';
import {Sidebar} from './components/Sidebar';
import {KPICard} from './components/KPICard';
import {ProductCard} from './components/ProductCard';
import {DetailsPanel} from './components/DetailsPanel';
import {DEFAULT_PRODUCT_IMAGE} from './constants';
import {
  ApiAuthMessageResponse,
  ApiAuthUser,
  ApiCheckNowSummary,
  ApiLoginResponse,
  ApiPriceHistoryPoint,
  ApiProduct,
  PriceHistoryPoint,
  Product,
  ProductStatus,
} from './types';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001').replace(
  /\/+$/,
  '',
);

type AuthStatus = 'checking' | 'authenticated' | 'unauthenticated';
type AuthView = 'login' | 'register' | 'verify';

class ApiHttpError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiHttpError';
  }
}

function isUnauthorizedError(error: unknown): boolean {
  return error instanceof ApiHttpError && error.status === 401;
}

function readCookie(cookieName: string): string | null {
  const cookies = document.cookie ? document.cookie.split(';') : [];
  for (const cookie of cookies) {
    const [name, ...valueParts] = cookie.trim().split('=');
    if (name === cookieName) {
      return decodeURIComponent(valueParts.join('='));
    }
  }
  return null;
}

function formatDateLabel(dateIso: string): string {
  const date = new Date(dateIso);
  if (Number.isNaN(date.getTime())) {
    return '-';
  }
  return new Intl.DateTimeFormat('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date);
}

function formatChartDate(dateIso: string): string {
  const date = new Date(dateIso);
  if (Number.isNaN(date.getTime())) {
    return '-';
  }
  return new Intl.DateTimeFormat('es-ES', {
    day: '2-digit',
    month: 'short',
  }).format(date);
}

function toUiStore(storeCode: string): string {
  const normalized = storeCode.trim().toLowerCase();
  if (normalized === 'amazon_es') return 'Amazon ES';
  if (normalized === 'pccomponentes') return 'PCComponentes';
  return storeCode;
}

function toUiStatus(product: ApiProduct): ProductStatus {
  if (product.last_status === 'never_checked') return 'PENDING';
  if (product.last_status === 'error' || product.last_status === 'unavailable') return 'ERROR';
  if (typeof product.last_price === 'number' && product.last_price <= product.desired_price) {
    return 'DROP ALERT';
  }
  return 'ACTIVE';
}

function mapProduct(product: ApiProduct): Product {
  const status = toUiStatus(product);
  return {
    id: product.id,
    url: product.url,
    name: product.title || product.url,
    store: toUiStore(product.store),
    status,
    currentPrice: product.last_price,
    targetPrice: product.desired_price,
    imageUrl: product.image_url || DEFAULT_PRODUCT_IMAGE,
    trackingSince: formatDateLabel(product.created_at),
    currency: product.currency || 'EUR',
    checkedAt: product.last_checked_at,
    errorMsg: status === 'ERROR' ? product.last_error || 'Price check failed' : undefined,
    pendingMsg: status === 'PENDING' ? 'Initial verification in progress...' : undefined,
  };
}

function mapHistory(history: ApiPriceHistoryPoint[]): PriceHistoryPoint[] {
  return history
    .filter((point) => typeof point.price === 'number')
    .map((point) => ({
      date: formatChartDate(point.checked_at),
      price: point.price as number,
    }));
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return 'Unexpected error while calling backend.';
}

async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers || {});

  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const csrfToken = readCookie('csrf_token');
  if (csrfToken && !headers.has('x-csrf-token')) {
    headers.set('x-csrf-token', csrfToken);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const rawBody = await response.text();
  let parsedBody: unknown = null;
  if (rawBody) {
    try {
      parsedBody = JSON.parse(rawBody);
    } catch {
      parsedBody = rawBody;
    }
  }

  if (!response.ok) {
    if (
      parsedBody &&
      typeof parsedBody === 'object' &&
      'detail' in parsedBody &&
      typeof (parsedBody as {detail: unknown}).detail === 'string'
    ) {
      throw new ApiHttpError(response.status, (parsedBody as {detail: string}).detail);
    }
    throw new ApiHttpError(response.status, `Request failed with status ${response.status}`);
  }

  return parsedBody as T;
}

export default function App() {
  const [authStatus, setAuthStatus] = useState<AuthStatus>('checking');
  const [authUser, setAuthUser] = useState<ApiAuthUser | null>(null);
  const [authView, setAuthView] = useState<AuthView>('login');
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [authNotice, setAuthNotice] = useState<string | null>(null);

  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [registerConfirmPassword, setRegisterConfirmPassword] = useState('');
  const [registerLoading, setRegisterLoading] = useState(false);
  const [pendingVerificationEmail, setPendingVerificationEmail] = useState('');
  const [verifyToken, setVerifyToken] = useState('');
  const [verifyLoading, setVerifyLoading] = useState(false);

  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null);
  const [historyByProduct, setHistoryByProduct] = useState<Record<number, PriceHistoryPoint[]>>({});

  const [urlInput, setUrlInput] = useState('');
  const [targetPriceInput, setTargetPriceInput] = useState('');

  const [productsLoading, setProductsLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [savingProduct, setSavingProduct] = useState(false);
  const [runningCheck, setRunningCheck] = useState(false);
  const [deletingProduct, setDeletingProduct] = useState(false);
  const [savingEditAlert, setSavingEditAlert] = useState(false);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  const resetDashboardData = useCallback(() => {
    setProducts([]);
    setSelectedProductId(null);
    setHistoryByProduct({});
    setUrlInput('');
    setTargetPriceInput('');
    setErrorMessage(null);
    setInfoMessage(null);
  }, []);

  const switchAuthView = (nextView: AuthView) => {
    setAuthView(nextView);
    setLoginError(null);
    setAuthNotice(null);
  };

  const forceLoginScreen = useCallback(
    (message?: string) => {
      setAuthStatus('unauthenticated');
      setAuthUser(null);
      setAuthView('login');
      setLoginPassword('');
      setLoginError(message || null);
      setAuthNotice(null);
      resetDashboardData();
    },
    [resetDashboardData],
  );

  const handleProtectedError = useCallback(
    (error: unknown, fallbackMessage: string) => {
      if (isUnauthorizedError(error)) {
        forceLoginScreen('La sesion expiro. Inicia sesion de nuevo.');
        return;
      }
      setErrorMessage(getErrorMessage(error) || fallbackMessage);
    },
    [forceLoginScreen],
  );

  const selectedProduct = useMemo(
    () => products.find((product) => product.id === selectedProductId) || null,
    [products, selectedProductId],
  );

  const selectedHistory = selectedProduct ? historyByProduct[selectedProduct.id] || [] : [];

  const totalTracked = products.length;
  const activeTracked = products.filter(
    (product) => product.status === 'ACTIVE' || product.status === 'DROP ALERT',
  ).length;
  const incidents = products.filter((product) => product.status === 'ERROR').length;
  const drops = products.filter((product) => product.status === 'DROP ALERT').length;

  const refreshProducts = useCallback(async (preferredSelectedId?: number) => {
    const apiProducts = await apiRequest<ApiProduct[]>('/api/products');
    const nextProducts = apiProducts.map(mapProduct);
    setProducts(nextProducts);
    setSelectedProductId((currentSelectedId) => {
      const requestedId = preferredSelectedId ?? currentSelectedId;
      if (typeof requestedId === 'number' && nextProducts.some((product) => product.id === requestedId)) {
        return requestedId;
      }
      return nextProducts.length > 0 ? nextProducts[0].id : null;
    });
  }, []);

  useEffect(() => {
    let cancelled = false;
    const checkAuth = async () => {
      setAuthStatus('checking');
      setLoginError(null);
      try {
        const currentUser = await apiRequest<ApiAuthUser>('/api/auth/me');
        if (cancelled) return;
        setAuthUser(currentUser);
        setAuthStatus('authenticated');
      } catch (error) {
        if (cancelled) return;
        if (isUnauthorizedError(error)) {
          forceLoginScreen();
          return;
        }
        forceLoginScreen(getErrorMessage(error));
      }
    };

    void checkAuth();
    return () => {
      cancelled = true;
    };
  }, [forceLoginScreen]);

  useEffect(() => {
    if (authStatus !== 'authenticated') {
      setProductsLoading(false);
      return;
    }

    let cancelled = false;
    const bootstrap = async () => {
      setProductsLoading(true);
      setErrorMessage(null);
      try {
        await refreshProducts();
      } catch (error) {
        if (!cancelled) {
          handleProtectedError(error, 'No se pudieron cargar los productos.');
        }
      } finally {
        if (!cancelled) {
          setProductsLoading(false);
        }
      }
    };
    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [authStatus, handleProtectedError, refreshProducts]);

  useEffect(() => {
    if (authStatus !== 'authenticated' || selectedProductId === null) {
      return;
    }
    let cancelled = false;
    const loadHistory = async () => {
      setHistoryLoading(true);
      try {
        const apiHistory = await apiRequest<ApiPriceHistoryPoint[]>(
          `/api/products/${selectedProductId}/history`,
        );
        if (!cancelled) {
          setHistoryByProduct((current) => ({
            ...current,
            [selectedProductId]: mapHistory(apiHistory),
          }));
        }
      } catch (error) {
        if (!cancelled) {
          if (isUnauthorizedError(error)) {
            forceLoginScreen('La sesion expiro. Inicia sesion de nuevo.');
            return;
          }
          setErrorMessage(getErrorMessage(error));
          setHistoryByProduct((current) => ({
            ...current,
            [selectedProductId]: [],
          }));
        }
      } finally {
        if (!cancelled) {
          setHistoryLoading(false);
        }
      }
    };

    void loadHistory();
    return () => {
      cancelled = true;
    };
  }, [authStatus, forceLoginScreen, selectedProductId]);

  const handleLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!loginEmail.trim() || !loginPassword) {
      setLoginError('Introduce email y contrasena.');
      return;
    }

    setLoginLoading(true);
    setLoginError(null);
    setAuthNotice(null);
    try {
      const loginResponse = await apiRequest<ApiLoginResponse>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          email: loginEmail.trim(),
          password: loginPassword,
        }),
      });
      setAuthUser(loginResponse.user);
      setAuthStatus('authenticated');
      setLoginPassword('');
      setInfoMessage(`Sesion iniciada como ${loginResponse.user.email}.`);
    } catch (error) {
      setLoginError(getErrorMessage(error));
    } finally {
      setLoginLoading(false);
    }
  };

  const handleRegister = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!registerEmail.trim() || !registerPassword || !registerConfirmPassword) {
      setLoginError('Completa todos los campos para crear la cuenta.');
      return;
    }
    if (registerPassword.length < 12) {
      setLoginError('La contrasena debe tener al menos 12 caracteres.');
      return;
    }
    if (registerPassword !== registerConfirmPassword) {
      setLoginError('Las contrasenas no coinciden.');
      return;
    }

    setRegisterLoading(true);
    setLoginError(null);
    setAuthNotice(null);
    try {
      const response = await apiRequest<ApiAuthMessageResponse>('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          email: registerEmail.trim(),
          password: registerPassword,
        }),
      });
      setPendingVerificationEmail(registerEmail.trim());
      setLoginEmail(registerEmail.trim());
      setRegisterPassword('');
      setRegisterConfirmPassword('');
      setVerifyToken(response.debug_token || '');
      setAuthView('verify');
      setAuthNotice(response.message);
    } catch (error) {
      setLoginError(getErrorMessage(error));
    } finally {
      setRegisterLoading(false);
    }
  };

  const handleVerifyEmail = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!verifyToken.trim()) {
      setLoginError('Introduce el token de verificacion.');
      return;
    }

    setVerifyLoading(true);
    setLoginError(null);
    setAuthNotice(null);
    try {
      const response = await apiRequest<ApiAuthMessageResponse>('/api/auth/verify-email', {
        method: 'POST',
        body: JSON.stringify({token: verifyToken.trim()}),
      });
      setAuthView('login');
      setVerifyToken('');
      setAuthNotice(`${response.message} Ya puedes iniciar sesion.`);
    } catch (error) {
      setLoginError(getErrorMessage(error));
    } finally {
      setVerifyLoading(false);
    }
  };

  const handleResendVerification = async () => {
    if (!pendingVerificationEmail.trim()) {
      setLoginError('Primero registra una cuenta para reenviar verificacion.');
      return;
    }

    setVerifyLoading(true);
    setLoginError(null);
    setAuthNotice(null);
    try {
      const response = await apiRequest<ApiAuthMessageResponse>('/api/auth/resend-verification', {
        method: 'POST',
        body: JSON.stringify({email: pendingVerificationEmail}),
      });
      if (response.debug_token) {
        setVerifyToken(response.debug_token);
      }
      setAuthNotice(response.message);
    } catch (error) {
      setLoginError(getErrorMessage(error));
    } finally {
      setVerifyLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await apiRequest<{message: string}>('/api/auth/logout', {method: 'POST'});
    } catch {
      // Si la sesion ya no existe, igual forzamos salida local.
    } finally {
      forceLoginScreen();
    }
  };

  const handleSaveProduct = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedUrl = urlInput.trim();
    const parsedPrice = Number.parseFloat(targetPriceInput);

    if (!trimmedUrl) {
      setErrorMessage('Product URL is required.');
      return;
    }
    if (!Number.isFinite(parsedPrice) || parsedPrice <= 0) {
      setErrorMessage('Target price must be greater than zero.');
      return;
    }

    setSavingProduct(true);
    setErrorMessage(null);
    setInfoMessage(null);
    try {
      const createdProduct = await apiRequest<ApiProduct>('/api/products', {
        method: 'POST',
        body: JSON.stringify({
          url: trimmedUrl,
          desired_price: Number(parsedPrice.toFixed(2)),
        }),
      });

      await refreshProducts(createdProduct.id);
      setHistoryByProduct((current) => {
        const next = {...current};
        delete next[createdProduct.id];
        return next;
      });
      setUrlInput('');
      setTargetPriceInput('');
      setInfoMessage('Product saved successfully.');
    } catch (error) {
      handleProtectedError(error, 'No se pudo guardar el producto.');
    } finally {
      setSavingProduct(false);
    }
  };

  const handleCheckNow = async () => {
    setRunningCheck(true);
    setErrorMessage(null);
    setInfoMessage(null);
    try {
      const summary = await apiRequest<ApiCheckNowSummary>('/api/jobs/check-now', {
        method: 'POST',
      });
      await refreshProducts(selectedProductId || undefined);
      if (selectedProductId !== null) {
        setHistoryByProduct((current) => {
          const next = {...current};
          delete next[selectedProductId];
          return next;
        });
      }
      setInfoMessage(
        `Check finished. OK: ${summary.checked_ok}, Failed: ${summary.checked_failed}, Alerts: ${summary.alerts_created}`,
      );
    } catch (error) {
      handleProtectedError(error, 'No se pudo ejecutar la comprobacion manual.');
    } finally {
      setRunningCheck(false);
    }
  };

  const handleEditAlert = async (newPrice: number) => {
    if (!selectedProduct) return;
    setSavingEditAlert(true);
    setErrorMessage(null);
    try {
      await apiRequest<ApiProduct>('/api/products', {
        method: 'POST',
        body: JSON.stringify({
          url: selectedProduct.url,
          desired_price: Number(newPrice.toFixed(2)),
        }),
      });
      await refreshProducts(selectedProduct.id);
      setInfoMessage('Target price updated.');
    } catch (error) {
      handleProtectedError(error, 'No se pudo actualizar el precio objetivo.');
    } finally {
      setSavingEditAlert(false);
    }
  };

  const handleDeleteProduct = async (product: Product) => {
    if (!window.confirm(`Remove "${product.name}" from tracking?`)) {
      return;
    }

    setDeletingProduct(true);
    setErrorMessage(null);
    setInfoMessage(null);
    try {
      await apiRequest<void>(`/api/products/${product.id}`, {method: 'DELETE'});
      setHistoryByProduct((current) => {
        const next = {...current};
        delete next[product.id];
        return next;
      });
      await refreshProducts();
      setInfoMessage('Product removed successfully.');
    } catch (error) {
      handleProtectedError(error, 'No se pudo eliminar el producto.');
    } finally {
      setDeletingProduct(false);
    }
  };

  if (authStatus === 'checking') {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center p-6">
        <div className="bg-surface-container-lowest rounded-3xl px-8 py-10 shadow-sm border border-outline-variant/10 flex items-center gap-4">
          <Loader2 size={22} className="animate-spin text-primary" />
          <div>
            <p className="font-manrope text-lg font-extrabold text-on-surface">Checking session</p>
            <p className="text-sm font-semibold text-on-surface-variant">Connecting with backend...</p>
          </div>
        </div>
      </div>
    );
  }

  if (authStatus === 'unauthenticated') {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center p-6">
        <div className="w-full max-w-md bg-surface-container-lowest rounded-3xl p-8 shadow-sm border border-outline-variant/10">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-11 h-11 rounded-xl primary-gradient flex items-center justify-center text-white shadow-lg">
              <LineChart size={24} />
            </div>
            <div>
              <h1 className="text-lg font-extrabold text-primary tracking-tight">Atmospheric Analyst</h1>
              <p className="text-[11px] text-on-surface-variant font-bold uppercase tracking-widest">
                Price Tracker
              </p>
            </div>
          </div>

          <h2 className="font-manrope text-2xl font-extrabold text-on-surface mb-2">
            {authView === 'register'
              ? 'Crear cuenta'
              : authView === 'verify'
                ? 'Verificar cuenta'
                : 'Iniciar sesion'}
          </h2>
          <p className="text-sm text-on-surface-variant font-medium mb-6">
            Seguridad activa: necesitas cuenta verificada para entrar.
          </p>

          {authView !== 'verify' && (
            <div className="grid grid-cols-2 gap-2 mb-5">
              <button
                type="button"
                onClick={() => switchAuthView('login')}
                className={`h-10 rounded-xl text-sm font-bold transition-colors ${
                  authView === 'login'
                    ? 'bg-primary text-white'
                    : 'bg-surface-container-high text-on-surface-variant'
                }`}
              >
                Iniciar sesion
              </button>
              <button
                type="button"
                onClick={() => switchAuthView('register')}
                className={`h-10 rounded-xl text-sm font-bold transition-colors ${
                  authView === 'register'
                    ? 'bg-primary text-white'
                    : 'bg-surface-container-high text-on-surface-variant'
                }`}
              >
                Crear cuenta
              </button>
            </div>
          )}

          {loginError && (
            <div className="mb-5 rounded-xl border border-error/20 bg-error/5 text-error px-4 py-3 text-sm font-semibold">
              {loginError}
            </div>
          )}
          {authNotice && (
            <div className="mb-5 rounded-xl border border-primary/20 bg-primary/5 text-primary px-4 py-3 text-sm font-semibold">
              {authNotice}
            </div>
          )}

          {authView === 'login' && (
            <form className="space-y-4" onSubmit={handleLogin}>
              <div>
                <label className="block text-[10px] font-bold text-on-surface-variant uppercase mb-2 ml-1">
                  Email
                </label>
                <input
                  type="email"
                  autoComplete="email"
                  value={loginEmail}
                  onChange={(event) => setLoginEmail(event.target.value)}
                  className="w-full h-12 px-4 rounded-xl border-none bg-surface-container-highest focus:bg-white focus:ring-2 focus:ring-primary/20 transition-all text-sm font-medium"
                  placeholder="tu@email.com"
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-on-surface-variant uppercase mb-2 ml-1">
                  Contrasena
                </label>
                <input
                  type="password"
                  autoComplete="current-password"
                  value={loginPassword}
                  onChange={(event) => setLoginPassword(event.target.value)}
                  className="w-full h-12 px-4 rounded-xl border-none bg-surface-container-highest focus:bg-white focus:ring-2 focus:ring-primary/20 transition-all text-sm font-medium"
                  placeholder="********"
                />
              </div>
              <button
                type="submit"
                disabled={loginLoading}
                className="w-full h-12 primary-gradient text-white font-bold rounded-xl shadow-lg hover:shadow-primary/30 transition-all active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loginLoading ? <Loader2 size={18} className="animate-spin" /> : <LogIn size={18} />}
                {loginLoading ? 'Entrando...' : 'Entrar'}
              </button>
            </form>
          )}

          {authView === 'register' && (
            <form className="space-y-4" onSubmit={handleRegister}>
              <div>
                <label className="block text-[10px] font-bold text-on-surface-variant uppercase mb-2 ml-1">
                  Email
                </label>
                <input
                  type="email"
                  autoComplete="email"
                  value={registerEmail}
                  onChange={(event) => setRegisterEmail(event.target.value)}
                  className="w-full h-12 px-4 rounded-xl border-none bg-surface-container-highest focus:bg-white focus:ring-2 focus:ring-primary/20 transition-all text-sm font-medium"
                  placeholder="tu@email.com"
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-on-surface-variant uppercase mb-2 ml-1">
                  Contrasena (min 12)
                </label>
                <input
                  type="password"
                  autoComplete="new-password"
                  value={registerPassword}
                  onChange={(event) => setRegisterPassword(event.target.value)}
                  className="w-full h-12 px-4 rounded-xl border-none bg-surface-container-highest focus:bg-white focus:ring-2 focus:ring-primary/20 transition-all text-sm font-medium"
                  placeholder="************"
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-on-surface-variant uppercase mb-2 ml-1">
                  Repite contrasena
                </label>
                <input
                  type="password"
                  autoComplete="new-password"
                  value={registerConfirmPassword}
                  onChange={(event) => setRegisterConfirmPassword(event.target.value)}
                  className="w-full h-12 px-4 rounded-xl border-none bg-surface-container-highest focus:bg-white focus:ring-2 focus:ring-primary/20 transition-all text-sm font-medium"
                  placeholder="************"
                />
              </div>
              <button
                type="submit"
                disabled={registerLoading}
                className="w-full h-12 primary-gradient text-white font-bold rounded-xl shadow-lg hover:shadow-primary/30 transition-all active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {registerLoading ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <UserPlus size={18} />
                )}
                {registerLoading ? 'Creando...' : 'Crear cuenta'}
              </button>
            </form>
          )}

          {authView === 'verify' && (
            <form className="space-y-4" onSubmit={handleVerifyEmail}>
              <div className="text-xs font-semibold text-on-surface-variant">
                {pendingVerificationEmail
                  ? `Email pendiente: ${pendingVerificationEmail}`
                  : 'Introduce el token de verificacion recibido por email.'}
              </div>
              <div>
                <label className="block text-[10px] font-bold text-on-surface-variant uppercase mb-2 ml-1">
                  Token de verificacion
                </label>
                <input
                  type="text"
                  value={verifyToken}
                  onChange={(event) => setVerifyToken(event.target.value)}
                  className="w-full h-12 px-4 rounded-xl border-none bg-surface-container-highest focus:bg-white focus:ring-2 focus:ring-primary/20 transition-all text-sm font-medium"
                  placeholder="Pega aqui el token"
                />
              </div>
              <button
                type="submit"
                disabled={verifyLoading}
                className="w-full h-12 primary-gradient text-white font-bold rounded-xl shadow-lg hover:shadow-primary/30 transition-all active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {verifyLoading ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <ShieldCheck size={18} />
                )}
                {verifyLoading ? 'Verificando...' : 'Verificar cuenta'}
              </button>
              <button
                type="button"
                onClick={handleResendVerification}
                disabled={verifyLoading}
                className="w-full h-11 bg-surface-container-high text-on-surface font-bold rounded-xl transition-colors hover:bg-surface-container-highest disabled:opacity-70 disabled:cursor-not-allowed"
              >
                Reenviar verificacion
              </button>
              <button
                type="button"
                onClick={() => switchAuthView('login')}
                className="w-full h-11 bg-surface-container-low text-on-surface-variant font-bold rounded-xl transition-colors hover:bg-surface-container-high"
              >
                Volver al login
              </button>
            </form>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface">
      <Sidebar userEmail={authUser?.email} onLogout={handleLogout} />

      <main className="ml-64 mr-[400px] p-8">
        <header className="mb-10">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="font-manrope text-3xl font-extrabold text-on-surface tracking-tight mb-2">
                Price Tracker Dashboard
              </h2>
              <p className="text-on-surface-variant font-medium">
                Monitoring product prices and alerting you when targets are reached.
              </p>
            </div>
            <button
              onClick={handleCheckNow}
              disabled={runningCheck || totalTracked === 0}
              className="h-11 px-5 primary-gradient text-white font-bold rounded-xl shadow-lg hover:shadow-primary/30 transition-all active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {runningCheck ? <Loader2 size={18} className="animate-spin" /> : <RefreshCw size={18} />}
              {runningCheck ? 'Updating...' : 'Update now'}
            </button>
          </div>
        </header>

        {errorMessage && (
          <div className="mb-6 rounded-xl border border-error/20 bg-error/5 text-error px-4 py-3 text-sm font-semibold">
            {errorMessage}
          </div>
        )}
        {infoMessage && (
          <div className="mb-6 rounded-xl border border-primary/20 bg-primary/5 text-primary px-4 py-3 text-sm font-semibold">
            {infoMessage}
          </div>
        )}

        <section className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <KPICard
            label="Total Tracked"
            value={totalTracked}
            subtext={drops > 0 ? `${drops} below target` : 'No active drops'}
            subtextColor="text-primary"
            icon={BarChart3}
          />
          <KPICard
            label="Active Data"
            value={activeTracked}
            subtext={totalTracked > 0 ? 'Connected to backend' : 'No products yet'}
            icon={Activity}
          />
          <KPICard
            label="Incidents"
            value={incidents}
            subtext={incidents > 0 ? 'Action required' : 'Everything healthy'}
            subtextColor="text-tertiary-container"
            icon={AlertTriangle}
            variant="tertiary"
          />
        </section>

        <section className="bg-surface-container-low p-8 rounded-2xl mb-12 border border-outline-variant/10">
          <h3 className="font-manrope text-lg font-bold mb-6 flex items-center gap-2">
            <PlusCircle size={20} className="text-primary" />
            Track New Item
          </h3>
          <form className="flex flex-col md:flex-row gap-4" onSubmit={handleSaveProduct}>
            <div className="flex-1">
              <label className="block text-[10px] font-bold text-on-surface-variant uppercase mb-2 ml-1">
                Product URL
              </label>
              <input
                type="text"
                value={urlInput}
                onChange={(event) => setUrlInput(event.target.value)}
                placeholder="https://amazon.es/dp/..."
                className="w-full h-12 px-4 rounded-xl border-none bg-surface-container-highest focus:bg-white focus:ring-2 focus:ring-primary/20 transition-all text-sm font-medium"
              />
            </div>
            <div className="w-full md:w-48">
              <label className="block text-[10px] font-bold text-on-surface-variant uppercase mb-2 ml-1">
                Target Price (EUR)
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={targetPriceInput}
                onChange={(event) => setTargetPriceInput(event.target.value)}
                placeholder="0.00"
                className="w-full h-12 px-4 rounded-xl border-none bg-surface-container-highest focus:bg-white focus:ring-2 focus:ring-primary/20 transition-all text-sm font-medium"
              />
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={savingProduct}
                className="h-12 px-8 primary-gradient text-white font-bold rounded-xl shadow-lg hover:shadow-primary/30 transition-all active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {savingProduct && <Loader2 size={16} className="animate-spin" />}
                {savingProduct ? 'Saving...' : 'Save Product'}
              </button>
            </div>
          </form>
        </section>

        <section>
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-manrope text-xl font-extrabold tracking-tight">Active Monitors</h3>
            <div className="flex gap-2">
              <button
                type="button"
                className="p-2 rounded-lg bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest transition-colors"
              >
                <Filter size={18} />
              </button>
              <button
                type="button"
                className="p-2 rounded-lg bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest transition-colors"
              >
                <LayoutGrid size={18} />
              </button>
            </div>
          </div>

          {productsLoading ? (
            <div className="bg-surface-container-lowest rounded-2xl p-8 text-on-surface-variant font-semibold flex items-center gap-3">
              <Loader2 size={18} className="animate-spin" />
              Loading products...
            </div>
          ) : products.length === 0 ? (
            <div className="bg-surface-container-lowest rounded-2xl p-8 text-on-surface-variant font-semibold">
              No products tracked yet. Add your first URL above.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {products.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  isSelected={selectedProduct?.id === product.id}
                  onClick={() => setSelectedProductId(product.id)}
                />
              ))}
            </div>
          )}
        </section>
      </main>

      <DetailsPanel
        product={selectedProduct}
        history={selectedHistory}
        historyLoading={historyLoading}
        deleting={deletingProduct}
        savingEdit={savingEditAlert}
        onClose={() => setSelectedProductId(null)}
        onDelete={handleDeleteProduct}
        onEditAlert={handleEditAlert}
      />
    </div>
  );
}
