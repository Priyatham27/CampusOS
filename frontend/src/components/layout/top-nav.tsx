"use client";

import React, { useState } from "react";
import { Search, Bell, Sun, Moon, LogOut, User as UserIcon, Settings, ShieldAlert } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useTheme } from "@/components/theme-provider";
import { cn } from "@/lib/utils";

export function TopNav() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  // Global search placeholder state
  const [searchQuery, setSearchQuery] = useState("");

  const dummyNotifications = [
    { id: 1, title: "Organization Seeded", desc: "CampusOS Academy configuration initialized.", time: "1 hour ago" },
    { id: 2, title: "Security Key Created", desc: "A new administrative token was assigned.", time: "3 hours ago" },
  ];

  return (
    <header className="h-16 border-b border-border glass flex items-center justify-between px-6 sticky top-0 z-20">
      {/* Search Bar Placeholder */}
      <div className="relative max-w-md w-full">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Global search (Ctrl + K)..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full h-9 rounded-lg bg-accent/10 border border-input pl-10 pr-4 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary focus-visible:ring-offset-0 placeholder:text-muted-foreground transition-all duration-200"
        />
      </div>

      {/* Action Utilities */}
      <div className="flex items-center gap-4">
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="h-9 w-9 rounded-lg hover:bg-accent/15 border border-border flex items-center justify-center text-foreground transition-all cursor-pointer"
          title="Toggle Light/Dark Theme"
        >
          {theme === "dark" ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4" />}
        </button>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setNotificationsOpen(!notificationsOpen)}
            className="h-9 w-9 rounded-lg hover:bg-accent/15 border border-border flex items-center justify-center text-foreground transition-all cursor-pointer relative"
          >
            <Bell className="h-4 w-4" />
            <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-primary" />
          </button>

          {/* Notifications Panel */}
          {notificationsOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setNotificationsOpen(false)} />
              <div className="absolute right-0 mt-2 w-80 rounded-xl glass border border-border p-4 shadow-2xl z-50 flex flex-col gap-3">
                <div className="flex justify-between items-center pb-2 border-b border-border">
                  <h4 className="text-sm font-bold text-foreground">Notifications</h4>
                  <span className="text-2xs uppercase font-bold text-primary tracking-wider bg-primary/10 px-2 py-0.5 rounded-full">
                    2 New
                  </span>
                </div>
                <div className="flex flex-col gap-3">
                  {dummyNotifications.map((n) => (
                    <div key={n.id} className="text-xs flex flex-col gap-0.5">
                      <span className="font-semibold text-foreground">{n.title}</span>
                      <span className="text-muted-foreground leading-relaxed">{n.desc}</span>
                      <span className="text-2xs text-muted-foreground/60 mt-1">{n.time}</span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* User Profile Dropdown */}
        <div className="relative">
          <button
            onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
            className="flex items-center gap-3 hover:bg-accent/10 border border-border px-3 py-1.5 rounded-lg text-sm text-foreground transition-all cursor-pointer"
          >
            <div className="h-7 w-7 rounded-full bg-primary/20 text-primary font-bold flex items-center justify-center text-xs">
              {user?.full_name?.charAt(0) || "U"}
            </div>
            <div className="text-left hidden sm:flex flex-col">
              <span className="font-semibold leading-none">{user?.full_name || "Guest"}</span>
              <span className="text-3xs font-bold uppercase tracking-wider text-muted-foreground mt-0.5">
                {user?.role?.name || "Member"}
              </span>
            </div>
          </button>

          {profileDropdownOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setProfileDropdownOpen(false)} />
              <div className="absolute right-0 mt-2 w-56 rounded-xl glass border border-border p-2 shadow-2xl z-50 flex flex-col gap-1">
                <div className="px-3 py-2 border-b border-border mb-1 text-xs">
                  <p className="font-bold text-foreground truncate">{user?.full_name}</p>
                  <p className="text-muted-foreground truncate text-3xs">{user?.email}</p>
                </div>
                <button
                  onClick={() => {
                    setProfileDropdownOpen(false);
                    // Action placeholder
                  }}
                  className="flex items-center gap-2 px-3 py-2 text-xs text-foreground hover:bg-accent/10 rounded-lg text-left transition-all"
                >
                  <UserIcon className="h-4 w-4 text-muted-foreground" />
                  My Profile
                </button>
                <button
                  onClick={() => {
                    setProfileDropdownOpen(false);
                    // Action placeholder
                  }}
                  className="flex items-center gap-2 px-3 py-2 text-xs text-foreground hover:bg-accent/10 rounded-lg text-left transition-all"
                >
                  <Settings className="h-4 w-4 text-muted-foreground" />
                  Branding Controls
                </button>
                <button
                  onClick={() => {
                    setProfileDropdownOpen(false);
                    logout();
                  }}
                  className="flex items-center gap-2 px-3 py-2 text-xs text-rose-500 hover:bg-rose-500/10 rounded-lg text-left transition-all"
                >
                  <LogOut className="h-4 w-4" />
                  Log Out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

export default TopNav;
