"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useToast } from "@/components/ui/toast";
import {
  Plus,
  Edit2,
  Trash2,
  GitBranch,
  RefreshCw,
  Search,
} from "lucide-react";
import { Branch, Department } from "@/types/academic";

const branchSchema = z.object({
  name: z.string().min(3, "Name must be at least 3 characters"),
  code: z.string().min(2, "Code must be at least 2 characters (e.g. AIML)"),
  departmentId: z.string().min(1, "Department is required"),
});

type FormValues = z.infer<typeof branchSchema>;

export default function BranchesPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const orgId = user?.tenant?.organizationId || "";
  const { success, error: toastError } = useToast();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingBranch, setEditingBranch] = useState<Branch | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Fetch list of branches
  const { data: branches = [], isLoading, refetch } = useQuery<Branch[]>({
    queryKey: ["branches", orgId],
    queryFn: () => api.get<Branch[]>(`/organizations/${orgId}/branches`),
    enabled: !!orgId,
  });

  // Fetch list of departments for the selector
  const { data: depts = [] } = useQuery<Department[]>({
    queryKey: ["departments", orgId],
    queryFn: () => api.get<Department[]>(`/organizations/${orgId}/departments`),
    enabled: !!orgId,
  });

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(branchSchema),
  });

  // Mutate create
  const createMutation = useMutation({
    mutationFn: (data: FormValues) => api.post<Branch>(`/organizations/${orgId}/branches`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["branches", orgId] });
      success("Branch Created", "The branch specialization has been registered.");
      setModalOpen(false);
      reset();
    },
    onError: (err: any) => {
      toastError("Failed to Create", err?.detail || "An error occurred.");
    },
  });

  // Mutate update
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<FormValues> }) =>
      api.patch<Branch>(`/organizations/${orgId}/branches/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["branches", orgId] });
      success("Branch Updated", "Details updated successfully.");
      setModalOpen(false);
      setEditingBranch(null);
      reset();
    },
    onError: (err: any) => {
      toastError("Failed to Update", err?.detail || "An error occurred.");
    },
  });

  // Mutate delete
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/organizations/${orgId}/branches/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["branches", orgId] });
      success("Deleted", "Branch soft-deleted successfully.");
    },
    onError: (err: any) => {
      toastError("Failed to Delete", err?.detail || "An error occurred.");
    },
  });

  // Bulk delete
  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) =>
      api.post(`/organizations/${orgId}/branches/bulk`, { ids }, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["branches", orgId] });
      success("Bulk Deleted", "Selected branches removed.");
      setSelectedIds([]);
    },
    onError: (err: any) => {
      toastError("Bulk Delete Failed", err?.detail || "An error occurred.");
    },
  });

  const onSubmit = (data: FormValues) => {
    if (editingBranch) {
      updateMutation.mutate({ id: editingBranch.branchId, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleEditClick = (brn: Branch) => {
    setEditingBranch(brn);
    setValue("name", brn.name);
    setValue("code", brn.code);
    setValue("departmentId", brn.departmentId);
    setModalOpen(true);
  };

  const handleDeleteClick = (id: string) => {
    if (confirm("Are you sure you want to delete this branch specialization?")) {
      deleteMutation.mutate(id);
    }
  };

  const handleBulkDelete = () => {
    if (confirm(`Are you sure you want to delete the ${selectedIds.length} selected branches?`)) {
      bulkDeleteMutation.mutate(selectedIds);
    }
  };

  const toggleSelectRow = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredBranches.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredBranches.map((b) => b.branchId));
    }
  };

  // Filter local lists by search query
  const filteredBranches = branches.filter(
    (b) =>
      b.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const canWrite =
    user?.role?.permissions.includes("*") || user?.role?.permissions.includes("academic:write");

  return (
    <div className="flex flex-col gap-6">
      {/* Search and Action Toolbar */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-stretch md:items-center">
        {/* Search */}
        <div className="relative max-w-sm w-full">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search branches..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-9 rounded-lg bg-accent/10 border border-input pl-10 pr-4 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary focus-visible:ring-offset-0 placeholder:text-muted-foreground transition-all duration-200"
          />
        </div>

        {/* Buttons */}
        <div className="flex items-center gap-3">
          {selectedIds.length > 0 && canWrite && (
            <Button variant="danger" size="sm" onClick={handleBulkDelete}>
              <Trash2 className="h-4 w-4 mr-2" /> Bulk Delete ({selectedIds.length})
            </Button>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            className="border-border text-foreground hover:bg-accent/10"
          >
            <RefreshCw className="h-4 w-4 mr-2" /> Refresh
          </Button>

          {canWrite && (
            <Button
              onClick={() => {
                setEditingBranch(null);
                reset({ name: "", code: "", departmentId: "" });
                setModalOpen(true);
              }}
              size="sm"
              className="flex items-center gap-1.5"
            >
              <Plus className="h-4 w-4" /> Create Branch
            </Button>
          )}
        </div>
      </div>

      {/* Main List Grid */}
      <Card glass>
        <CardContent className="pt-6">
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : filteredBranches.length === 0 ? (
            <EmptyState
              title="No Branches Found"
              description="Configure academic branch specializations under active departments."
              actionText={canWrite ? "Create Branch" : undefined}
              onAction={
                canWrite
                  ? () => {
                      setEditingBranch(null);
                      setModalOpen(true);
                    }
                  : undefined
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left border-collapse">
                <thead>
                  <tr className="border-b border-border text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    {canWrite && (
                      <th className="py-3 px-4 w-12">
                        <input
                          type="checkbox"
                          checked={selectedIds.length === filteredBranches.length && filteredBranches.length > 0}
                          onChange={toggleSelectAll}
                          className="rounded border-input text-primary focus:ring-primary cursor-pointer h-4 w-4"
                        />
                      </th>
                    )}
                    <th className="py-3 px-4">Branch Specialization Title</th>
                    <th className="py-3 px-4">Affiliated Dept</th>
                    <th className="py-3 px-4">Branch Code</th>
                    {canWrite && <th className="py-3 px-4 text-right">Actions</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredBranches.map((b) => {
                    const dept = depts.find((d) => d.id === b.departmentId);
                    return (
                      <tr key={b.branchId} className="hover:bg-accent/5 transition-colors">
                        {canWrite && (
                          <td className="py-3.5 px-4">
                            <input
                              type="checkbox"
                              checked={selectedIds.includes(b.branchId)}
                              onChange={() => toggleSelectRow(b.branchId)}
                              className="rounded border-input text-primary focus:ring-primary cursor-pointer h-4 w-4"
                            />
                          </td>
                        )}
                        <td className="py-3.5 px-4 font-semibold text-foreground flex items-center gap-2">
                          <div className="h-7 w-7 rounded-lg bg-pink-500/10 text-pink-400 flex items-center justify-center">
                            <GitBranch className="h-4 w-4" />
                          </div>
                          {b.name}
                        </td>
                        <td className="py-3.5 px-4 text-muted-foreground">{dept?.name || "Loading..."}</td>
                        <td className="py-3.5 px-4 font-mono font-bold text-xs">{b.code}</td>
                        {canWrite && (
                          <td className="py-3.5 px-4 text-right">
                            <div className="flex justify-end gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleEditClick(b)}
                                className="h-8 w-8 p-0 cursor-pointer border-border text-foreground hover:bg-accent/15"
                              >
                                <Edit2 className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                variant="danger"
                                size="sm"
                                disabled={deleteMutation.isPending}
                                onClick={() => handleDeleteClick(b.branchId)}
                                className="h-8 w-8 p-0 cursor-pointer"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Creation Modal */}
      <Dialog
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingBranch ? "Edit Branch" : "Create Branch"}
        description="Configure academic branch specializations, unique codes, and associated departments."
      >
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Input
            type="text"
            label="Branch Title"
            placeholder="AI & Machine Learning"
            error={errors.name?.message}
            {...register("name")}
          />

          <Input
            type="text"
            label="Branch Code"
            placeholder="AIML"
            error={errors.code?.message}
            {...register("code")}
          />

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Affiliated Department
            </label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              {...register("departmentId")}
            >
              <option value="">Select affiliated department...</option>
              {depts.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.code})
                </option>
              ))}
            </select>
            {errors.departmentId && (
              <span className="text-xs text-rose-500 font-medium">{errors.departmentId.message}</span>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createMutation.isPending || updateMutation.isPending}>
              {editingBranch ? "Save Changes" : "Create Branch"}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
