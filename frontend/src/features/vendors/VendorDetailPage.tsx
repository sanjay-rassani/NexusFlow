import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, MapPin, Package, Store } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { fetchVendor, fetchVendorProducts, type Product } from "../../api/vendors";

function ProductCard({ product }: { product: Product }) {
  return (
    <div
      className={`flex items-center justify-between gap-4 p-4 rounded-xl border transition-colors ${
        product.is_available
          ? "border-gray-100 bg-white hover:border-indigo-100"
          : "border-gray-100 bg-gray-50 opacity-60"
      }`}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h4 className="font-medium text-gray-900 truncate">{product.name}</h4>
          {!product.is_available && (
            <span className="text-xs bg-gray-200 text-gray-500 px-2 py-0.5 rounded-full flex-shrink-0">
              Unavailable
            </span>
          )}
        </div>
        {product.description && (
          <p className="text-sm text-gray-500 mt-0.5 truncate">
            {product.description}
          </p>
        )}
        {product.category && (
          <span className="text-xs text-indigo-500 mt-1 block">
            {product.category.name}
          </span>
        )}
      </div>

      <div className="flex-shrink-0 text-right">
        <span className="font-semibold text-gray-900">${product.price}</span>
        {product.stock_count > 0 && (
          <p className="text-xs text-gray-400 mt-0.5">{product.stock_count} left</p>
        )}
      </div>
    </div>
  );
}

export default function VendorDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: vendor, isLoading: vendorLoading } = useQuery({
    queryKey: ["vendor", id],
    queryFn: () => fetchVendor(id!),
    enabled: !!id,
    staleTime: 5 * 60_000,
  });

  const { data: products, isLoading: productsLoading } = useQuery({
    queryKey: ["vendor-products", id],
    queryFn: () => fetchVendorProducts(id!),
    enabled: !!id,
    staleTime: 5 * 60_000,
  });

  if (vendorLoading) {
    return (
      <div className="space-y-4">
        <div className="h-32 rounded-2xl bg-gray-100 animate-pulse" />
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-20 rounded-xl bg-gray-100 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!vendor) {
    return (
      <div className="text-center py-16 text-gray-500">
        <p>Vendor not found.</p>
        <Link to="/vendors" className="text-indigo-600 text-sm mt-2 inline-block hover:underline">
          ← Back to restaurants
        </Link>
      </div>
    );
  }

  return (
    <div>
      {/* Back link */}
      <Link
        to="/vendors"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-5 transition-colors"
      >
        <ArrowLeft size={15} />
        All restaurants
      </Link>

      {/* Vendor header */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-6 flex items-start gap-5">
        <div className="w-16 h-16 rounded-xl bg-indigo-50 flex items-center justify-center flex-shrink-0">
          <Store size={28} className="text-indigo-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-bold text-gray-900">{vendor.name}</h1>
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                vendor.is_open
                  ? "bg-green-50 text-green-700"
                  : "bg-gray-100 text-gray-500"
              }`}
            >
              {vendor.is_open ? "Open" : "Closed"}
            </span>
          </div>
          {vendor.description && (
            <p className="text-sm text-gray-600 mt-1">{vendor.description}</p>
          )}
          {vendor.address && (
            <div className="flex items-center gap-1.5 mt-2 text-xs text-gray-400">
              <MapPin size={12} />
              {vendor.address}
            </div>
          )}
        </div>
      </div>

      {/* Menu */}
      <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <Package size={18} className="text-gray-400" />
        Menu
      </h2>

      {productsLoading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-20 rounded-xl bg-gray-100 animate-pulse" />
          ))}
        </div>
      ) : !products?.results.length ? (
        <div className="text-center py-10 text-gray-400">
          <Package size={36} className="mx-auto mb-2 opacity-30" />
          <p className="text-sm">No menu items available</p>
        </div>
      ) : (
        <div className="space-y-3">
          {products.results.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      )}
    </div>
  );
}
