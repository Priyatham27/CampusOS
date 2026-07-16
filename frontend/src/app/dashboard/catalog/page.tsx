"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BookText,
  CheckCircle2,
  FileEdit,
  Archive,
  PlusCircle,
  GitMerge,
  Layers,
  TrendingUp,
} from "lucide-react";
import { Curriculum } from "@/types/catalog";

interface ListResponse {
  data: Curriculum[];
  meta: { total: number };
}

const statusColors: Record<string, string> = {
  ACTIVE: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  DRAFT: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  ARCHIVED: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
};

export default function CatalogDashboard() {
  const { user } = useAuth();
  const orgId = user?.tenant?.organizationId || "";

  const { data: allCurricula = [], isLoading } = useQuery<Curriculum[]>({
    queryKey: ["curricula", orgId],
    queryFn: async () => {
      const res = await api.get<any>(`/organizations/${orgId}/catalog/curricula?limit=100`);
      return Array.isArray(res) ? res : res?.data ?? res ?? [];
    },
    enabled: !!orgId,
  });

  const total = allCurricula.length;
  const active = allCurricula.filter((c) => c.status === "ACTIVE").length;
  const draft = allCurricula.filter((c) => c.status === "DRAFT").length;
  const archived = allCurricula.filter((c) => c.status === "ARCHIVED").length;
  const totalCredits = allCurricula.reduce((sum, c) => sum + (c.totalCredits || 0), 0);

  const statsCards = [
    {
      label: "Total Curricula",
      value: total,
      icon: BookText,
      color: "bg-violet-500/20 text-violet-400",
    },
    {
      label: "Active Versions",
      value: active,
      icon: CheckCircle2,
      color: "bg-emerald-500/20 text-emerald-400",
    },
    {
      label: "Drafts",
      value: draft,
      icon: FileEdit,
      color: "bg-amber-500/20 text-amber-400",
    },
    {
      label: "Archived",
      value: archived,
      icon: Archive,
      color: "bg-zinc-500/20 text-zinc-400",
    },
  ];

  const quickActions = [
    {
      title: "New Curriculum",
      desc: "Start a new versioned curriculum plan",
      href: "/dashboard/catalog/curricula?create=true",
      icon: PlusCircle,
      color: "text-violet-400 bg-violet-500/10",
    },
    {
      title: "Browse Curricula",
      desc: "View all versions and lifecycle status",
      href: "/dashboard/catalog/curricula",
      icon: BookText,
      color: "text-sky-400 bg-sky-500/10",
    },
    {
      title: "Prerequisite Graphs",
      desc: "Visualize subject dependency chains",
      href: "/dashboard/catalog/prerequisites",
      icon: GitMerge,
      color: "text-pink-400 bg-pink-500/10",
    },
  ];

  const recentCurricula = [...allCurricula]
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    .slice(0, 5);

  return (
    <div className="flex flex-col gap-6">
      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statsCards.map((card) => (
          <Card
            key={card.label}
            glass
            className="flex items-center gap-4 hover:translate-y-[-2px] transition-transform duration-200"
          >
            <div className={`h-10 w-10 rounded-lg flex items-center justify-center flex-shrink-0 ${card.color}`}>
              <card.icon className="h-5 w-5" />
            </div>
            <div className="flex flex-col">
              <span className="text-2xs font-bold text-muted-foreground uppercase tracking-wider">
                {card.label}
              </span>
              {isLoading ? (
                <Skeleton className="h-6 w-10 mt-1" />
              ) : (
                <span className="text-xl font-bold">{card.value}</span>
              )}
            </div>
          </Card>
        ))}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Recent Curricula + Quick Actions */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          {/* Quick Actions */}
          <div className="flex flex-col gap-3">
            <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest">
              Quick Actions
            </span>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {quickActions.map((act) => (
                <Link key={act.title} href={act.href}>
                  <Card
                    glass
                    className="flex items-start gap-3 p-5 hover:bg-accent/5 transition-colors cursor-pointer group h-full"
                  >
                    <div
                      className={`h-9 w-9 rounded-lg flex items-center justify-center flex-shrink-0 ${act.color}`}
                    >
                      <act.icon className="h-4.5 w-4.5" />
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span className="text-sm font-semibold group-hover:text-primary transition-colors">
                        {act.title}
                      </span>
                      <span className="text-2xs text-muted-foreground leading-snug">
                        {act.desc}
                      </span>
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          </div>

          {/* Recent Curricula Table */}
          <Card glass>
            <div className="flex flex-col gap-4">
              <div className="flex justify-between items-center border-b border-border pb-3">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                  Recent Curricula
                </span>
                <Link
                  href="/dashboard/catalog/curricula"
                  className="text-2xs text-primary font-semibold hover:underline"
                >
                  View All →
                </Link>
              </div>

              {isLoading ? (
                <div className="space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <Skeleton key={i} className="h-10 w-full" />
                  ))}
                </div>
              ) : recentCurricula.length === 0 ? (
                <div className="text-center py-8 text-xs text-muted-foreground">
                  <BookText className="h-8 w-8 mx-auto mb-2 opacity-30" />
                  No curricula yet. Start by creating your first curriculum.
                </div>
              ) : (
                <div className="flex flex-col divide-y divide-border">
                  {recentCurricula.map((c) => (
                    <Link
                      key={c.curriculumId}
                      href={`/dashboard/catalog/curricula/${c.curriculumId}`}
                      className="flex items-center justify-between py-3 hover:bg-accent/5 -mx-1 px-1 rounded transition-colors"
                    >
                      <div className="flex flex-col gap-0.5">
                        <span className="text-sm font-semibold">{c.name}</span>
                        <span className="text-2xs text-muted-foreground">
                          v{c.version} · {c.totalCredits} credits
                          {c.admissionBatch ? ` · Batch ${c.admissionBatch}` : ""}
                        </span>
                      </div>
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-3xs font-bold uppercase tracking-wider border ${
                          statusColors[c.status] || ""
                        }`}
                      >
                        {c.status}
                      </span>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Right: Engine Health */}
        <div className="flex flex-col gap-6">
          <Card glass>
            <div className="flex flex-col gap-4">
              <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider border-b border-border pb-2.5">
                Catalog Engine Status
              </span>

              <div className="flex flex-col gap-4">
                <div className="flex justify-between items-start text-xs">
                  <div className="flex flex-col gap-0.5">
                    <span className="font-semibold">Versioning Engine</span>
                    <span className="text-3xs text-muted-foreground">DRAFT → ACTIVE → ARCHIVED</span>
                  </div>
                  <span className="inline-flex items-center gap-1 text-emerald-400 font-bold text-2xs uppercase">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Active
                  </span>
                </div>

                <div className="flex justify-between items-start text-xs">
                  <div className="flex flex-col gap-0.5">
                    <span className="font-semibold">Cycle Detection</span>
                    <span className="text-3xs text-muted-foreground">DFS prerequisite validation</span>
                  </div>
                  <span className="inline-flex items-center gap-1 text-emerald-400 font-bold text-2xs uppercase">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Enabled
                  </span>
                </div>

                <div className="flex justify-between items-start text-xs">
                  <div className="flex flex-col gap-0.5">
                    <span className="font-semibold">Weight Validation</span>
                    <span className="text-3xs text-muted-foreground">Assessment scheme 100% rule</span>
                  </div>
                  <span className="inline-flex items-center gap-1 text-emerald-400 font-bold text-2xs uppercase">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Enforced
                  </span>
                </div>

                <div className="flex justify-between items-start text-xs">
                  <div className="flex flex-col gap-0.5">
                    <span className="font-semibold">Clone Engine</span>
                    <span className="text-3xs text-muted-foreground">Non-destructive versioning</span>
                  </div>
                  <span className="inline-flex items-center gap-1 text-emerald-400 font-bold text-2xs uppercase">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Ready
                  </span>
                </div>
              </div>

              {!isLoading && totalCredits > 0 && (
                <div className="mt-2 pt-3 border-t border-border">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground font-semibold flex items-center gap-1">
                      <TrendingUp className="h-3.5 w-3.5" />
                      Total Credits Catalogued
                    </span>
                    <span className="font-bold text-violet-400">{totalCredits.toFixed(1)}</span>
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
