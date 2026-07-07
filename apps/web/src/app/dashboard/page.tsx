"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { useFeatureFlags } from "@/hooks/use-feature-flags";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import {
  Users,
  ShieldCheck,
  ToggleLeft,
  ToggleRight,
  Sparkles,
  CalendarDays,
  Lock,
  Layers,
  GraduationCap
} from "lucide-react";

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { flags, isEnabled, isLoading: flagsLoading } = useFeatureFlags();
  const { success, error: toastError } = useToast();

  // Fetch count of users and roles for stats
  const { data: users = [] } = useQuery<any[]>({
    queryKey: ["users_list"],
    queryFn: () => api.get<any[]>("/users"),
  });

  const { data: roles = [] } = useQuery<any[]>({
    queryKey: ["roles_list"],
    queryFn: () => api.get<any[]>("/roles"),
  });

  // Flag toggle mutation
  const toggleFlagMutation = useMutation({
    mutationFn: async ({ name, enabled }: { name: string; enabled: boolean }) => {
      return api.post<Record<string, boolean>>("/settings/feature-flags", {
        [name]: enabled,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["feature_flags"] });
      success("Feature Updated", "Platform module configurations updated.");
    },
    onError: (err: any) => {
      toastError("Failed to update feature", err?.detail || "An error occurred.");
    },
  });

  const handleToggleFlag = (name: string, currentStatus: boolean) => {
    toggleFlagMutation.mutate({ name, enabled: !currentStatus });
  };

  const tenantName = user?.tenant?.name || "CampusOS Academy";

  return (
    <div className="flex flex-col gap-8">
      {/* Welcome Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass p-6 rounded-xl border border-border">
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">
            <GraduationCap className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
              Welcome back, {user?.full_name || "User"} <Sparkles className="h-4 w-4 text-primary animate-pulse" />
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Managing white-labeled environment for <span className="font-semibold text-foreground">{tenantName}</span>.
            </p>
          </div>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card glass>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              Total Users
            </CardTitle>
            <Users className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{users.length}</div>
            <p className="text-3xs text-muted-foreground mt-1">Scope: Active Organization members</p>
          </CardContent>
        </Card>

        <Card glass>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              Configured Roles
            </CardTitle>
            <ShieldCheck className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{roles.length}</div>
            <p className="text-3xs text-muted-foreground mt-1">Scope: Security profiles</p>
          </CardContent>
        </Card>

        <Card glass>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              Primary System Theme
            </CardTitle>
            <Layers className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold flex items-center gap-2">
              <span
                className="h-3 w-3 rounded-full border border-border inline-block"
                style={{ backgroundColor: user?.tenant?.config?.theme?.primary_color || "#4f46e5" }}
              />
              {user?.tenant?.config?.theme?.primary_color || "#4f46e5"}
            </div>
            <p className="text-3xs text-muted-foreground mt-1">Status: Applied to dynamic layout styles</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Feature Flags Module Toggles */}
        <Card glass className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Feature Flag System</CardTitle>
            <CardDescription>
              Toggle modular plug-ins for this tenant. Enabling options here unlocks secondary sidebar items.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {flagsLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : (
              <div className="divide-y divide-border">
                {Object.entries(flags).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between py-3.5 first:pt-0 last:pb-0">
                    <div>
                      <h4 className="text-sm font-semibold text-foreground capitalize">
                        {key.replace("enable_", "").replace("_", " ")}
                      </h4>
                      <p className="text-2xs text-muted-foreground mt-0.5">
                        {key === "enable_events" && "Organize campus events, bookings, and RSVP sheets."}
                        {key === "enable_attendance" && "Dynamic QR scanner logs for classes and lecture halls."}
                        {key === "enable_certificates" && "Credential generation, signatures, and batch distributions."}
                        {key === "enable_clubs" && "Student organizations, budgets, approvals, and listings."}
                        {key === "enable_analytics" && "Aggregated summaries, activity logs, and feedback scores."}
                        {key === "enable_audit_logs" && "Core administrative and security log tracking."}
                        {key === "enable_file_uploads" && "Standard file attachment uploads (PDF/Images)."}
                      </p>
                    </div>
                    
                    <button
                      onClick={() => handleToggleFlag(key, val)}
                      disabled={toggleFlagMutation.isPending}
                      className="text-primary hover:text-primary/80 transition-colors disabled:opacity-50 cursor-pointer"
                    >
                      {val ? (
                        <ToggleRight className="h-8 w-8 text-primary" />
                      ) : (
                        <ToggleLeft className="h-8 w-8 text-muted-foreground/60" />
                      )}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Extensions Sidebar widgets */}
        <Card glass>
          <CardHeader>
            <CardTitle>Module Integrations</CardTitle>
            <CardDescription>Preview of modular expansion capabilities.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3 p-3.5 border border-border rounded-lg relative overflow-hidden">
              <div className="h-9 w-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">
                <CalendarDays className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <h4 className="text-xs font-semibold text-foreground">Events Manager</h4>
                <p className="text-3xs text-muted-foreground truncate mt-0.5">
                  {isEnabled("enable_events") ? "Active and running" : "Status: Locked"}
                </p>
              </div>
              {!isEnabled("enable_events") && (
                <Lock className="absolute right-3.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              )}
            </div>

            <div className="p-4 bg-primary/5 rounded-lg border border-primary/10 text-xs leading-relaxed text-muted-foreground">
              <span className="font-semibold text-primary block mb-1">Founding Architecture Note</span>
              CampusOS employs an extensible feature flag architecture. Future plugins (like `events` or `attendance`) can be loaded instantly by dropping routes into the router layer and checking feature checks.
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
