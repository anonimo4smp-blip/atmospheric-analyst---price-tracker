export type ProductStatus = 'ACTIVE' | 'DROP ALERT' | 'ERROR' | 'PENDING';

export interface Product {
  id: number;
  url: string;
  name: string;
  store: string;
  status: ProductStatus;
  currentPrice: number | null;
  originalPrice?: number;
  targetPrice: number;
  imageUrl: string;
  trackingSince: string;
  currency: string;
  checkedAt: string | null;
  errorMsg?: string;
  pendingMsg?: string;
}

export interface PriceHistoryPoint {
  date: string;
  price: number;
}

export interface ApiProduct {
  id: number;
  url: string;
  store: string;
  title: string | null;
  image_url: string | null;
  desired_price: number;
  last_price: number | null;
  currency: string;
  last_status: string;
  last_error: string | null;
  last_checked_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApiPriceHistoryPoint {
  id: number;
  product_id: number;
  title_snapshot: string | null;
  price: number | null;
  currency: string;
  status: string;
  error_message: string | null;
  checked_at: string;
}

export interface ApiCheckNowSummary {
  total_products: number;
  checked_ok: number;
  checked_failed: number;
  alerts_created: number;
}

export interface ApiAuthUser {
  id: number;
  email: string;
  is_email_verified: boolean;
  is_active: boolean;
  created_at: string;
}

export interface ApiLoginResponse {
  user: ApiAuthUser;
}

export interface ApiAuthMessageResponse {
  message: string;
  debug_token: string | null;
}
