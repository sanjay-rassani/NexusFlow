import { api } from "./axios";

export interface Vendor {
  id: string;
  name: string;
  description: string;
  address: string;
  phone: string;
  is_open: boolean;
  is_active: boolean;
  created_at: string;
}

export interface Product {
  id: string;
  name: string;
  description: string;
  price: string;
  stock_count: number;
  is_available: boolean;
  category: { id: string; name: string } | null;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export async function fetchVendors(params?: Record<string, string>) {
  const { data } = await api.get<PaginatedResponse<Vendor>>("/vendors/", {
    params,
  });
  return data;
}

export async function fetchVendor(id: string) {
  const { data } = await api.get<Vendor>(`/vendors/${id}/`);
  return data;
}

export async function fetchVendorProducts(
  vendorId: string,
  params?: Record<string, string>,
) {
  const { data } = await api.get<PaginatedResponse<Product>>(
    `/vendors/${vendorId}/products/`,
    { params },
  );
  return data;
}
