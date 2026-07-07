"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "./use-auth";

export function useFeatureFlags() {
  const { isAuthenticated } = useAuth();

  const { data: flags = {}, isLoading } = useQuery<Record<string, boolean>>({
    queryKey: ["feature_flags"],
    queryFn: async () => {
      try {
        const resolved = await api.get<Record<string, boolean>>("/settings/feature-flags");
        return resolved;
      } catch (err) {
        console.error("Failed to load feature flags:", err);
        return {};
      }
    },
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 10, // 10 minutes cache
  });

  const isEnabled = (flagName: string): boolean => {
    return !!flags[flagName];
  };

  return {
    flags,
    isLoading,
    isEnabled,
  };
}

export default useFeatureFlags;
