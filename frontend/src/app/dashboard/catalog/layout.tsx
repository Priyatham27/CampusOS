"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Library,
  LayoutGrid,
  BookText,
  GitMerge,
} from "lucide-react";

interface TabItem {
  name: string;
  href: string;
  icon: React.ComponentType<any>;
}

export default function CatalogLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  const tabs: TabItem[] = [
    { name: "Overview", href: "/dashboard/catalog", icon: LayoutGrid },
    { name: "Curricula", href: "/dashboard/catalog/curricula", icon: BookText },
    { name: "Prerequisites", href: "/dashboard/catalog/prerequisites", icon: GitMerge },
  ];

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-xl bg-violet-500/10 text-violet-400 flex items-center justify-center">
            <Library className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Academic Catalog</h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Manage versioned curricula, subjects, prerequisites, and assessment schemes.
            </p>
          </div>
        </div>
      </div>

      {/* Sub-Navigation Tab bar */}
      <div className="w-full border-b border-border overflow-x-auto scrollbar-thin">
        <nav className="flex space-x-1 min-w-max pb-1">
          {tabs.map((tab) => {
            const isActive =
              tab.href === "/dashboard/catalog"
                ? pathname === "/dashboard/catalog"
                : pathname.startsWith(tab.href);

            return (
              <Link
                key={tab.name}
                href={tab.href}
                className={cn(
                  "flex items-center gap-2 px-4 py-2.5 border-b-2 text-xs font-semibold uppercase tracking-wider transition-all select-none whitespace-nowrap cursor-pointer",
                  isActive
                    ? "border-violet-500 text-violet-400"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                )}
              >
                <tab.icon className="h-4 w-4" />
                {tab.name}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Page Content */}
      <div className="flex-1 min-h-0">{children}</div>
    </div>
  );
}
