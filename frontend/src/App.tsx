import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";
import { RouterProvider } from "react-router-dom";
import { fetchMe } from "./api/auth";
import { router } from "./router";
import { useAuthStore } from "./store/authStore";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function AuthHydrator() {
  const { setUser, reset, setLoading } = useAuthStore();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      reset();
      return;
    }

    fetchMe()
      .then(setUser)
      .catch(() => reset());
  }, [setUser, reset, setLoading]);

  return null;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthHydrator />
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
