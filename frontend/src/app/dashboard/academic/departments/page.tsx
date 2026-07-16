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
  Building2,
  RefreshCw,
  Search,
} from "lucide-react";
import { Department } from "@/types/academic";

const departmentSchema = z.object({
  name: z.string().min(3, "Name must be at least 3 characters"),
  code: z.string().min(2, "Code must be at least 2 characters (e.g. CSE)"),
  hod: z.string().optional(),
  description: z.string().optional(),
  status: z.enum(["ACTIVE", "INACTIVE"]),
});

type FormValues = z.infer<typeof departmentSchema>;

export default function DepartmentsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const orgId = user?.tenant?.organizationId || "";
  const { success, error: toastError } = useToast();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingDept, setEditingDept] = useState<Department | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Fetch list
  const { data: depts = [], isLoading, refetch } = useQuery<Department[]>({
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
    resolver: zodResolver(departmentSchema),
    defaultValues: {
      status: "ACTIVE",
    },
  });

  // Mutate create
  const createMutation = useMutation({
    mutationFn: (data: FormValues) => api.post<Department>(`/organizations/${orgId}/departments`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["departments", orgId] });
      success("Department Created", "The department has been registered.");
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
      api.patch<Department>(`/organizations/${orgId}/departments/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["departments", orgId] });
      success("Department Updated", "Details updated successfully.");
      setModalOpen(false);
      setEditingDept(null);
      reset();
    },
    onError: (err: any) => {
      toastError("Failed to Update", err?.detail || "An error occurred.");
    },
  });

  // Mutate delete
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/organizations/${orgId}/departments/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["departments", orgId] });
      success("Deleted", "Department soft-deleted successfully.");
    },
    onError: (err: any) => {
      toastError("Failed to Delete", err?.detail || "An error occurred.");
    },
  });

  // Bulk delete
  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) =>
      api.post(`/organizations/${orgId}/departments/bulk`, { ids }, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["departments", orgId] });
      success("Bulk Deleted", "Selected departments removed.");
      setSelectedIds([]);
    },
    onError: (err: any) => {
      toastError("Bulk Delete Failed", err?.detail || "An error occurred.");
    },
  });

  const onSubmit = (data: FormValues) => {
    if (editingDept) {
      updateMutation.mutate({ id: editingDept.departmentId, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleEditClick = (dept: Department) => {
    setEditingDept(dept);
    setValue("name", dept.name);
    setValue("code", dept.code);
    setValue("hod", dept.hod || "");
    setValue("description", dept.description || "");
    setValue("status", dept.status);
    setModalOpen(true);
  };

  const handleDeleteClick = (id: string) => {
    if (confirm("Are you sure you want to delete this department?")) {
      deleteMutation.mutate(id);
    }
  };

  const handleBulkDelete = () => {
    if (confirm(`Are you sure you want to delete the ${selectedIds.length} selected departments?`)) {
      bulkDeleteMutation.mutate(selectedIds);
    }
  };

  const toggleSelectRow = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredDepts.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredDepts.map((d) => d.departmentId));
    }
  };

  // Filter local lists by search query
  const filteredDepts = depts.filter(
    (d) =>
      d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const canWrite =
    user?.role?.permissions.includes("*") || user?.role?.permissions.includes("department:write");

  return (
    <div className="flex flex-col gap-6">
      {/* Search and Action Toolbar */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-stretch md:items-center">
        {/* Search */}
        <div className="relative max-w-sm w-full">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search departments..."
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
                setEditingDept(null);
                reset({ name: "", code: "", hod: "", description: "", status: "ACTIVE" });
                setModalOpen(true);
              }}
              size="sm"
              className="flex items-center gap-1.5"
            >
              <Plus className="h-4 w-4" /> Add Department
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
          ) : filteredDepts.length === 0 ? (
            <EmptyState
              title="No Departments Found"
              description="Register academic divisions under this institution."
              actionText={canWrite ? "Register Department" : undefined}
              onAction={
                canWrite
                  ? () => {
                      setEditingDept(null);
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
                          checked={selectedIds.length === filteredDepts.length && filteredDepts.length > 0}
                          onChange={toggleSelectAll}
                          className="rounded border-input text-primary focus:ring-primary cursor-pointer h-4 w-4"
                        />
                      </th>
                    )}
                    <th className="py-3 px-4">Dept Name</th>
                    <th className="py-3 px-4">Code</th>
                    <th className="py-3 px-4">Head of Dept (HoD)</th>
                    <th className="py-3 px-4">Status</th>
                    {canWrite && <th className="py-3 px-4 text-right">Actions</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredDepts.map((d) => (
                    <tr key={d.departmentId} className="hover:bg-accent/5 transition-colors">
                      {canWrite && (
                        <td className="py-3.5 px-4">
                          <input
                            type="checkbox"
                            checked={selectedIds.includes(d.departmentId)}
                            onChange={() => toggleSelectRow(d.departmentId)}
                            className="rounded border-input text-primary focus:ring-primary cursor-pointer h-4 w-4"
                          />
                        </td>
                      )}
                      <td className="py-3.5 px-4 font-semibold text-foreground flex items-center gap-2">
                        <div className="h-7 w-7 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
                          <Building2 className="h-4 w-4" />
                        </div>
                        {d.name}
                      </td>
                      <td className="py-3.5 px-4 font-mono font-bold text-xs">{d.code}</td>
                      <td className="py-3.5 px-4 text-muted-foreground">{d.hod || "Not Assigned"}</td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-3xs font-bold uppercase tracking-wider border ${
                            d.status === "ACTIVE"
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                              : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                          }`}
                        >
                          {d.status}
                        </span>
                      </td>
                      {canWrite && (
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleEditClick(d)}
                              className="h-8 w-8 p-0 cursor-pointer border-border text-foreground hover:bg-accent/15"
                            >
                              <Edit2 className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              variant="danger"
                              size="sm"
                              disabled={deleteMutation.isPending}
                              onClick={() => handleDeleteClick(d.departmentId)}
                              className="h-8 w-8 p-0 cursor-pointer"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Creation/Edit Modal */}
      <Dialog
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingDept ? "Edit Department" : "Add Department"}
        description="Configure academic division identifiers and HoD details."
      >
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Input
            type="text"
            label="Department Name"
            placeholder="Computer Science & Engineering"
            error={errors.name?.message}
            {...register("name")}
          />

          <Input
            type="text"
            label="Department Code"
            placeholder="CSE"
            error={errors.code?.message}
            {...register("code")}
          />

          <Input
            type="text"
            label="Head of Department (HoD)"
            placeholder="Dr. John McCarthy"
            error={errors.hod?.message}
            {...register("hod")}
          />

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Department Status
            </label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              {...register("status")}
            >
              <option value="ACTIVE">ACTIVE</option>
              <option value="INACTIVE">INACTIVE</option>
            </select>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createMutation.isPending || updateMutation.isPending}>
              {editingDept ? "Save Changes" : "Create Department"}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
