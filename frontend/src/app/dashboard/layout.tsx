"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { FullScreenLoader } from "@/components/ui/loading";
import Sidebar from "@/components/layout/sidebar";
import TopNav from "@/components/layout/top-nav";
import { STORAGE_KEYS } from "@/lib/constants";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, isLoading, isAuthenticated } = useAuth();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Guard: Redirect to login if logged in flag is missing
  useEffect(() => {
    const isLoggedIn = localStorage.getItem(STORAGE_KEYS.LOGGED_IN_FLAG) === "true";
    if (!isLoggedIn) {
      router.push("/login");
    }
  }, [router]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      const isLoggedIn = localStorage.getItem(STORAGE_KEYS.LOGGED_IN_FLAG) === "true";
      if (!isLoggedIn) {
        router.push("/login");
      }
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || !isAuthenticated) {
    return <FullScreenLoader message="Authenticating CampusOS Session..." />;
  }

  return (
    <div className="flex min-h-screen bg-background text-foreground transition-all duration-300">
      {/* Sidebar */}
      <Sidebar collapsed={sidebarCollapsed} setCollapsed={setSidebarCollapsed} />

      {/* Main Layout Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopNav />
        <main className="flex-1 p-6 md:p-8 overflow-y-auto max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
