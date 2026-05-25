import { lazy, Suspense } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { ProtectedRoute } from "./ProtectedRoute";

// Lazy-loaded pages for code splitting
const LoginPage = lazy(() => import("../features/auth/LoginPage"));
const RegisterPage = lazy(() => import("../features/auth/RegisterPage"));
const VendorListPage = lazy(() => import("../features/vendors/VendorListPage"));
const VendorDetailPage = lazy(
  () => import("../features/vendors/VendorDetailPage"),
);
const OrderListPage = lazy(() => import("../features/orders/OrderListPage"));
const OrderDetailPage = lazy(
  () => import("../features/orders/OrderDetailPage"),
);

function PageLoader() {
  return (
    <div className="flex h-64 items-center justify-center">
      <span className="text-sm text-gray-400 animate-pulse">Loading…</span>
    </div>
  );
}

function withSuspense(Component: React.ComponentType) {
  return (
    <Suspense fallback={<PageLoader />}>
      <Component />
    </Suspense>
  );
}

export const router = createBrowserRouter([
  // Public routes
  {
    path: "/login",
    element: withSuspense(LoginPage),
  },
  {
    path: "/register",
    element: withSuspense(RegisterPage),
  },

  // Authenticated routes (all roles)
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <Layout />,
        children: [
          { index: true, element: <Navigate to="/vendors" replace /> },

          // Vendor browsing — all authenticated users
          { path: "vendors", element: withSuspense(VendorListPage) },
          { path: "vendors/:id", element: withSuspense(VendorDetailPage) },

          // Customer orders
          {
            element: <ProtectedRoute allowedRoles={["CUSTOMER"]} />,
            children: [
              { path: "orders", element: withSuspense(OrderListPage) },
              { path: "orders/:id", element: withSuspense(OrderDetailPage) },
            ],
          },
        ],
      },
    ],
  },

  // Fallback
  { path: "*", element: <Navigate to="/" replace /> },
]);
