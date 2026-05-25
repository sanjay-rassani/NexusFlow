import { useQuery } from "@tanstack/react-query";
import { MapPin, Search, Store } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { fetchVendors, type Vendor } from "../../api/vendors";

function VendorCard({ vendor }: { vendor: Vendor }) {
  return (
    <Link
      to={`/vendors/${vendor.id}`}
      className="block bg-white rounded-xl border border-gray-100 p-5 hover:shadow-md hover:border-indigo-100 transition-all group"
    >
      <div className="flex items-start justify-between gap-3">
        {/* Avatar placeholder */}
        <div className="w-12 h-12 rounded-xl bg-indigo-50 flex items-center justify-center flex-shrink-0">
          <Store size={22} className="text-indigo-400" />
        </div>

        <span
          className={`text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0 ${
            vendor.is_open
              ? "bg-green-50 text-green-700"
              : "bg-gray-100 text-gray-500"
          }`}
        >
          {vendor.is_open ? "Open" : "Closed"}
        </span>
      </div>

      <h3 className="mt-3 font-semibold text-gray-900 group-hover:text-indigo-700 transition-colors">
        {vendor.name}
      </h3>

      {vendor.description && (
        <p className="text-sm text-gray-500 mt-1 line-clamp-2">
          {vendor.description}
        </p>
      )}

      {vendor.address && (
        <div className="flex items-center gap-1 mt-3 text-xs text-gray-400">
          <MapPin size={12} />
          <span className="truncate">{vendor.address}</span>
        </div>
      )}
    </Link>
  );
}

export default function VendorListPage() {
  const [search, setSearch] = useState("");
  const [isOpenOnly, setIsOpenOnly] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["vendors", search, isOpenOnly],
    queryFn: () =>
      fetchVendors({
        ...(search && { search }),
        ...(isOpenOnly && { is_open: "true" }),
      }),
    staleTime: 60_000, // use React Query cache — respects backend Redis cache
  });

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Restaurants</h1>
        <p className="text-sm text-gray-500 mt-1">
          Browse available vendors and order in real time
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-6">
        <div className="relative flex-1 max-w-sm">
          <Search
            size={15}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            type="text"
            placeholder="Search restaurants…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <button
          onClick={() => setIsOpenOnly((v) => !v)}
          className={`px-4 py-2 text-sm rounded-lg border font-medium transition-colors ${
            isOpenOnly
              ? "bg-indigo-600 border-indigo-600 text-white"
              : "border-gray-300 text-gray-600 hover:border-indigo-300"
          }`}
        >
          Open now
        </button>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="h-44 rounded-xl bg-gray-100 animate-pulse"
            />
          ))}
        </div>
      ) : isError ? (
        <div className="text-center py-16 text-gray-500">
          <p>Failed to load restaurants. Please try again.</p>
        </div>
      ) : !data?.results.length ? (
        <div className="text-center py-16 text-gray-400">
          <Store size={40} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">No restaurants found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.results.map((v) => (
            <VendorCard key={v.id} vendor={v} />
          ))}
        </div>
      )}
    </div>
  );
}
