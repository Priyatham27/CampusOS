"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { useFeatureFlags } from "@/hooks/use-feature-flags";
import {
  LayoutDashboard,
  Users,
  ShieldCheck,
  Settings,
  History,
  Calendar,
  Award,
  UsersRound,
  BarChart3,
  Lock,
  ChevronLeft,
  ChevronRight,
  GraduationCap
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  collapsed: boolean;
  setCollapsed: (c: boolean) => void;
}

export function Sidebar({ collapsed, setCollapsed }: SidebarProps) {
  const pathname = usePathname();
  const { user } = useAuth();
  const { isEnabled } = useFeatureFlags();

  const tenantName = user?.tenant?.name || "CampusOS Academy";
  const tenantLogo = user?.tenant?.config?.theme?.logo_url;

  const coreNav = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Academic", href: "/dashboard/academic", icon: GraduationCap, perm: "academic:read" },
    { name: "Users", href: "/dashboard/users", icon: Users, perm: "users:read" },
    { name: "Roles & RBAC", href: "/dashboard/roles", icon: ShieldCheck, perm: "roles:read" },
    { name: "Audit Trail", href: "/dashboard/audit", icon: History, perm: "audit:read" },
    { name: "Settings", href: "/dashboard/settings", icon: Settings, perm: "settings:read" },
  ];

  const modularNav = [
    { name: "Events Manager", href: "/dashboard/events", icon: Calendar, flag: "enable_events" },
    { name: "Attendance Check", href: "/dashboard/attendance", icon: UsersRound, flag: "enable_attendance" },
    { name: "Certificates", href: "/dashboard/certificates", icon: Award, flag: "enable_certificates" },
    { name: "Clubs Portal", href: "/dashboard/clubs", icon: UsersRound, flag: "enable_clubs" },
    { name: "Campus Analytics", href: "/dashboard/analytics", icon: BarChart3, flag: "enable_analytics" },
  ];

  // Helper check for role permission list
  const hasPermission = (permName?: string) => {
    if (!permName) return true;
    if (!user?.role?.permissions) return false;
    return user.role.permissions.includes("*") || user.role.permissions.includes(permName);
  };

  return (
    <aside
      className={cn(
        "glass border-r border-border h-screen sticky top-0 flex flex-col transition-all duration-300 z-30 select-none",
        collapsed ? "w-20" : "w-64"
      )}
    >
      {/* Branding Header */}
      <div className="h-16 flex items-center gap-3 px-4 border-b border-border">
        {tenantLogo ? (
          <img src={tenantLogo} alt="Logo" className="h-8 w-8 rounded-lg object-cover flex-shrink-0" />
        ) : (
          <div className="h-8 w-8 rounded-lg bg-primary/20 text-primary flex items-center justify-center flex-shrink-0">
            <GraduationCap className="h-5 w-5" />
          </div>
        )}
        {!collapsed && (
          <span className="font-bold text-sm tracking-wide text-foreground truncate max-w-[170px]">
            {tenantName}
          </span>
        )}
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto py-4 px-3 space-y-6">
        {/* Core Modules Group */}
        <div>
          {!collapsed && (
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest px-3 mb-2">
              Platform Core
            </p>
          )}
          <nav className="space-y-1">
            {coreNav.map((item) => {
              if (!hasPermission(item.perm)) return null;
              const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href + "/"));
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group",
                    isActive
                      ? "bg-primary text-primary-foreground shadow"
                      : "text-muted-foreground hover:text-foreground hover:bg-accent/15"
                  )}
                >
                  <item.icon className="h-4 w-4 flex-shrink-0" />
                  {!collapsed && <span>{item.name}</span>}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Extensions Group */}
        <div>
          {!collapsed && (
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest px-3 mb-2">
              Modules & Extensions
            </p>
          )}
          <nav className="space-y-1">
            {modularNav.map((item) => {
              const active = isEnabled(item.flag);
              return (
                <div
                  key={item.name}
                  className={cn(
                    "flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium select-none transition-all",
                    active
                      ? "text-muted-foreground hover:text-foreground hover:bg-accent/15 cursor-pointer"
                      : "opacity-45 text-muted-foreground bg-transparent"
                  )}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <item.icon className="h-4 w-4 flex-shrink-0" />
                    {!collapsed && <span className="truncate">{item.name}</span>}
                  </div>
                  {!active && !collapsed && (
                    <Lock className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                  )}
                </div>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Collapse Toggle Trigger */}
      <div className="p-4 border-t border-border flex justify-end">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="h-8 w-8 rounded-lg bg-accent/10 border border-border flex items-center justify-center hover:bg-accent/20 text-foreground transition-all cursor-pointer"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
