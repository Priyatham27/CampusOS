"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  PlusCircle,
  Copy,
  Eye,
  Archive,
  CheckCircle2,
  FileEdit,
  Trash2,
  ChevronUp,
  ChevronDown,
  X,
  BookText,
  Upload,
  Filter,
} from "lucide-react";
import { Curriculum, CurriculumStatus, CurriculumCreatePayload } from "@/types/catalog";

const statusColors: Record<CurriculumStatus, string> = {
  ACTIVE: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/25",
  DRAFT: "bg-amber-500/10 text-amber-400 border border-amber-500/25",
  ARCHIVED: "bg-zinc-500/10 text-zinc-400 border border-zinc-500/25",
};

const statusIcon: Record<CurriculumStatus, React.ElementType> = {
  ACTIVE: CheckCircle2,
  DRAFT: FileEdit,
  ARCHIVED: Archive,
};

interface ProgramOption {
  id: string;
  programId: string;
  name: string;
}

export default function CurriculaPage() {
  const { user } = useAuth();
  const orgId = user?.tenant?.organizationId || "";
  const qc = useQueryClient();
  const searchParams = useSearchParams();
  const router = useRouter();

  const [showCreate, setShowCreate] = useState(searchParams.get("create") === "true");
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterProgram, setFilterProgram] = useState<string>("");
  const [confirmAction, setConfirmAction] = useState<{
    type: "publish" | "archive" | "delete" | "clone";
    curriculumId: string;
    name: string;
  } | null>(null);

  // Create form state
  const [form, setForm] = useState<Partial<CurriculumCreatePayload>>({
    admissionBatch: "",
    description: "",
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  const { data: curricula = [], isLoading } = useQuery<Curriculum[]>({
    queryKey: ["curricula", orgId, filterStatus, filterProgram],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: "100" });
      if (filterStatus) params.set("status", filterStatus);
      if (filterProgram) params.set("programId", filterProgram);
      const res = await api.get<any>(`/organizations/${orgId}/catalog/curricula?${params}`);
      return Array.isArray(res) ? res : res?.data ?? res ?? [];
    },
    enabled: !!orgId,
  });

  const { data: programs = [] } = useQuery<ProgramOption[]>({
    queryKey: ["programs", orgId],
    queryFn: () => api.get<ProgramOption[]>(`/organizations/${orgId}/programs`),
    enabled: !!orgId,
  });

  const createMutation = useMutation({
    mutationFn: (payload: CurriculumCreatePayload) =>
      api.post(`/organizations/${orgId}/catalog/curricula`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["curricula", orgId] });
      setShowCreate(false);
      setForm({ admissionBatch: "", description: "" });
    },
  });

  const publishMutation = useMutation({
    mutationFn: (id: string) =>
      api.post(`/organizations/${orgId}/catalog/curricula/${id}/publish`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["curricula", orgId] });
      setConfirmAction(null);
    },
  });

  const archiveMutation = useMutation({
    mutationFn: (id: string) =>
      api.post(`/organizations/${orgId}/catalog/curricula/${id}/archive`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["curricula", orgId] });
      setConfirmAction(null);
    },
  });

  const cloneMutation = useMutation({
    mutationFn: (id: string) =>
      api.post<Curriculum>(`/organizations/${orgId}/catalog/curricula/${id}/clone`),
    onSuccess: (newCurr: any) => {
      qc.invalidateQueries({ queryKey: ["curricula", orgId] });
      setConfirmAction(null);
      if (newCurr?.curriculumId) {
        router.push(`/dashboard/catalog/curricula/${newCurr.curriculumId}`);
      }
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      api.delete(`/organizations/${orgId}/catalog/curricula/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["curricula", orgId] });
      setConfirmAction(null);
    },
  });

  const handleCreate = () => {
    const errors: Record<string, string> = {};
    if (!form.name?.trim()) errors.name = "Name is required.";
    if (!form.programId) errors.programId = "Program is required.";
    if (Object.keys(errors).length) {
      setFormErrors(errors);
      return;
    }
    createMutation.mutate({
      programId: form.programId!,
      name: form.name!,
      effectiveFrom: new Date().toISOString(),
      description: form.description,
      admissionBatch: form.admissionBatch,
    });
  };

  const confirmLabel: Record<string, string> = {
    publish: "Publish",
    archive: "Archive",
    delete: "Delete",
    clone: "Clone",
  };

  const handleConfirm = () => {
    if (!confirmAction) return;
    const { type, curriculumId } = confirmAction;
    if (type === "publish") publishMutation.mutate(curriculumId);
    if (type === "archive") archiveMutation.mutate(curriculumId);
    if (type === "clone") cloneMutation.mutate(curriculumId);
    if (type === "delete") deleteMutation.mutate(curriculumId);
  };

  const programNameMap = Object.fromEntries(
    programs.map((p) => [p.programId ?? p.id, p.name])
  );

  return (
    <div className="flex flex-col gap-6">
      {/* Top Bar */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          {/* Status filter */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="h-9 px-3 rounded-lg border border-border bg-background text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-violet-500"
          >
            <option value="">All Statuses</option>
            <option value="DRAFT">Draft</option>
            <option value="ACTIVE">Active</option>
            <option value="ARCHIVED">Archived</option>
          </select>
          {/* Program filter */}
          {programs.length > 0 && (
            <select
              value={filterProgram}
              onChange={(e) => setFilterProgram(e.target.value)}
              className="h-9 px-3 rounded-lg border border-border bg-background text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-violet-500"
            >
              <option value="">All Programs</option>
              {programs.map((p) => (
                <option key={p.programId ?? p.id} value={p.programId ?? p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          )}
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold transition-colors"
        >
          <PlusCircle className="h-4 w-4" />
          New Curriculum
        </button>
      </div>

      {/* Create Curriculum Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <Card glass className="w-full max-w-lg flex flex-col gap-6">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold">Create New Curriculum</h2>
              <button
                onClick={() => setShowCreate(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex flex-col gap-4">
              {/* Program */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Program *
                </label>
                <select
                  value={form.programId || ""}
                  onChange={(e) => setForm({ ...form, programId: e.target.value })}
                  className="h-10 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  <option value="">Select a program…</option>
                  {programs.map((p) => (
                    <option key={p.programId ?? p.id} value={p.programId ?? p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
                {formErrors.programId && (
                  <span className="text-2xs text-rose-400">{formErrors.programId}</span>
                )}
              </div>

              {/* Name */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Curriculum Name *
                </label>
                <input
                  type="text"
                  placeholder="e.g., B.Tech CSE 2024 Curriculum"
                  value={form.name || ""}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="h-10 px-3 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
                {formErrors.name && (
                  <span className="text-2xs text-rose-400">{formErrors.name}</span>
                )}
              </div>

              {/* Admission Batch */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Admission Batch
                </label>
                <input
                  type="text"
                  placeholder="e.g., 2024-28"
                  value={form.admissionBatch || ""}
                  onChange={(e) => setForm({ ...form, admissionBatch: e.target.value })}
                  className="h-10 px-3 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>

              {/* Description */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Description
                </label>
                <textarea
                  rows={3}
                  placeholder="Optional internal notes about this curriculum version…"
                  value={form.description || ""}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="px-3 py-2 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500 resize-none"
                />
              </div>
            </div>

            {createMutation.isError && (
              <p className="text-xs text-rose-400">
                {(createMutation.error as any)?.detail || "Failed to create curriculum."}
              </p>
            )}

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 rounded-lg border border-border text-xs font-semibold hover:bg-accent/10 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={createMutation.isPending}
                className="px-5 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-xs font-semibold transition-colors"
              >
                {createMutation.isPending ? "Creating…" : "Create Curriculum"}
              </button>
            </div>
          </Card>
        </div>
      )}

      {/* Confirm Action Modal */}
      {confirmAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <Card glass className="w-full max-w-md flex flex-col gap-5">
            <h2 className="text-base font-bold">
              {confirmLabel[confirmAction.type]} Curriculum?
            </h2>
            <p className="text-sm text-muted-foreground">
              {confirmAction.type === "publish" &&
                `Publishing "${confirmAction.name}" will make it ACTIVE. This cannot be undone without archiving first.`}
              {confirmAction.type === "archive" &&
                `Archiving "${confirmAction.name}" will mark it as read-only. Students on this version remain pinned.`}
              {confirmAction.type === "clone" &&
                `A new DRAFT version will be created from "${confirmAction.name}" with all subjects copied.`}
              {confirmAction.type === "delete" &&
                `Deleting "${confirmAction.name}" is permanent (soft delete). Only DRAFT curricula can be deleted.`}
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmAction(null)}
                className="px-4 py-2 rounded-lg border border-border text-xs font-semibold hover:bg-accent/10 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                disabled={
                  publishMutation.isPending ||
                  archiveMutation.isPending ||
                  cloneMutation.isPending ||
                  deleteMutation.isPending
                }
                className={`px-5 py-2 rounded-lg text-white text-xs font-semibold transition-colors disabled:opacity-50 ${
                  confirmAction.type === "delete"
                    ? "bg-rose-600 hover:bg-rose-500"
                    : confirmAction.type === "publish"
                    ? "bg-emerald-600 hover:bg-emerald-500"
                    : confirmAction.type === "clone"
                    ? "bg-violet-600 hover:bg-violet-500"
                    : "bg-zinc-600 hover:bg-zinc-500"
                }`}
              >
                {confirmLabel[confirmAction.type]}
              </button>
            </div>
          </Card>
        </div>
      )}

      {/* Curricula Table */}
      <Card glass className="overflow-hidden">
        {isLoading ? (
          <div className="p-6 space-y-3">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : curricula.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
            <BookText className="h-10 w-10 text-muted-foreground opacity-30" />
            <p className="text-sm font-semibold text-muted-foreground">No curricula found.</p>
            <p className="text-xs text-muted-foreground max-w-xs">
              Create your first curriculum to start building the academic catalog for a program.
            </p>
            <button
              onClick={() => setShowCreate(true)}
              className="mt-2 flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold transition-colors"
            >
              <PlusCircle className="h-4 w-4" />
              New Curriculum
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-accent/5">
                  <th className="px-4 py-3 text-left text-2xs font-bold text-muted-foreground uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left text-2xs font-bold text-muted-foreground uppercase tracking-wider">
                    Program
                  </th>
                  <th className="px-4 py-3 text-center text-2xs font-bold text-muted-foreground uppercase tracking-wider">
                    Version
                  </th>
                  <th className="px-4 py-3 text-center text-2xs font-bold text-muted-foreground uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-4 py-3 text-center text-2xs font-bold text-muted-foreground uppercase tracking-wider">
                    Credits
                  </th>
                  <th className="px-4 py-3 text-center text-2xs font-bold text-muted-foreground uppercase tracking-wider">
                    Batch
                  </th>
                  <th className="px-4 py-3 text-right text-2xs font-bold text-muted-foreground uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {curricula.map((c) => {
                  const Icon = statusIcon[c.status];
                  return (
                    <tr key={c.curriculumId} className="hover:bg-accent/5 transition-colors">
                      <td className="px-4 py-3.5">
                        <Link
                          href={`/dashboard/catalog/curricula/${c.curriculumId}`}
                          className="font-semibold hover:text-violet-400 transition-colors"
                        >
                          {c.name}
                        </Link>
                        {c.description && (
                          <p className="text-2xs text-muted-foreground mt-0.5 line-clamp-1">
                            {c.description}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3.5">
                        <span className="text-xs text-muted-foreground">
                          {programNameMap[c.programId] || c.programId}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-center">
                        <span className="text-xs font-bold tabular-nums">v{c.version}</span>
                      </td>
                      <td className="px-4 py-3.5 text-center">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-3xs font-bold uppercase tracking-wider ${
                            statusColors[c.status]
                          }`}
                        >
                          <Icon className="h-3 w-3" />
                          {c.status}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-center">
                        <span className="text-xs font-semibold tabular-nums">
                          {c.totalCredits?.toFixed(1) || "—"}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-center">
                        <span className="text-xs text-muted-foreground">
                          {c.admissionBatch || "—"}
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center justify-end gap-1.5">
                          <Link
                            href={`/dashboard/catalog/curricula/${c.curriculumId}`}
                            className="h-7 w-7 flex items-center justify-center rounded-md border border-border hover:bg-accent/20 text-muted-foreground hover:text-foreground transition-colors"
                            title="View"
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </Link>
                          <button
                            onClick={() =>
                              setConfirmAction({
                                type: "clone",
                                curriculumId: c.curriculumId,
                                name: c.name,
                              })
                            }
                            className="h-7 w-7 flex items-center justify-center rounded-md border border-border hover:bg-violet-500/10 text-muted-foreground hover:text-violet-400 transition-colors"
                            title="Clone"
                          >
                            <Copy className="h-3.5 w-3.5" />
                          </button>
                          {c.status === "DRAFT" && (
                            <>
                              <button
                                onClick={() =>
                                  setConfirmAction({
                                    type: "publish",
                                    curriculumId: c.curriculumId,
                                    name: c.name,
                                  })
                                }
                                className="h-7 w-7 flex items-center justify-center rounded-md border border-border hover:bg-emerald-500/10 text-muted-foreground hover:text-emerald-400 transition-colors"
                                title="Publish"
                              >
                                <Upload className="h-3.5 w-3.5" />
                              </button>
                              <button
                                onClick={() =>
                                  setConfirmAction({
                                    type: "delete",
                                    curriculumId: c.curriculumId,
                                    name: c.name,
                                  })
                                }
                                className="h-7 w-7 flex items-center justify-center rounded-md border border-border hover:bg-rose-500/10 text-muted-foreground hover:text-rose-400 transition-colors"
                                title="Delete"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </>
                          )}
                          {c.status === "ACTIVE" && (
                            <button
                              onClick={() =>
                                setConfirmAction({
                                  type: "archive",
                                  curriculumId: c.curriculumId,
                                  name: c.name,
                                })
                              }
                              className="h-7 w-7 flex items-center justify-center rounded-md border border-border hover:bg-zinc-500/10 text-muted-foreground hover:text-zinc-400 transition-colors"
                              title="Archive"
                            >
                              <Archive className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
