"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  GraduationCap,
  Calendar,
  Building2,
  BookOpen,
  GitBranch,
  Layers,
  Grid,
  Bookmark,
  Search,
  Settings,
  CalendarRange,
} from "lucide-react";

interface TabItem {
  name: string;
  href: string;
  icon: React.ComponentType<any>;
}

export default function AcademicLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  const tabs: TabItem[] = [
    { name: "Overview", href: "/dashboard/academic", icon: GraduationCap },
    { name: "Academic Years", href: "/dashboard/academic/academic-years", icon: Calendar },
    { name: "Departments", href: "/dashboard/academic/departments", icon: Building2 },
    { name: "Programs", href: "/dashboard/academic/programs", icon: BookOpen },
    { name: "Branches", href: "/dashboard/academic/branches", icon: GitBranch },
    { name: "Semesters", href: "/dashboard/academic/semesters", icon: Layers },
    { name: "Calendar & Windows", href: "/dashboard/academic/calendar", icon: CalendarRange },
    { name: "Sections", href: "/dashboard/academic/sections", icon: Grid },
    { name: "Courses", href: "/dashboard/academic/courses", icon: Bookmark },
    { name: "Cross Search", href: "/dashboard/academic/search", icon: Search },
    { name: "Settings & Seeding", href: "/dashboard/academic/settings", icon: Settings },
  ];

  return (
    <div className="flex flex-col gap-6">
      {/* Header section */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
            <GraduationCap className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Academic Platform</h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Administer collegiate structures, semesters, course catalogs, and class sections.
            </p>
          </div>
        </div>
      </div>

      {/* Horizontal Sub-Navigation Tab bar */}
      <div className="w-full border-b border-border overflow-x-auto scrollbar-thin">
        <nav className="flex space-x-1 min-w-max pb-1">
          {tabs.map((tab) => {
            // Match active exactly or check nested routes
            const isActive =
              tab.href === "/dashboard/academic"
                ? pathname === "/dashboard/academic"
                : pathname.startsWith(tab.href);

            return (
              <Link
                key={tab.name}
                href={tab.href}
                className={cn(
                  "flex items-center gap-2 px-4 py-2.5 border-b-2 text-xs font-semibold uppercase tracking-wider transition-all select-none whitespace-nowrap cursor-pointer",
                  isActive
                    ? "border-primary text-primary"
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

      {/* Child Pages Content */}
      <div className="flex-1 min-h-0">{children}</div>
    </div>
  );
}
