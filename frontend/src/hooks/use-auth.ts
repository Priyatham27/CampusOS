"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { api } from "@/lib/api";
import { STORAGE_KEYS } from "@/lib/constants";
import { injectBrandingColors } from "@/lib/utils";
import { User, AuthToken } from "@/types";
import { useToast } from "@/components/ui/toast";

export function useAuth() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const { success, error: toastError } = useToast();

  const loggedInFlag = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEYS.LOGGED_IN_FLAG) === "true" : false;

  // Retrieve current user profile
  const {
    data: user,
    isLoading,
    error,
    refetch,
  } = useQuery<User | null>({
    queryKey: ["current_user"],
    queryFn: async () => {
      if (!loggedInFlag) return null;
      try {
        const profile = await api.get<User>("/auth/me");
        return profile;
      } catch (err) {
        // Clear login indicator flag if token/session is invalid
        localStorage.removeItem(STORAGE_KEYS.LOGGED_IN_FLAG);
        return null;
      }
    },
    enabled: loggedInFlag,
    staleTime: 1000 * 60 * 5, // 5 minutes cache
    retry: false, // Do not retry auth endpoint failures
  });

  // Dynamically inject custom HSL themes when tenant configurations load
  useEffect(() => {
    if (user?.tenant?.config?.theme) {
      const { primary_color, secondary_color } = user.tenant.config.theme;
      injectBrandingColors(primary_color, secondary_color);
    }
  }, [user]);

  // Login mutation
  const loginMutation = useMutation({
    mutationFn: async (credentials: Parameters<typeof api.post>[1]) => {
      const res = await api.post<AuthToken>("/auth/login", credentials);
      localStorage.setItem(STORAGE_KEYS.LOGGED_IN_FLAG, "true");
      return res;
    },
    onSuccess: async () => {
      await refetch();
      success("Welcome to CampusOS", "Logged in successfully.");
      router.push("/dashboard");
    },
    onError: (err: any) => {
      toastError("Login Failed", err?.message || "Invalid email or password.");
    },
  });

  // Logout mutation calling backend logout endpoint to clear HttpOnly cookies
  const logoutMutation = useMutation({
    mutationFn: async () => {
      return api.post("/auth/logout");
    },
    onSuccess: () => {
      localStorage.removeItem(STORAGE_KEYS.LOGGED_IN_FLAG);
      queryClient.setQueryData(["current_user"], null);
      success("Logged Out", "You have been logged out of the platform.");
      router.push("/login");
    },
    onError: () => {
      // Force clear even if request fails
      localStorage.removeItem(STORAGE_KEYS.LOGGED_IN_FLAG);
      queryClient.setQueryData(["current_user"], null);
      router.push("/login");
    }
  });

  const logout = () => {
    logoutMutation.mutate();
  };

  return {
    user: user || null,
    isAuthenticated: !!user,
    isLoading: isLoading && loggedInFlag,
    error,
    login: loginMutation.mutate,
    isLoggingIn: loginMutation.isPending,
    logout,
  };
}
export default useAuth;
