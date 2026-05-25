import { LogOut, ShoppingBag, Store } from "lucide-react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { logout } from "../api/auth";
import { useAuthStore } from "../store/authStore";
import { useNotificationStore } from "../store/notificationStore";
import { useNotificationSocket } from "../hooks/useNotificationSocket";
import { NotificationBell } from "./NotificationBell";

export function Layout() {
  const { user, reset: resetAuth } = useAuthStore();
  const resetNotifs = useNotificationStore((s) => s.reset);
  const navigate = useNavigate();

  // Connect to real-time notification WebSocket
  useNotificationSocket(!!user);

  async function handleLogout() {
    await logout();
    resetAuth();
    resetNotifs();
    navigate("/login", { replace: true });
  }

  const navLinks = [
    { to: "/vendors", label: "Restaurants", icon: Store },
    ...(user?.role === "CUSTOMER"
      ? [{ to: "/orders", label: "My Orders", icon: ShoppingBag }]
      : []),
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Top navigation bar */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
        <div className="max-w-5xl mx-auto flex items-center justify-between px-4 h-14">
          {/* Logo */}
          <Link to="/" className="text-lg font-bold text-indigo-600">
            NexusFlow
          </Link>

          {/* Nav links */}
          <nav className="flex items-center gap-1">
            {navLinks.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-indigo-50 text-indigo-700"
                      : "text-gray-600 hover:bg-gray-100"
                  }`
                }
              >
                <Icon size={15} />
                {label}
              </NavLink>
            ))}
          </nav>

          {/* Right controls */}
          <div className="flex items-center gap-2">
            <NotificationBell />

            {/* User avatar / name */}
            <div className="flex items-center gap-2 pl-2 border-l border-gray-200">
              <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center">
                <span className="text-xs font-semibold text-indigo-700">
                  {user?.first_name?.[0]?.toUpperCase() ?? "?"}
                </span>
              </div>
              <span className="text-sm text-gray-700 hidden sm:block">
                {user?.first_name}
              </span>
            </div>

            <button
              onClick={handleLogout}
              className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
              title="Sign out"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </header>

      {/* Page content */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-6">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white py-4 text-center text-xs text-gray-400">
        NexusFlow — Real-time distributed delivery platform
      </footer>
    </div>
  );
}
