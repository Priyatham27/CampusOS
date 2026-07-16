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
  BookOpen,
  RefreshCw,
  Search,
} from "lucide-react";
import { Program, Department } from "@/types/academic";

const programSchema = z.object({
  name: z.string().min(3, "Name must be at least 3 characters"),
  duration: z.number().min(1, "Duration must be at least 1 year").max(10, "Duration must be less than 10 years"),
  level: z.enum(["UNDERGRADUATE", "POSTGRADUATE", "DOCTORAL", "DIPLOMA"]),
  departmentId: z.string().min(1, "Department is required"),
});

type FormValues = z.infer<typeof programSchema>;

export default function ProgramsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const orgId = user?.tenant?.organizationId || "";
  const { success, error: toastError } = useToast();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingProgram, setEditingProgram] = useState<Program | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Fetch list of programs
  const { data: programs = [], isLoading, refetch } = useQuery<Program[]>({
    queryKey: ["programs", orgId],
    queryFn: () => api.get<Program[]>(`/organizations/${orgId}/programs`),
    enabled: !!orgId,
  });

  // Fetch list of departments for the selection dropdown
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
    resolver: zodResolver(programSchema),
    defaultValues: {
      level: "UNDERGRADUATE",
    },
  });

  // Mutate create
  const createMutation = useMutation({
    mutationFn: (data: FormValues) => api.post<Program>(`/organizations/${orgId}/programs`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["programs", orgId] });
      success("Program Created", "The academic program has been registered.");
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
      api.patch<Program>(`/organizations/${orgId}/programs/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["programs", orgId] });
      success("Program Updated", "Details updated successfully.");
      setModalOpen(false);
      setEditingProgram(null);
      reset();
    },
    onError: (err: any) => {
      toastError("Failed to Update", err?.detail || "An error occurred.");
    },
  });

  // Mutate delete
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/organizations/${orgId}/programs/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["programs", orgId] });
      success("Deleted", "Program soft-deleted successfully.");
    },
    onError: (err: any) => {
      toastError("Failed to Delete", err?.detail || "An error occurred.");
    },
  });

  // Bulk delete
  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) =>
      api.post(`/organizations/${orgId}/programs/bulk`, { ids }, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["programs", orgId] });
      success("Bulk Deleted", "Selected programs removed.");
      setSelectedIds([]);
    },
    onError: (err: any) => {
      toastError("Bulk Delete Failed", err?.detail || "An error occurred.");
    },
  });

  const onSubmit = (data: FormValues) => {
    if (editingProgram) {
      updateMutation.mutate({ id: editingProgram.programId, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleEditClick = (prg: Program) => {
    setEditingProgram(prg);
    setValue("name", prg.name);
    setValue("duration", prg.duration);
    setValue("level", prg.level);
    setValue("departmentId", prg.departmentId);
    setModalOpen(true);
  };

  const handleDeleteClick = (id: string) => {
    if (confirm("Are you sure you want to delete this program?")) {
      deleteMutation.mutate(id);
    }
  };

  const handleBulkDelete = () => {
    if (confirm(`Are you sure you want to delete the ${selectedIds.length} selected programs?`)) {
      bulkDeleteMutation.mutate(selectedIds);
    }
  };

  const toggleSelectRow = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredPrograms.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredPrograms.map((p) => p.programId));
    }
  };

  // Filter local lists by search query
  const filteredPrograms = programs.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
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
            placeholder="Search programs..."
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
                setEditingProgram(null);
                reset({ name: "", duration: 4, level: "UNDERGRADUATE", departmentId: "" });
                setModalOpen(true);
              }}
              size="sm"
              className="flex items-center gap-1.5"
            >
              <Plus className="h-4 w-4" /> Create Program
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
          ) : filteredPrograms.length === 0 ? (
            <EmptyState
              title="No Programs Found"
              description="Configure academic programs (degree levels) for the institution."
              actionText={canWrite ? "Create Program" : undefined}
              onAction={
                canWrite
                  ? () => {
                      setEditingProgram(null);
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
                          checked={selectedIds.length === filteredPrograms.length && filteredPrograms.length > 0}
                          onChange={toggleSelectAll}
                          className="rounded border-input text-primary focus:ring-primary cursor-pointer h-4 w-4"
                        />
                      </th>
                    )}
                    <th className="py-3 px-4">Program Title</th>
                    <th className="py-3 px-4">Affiliated Dept</th>
                    <th className="py-3 px-4">Academic Level</th>
                    <th className="py-3 px-4">Duration (Years)</th>
                    {canWrite && <th className="py-3 px-4 text-right">Actions</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredPrograms.map((p) => {
                    const dept = depts.find((d) => d.id === p.departmentId);
                    return (
                      <tr key={p.programId} className="hover:bg-accent/5 transition-colors">
                        {canWrite && (
                          <td className="py-3.5 px-4">
                            <input
                              type="checkbox"
                              checked={selectedIds.includes(p.programId)}
                              onChange={() => toggleSelectRow(p.programId)}
                              className="rounded border-input text-primary focus:ring-primary cursor-pointer h-4 w-4"
                            />
                          </td>
                        )}
                        <td className="py-3.5 px-4 font-semibold text-foreground flex items-center gap-2">
                          <div className="h-7 w-7 rounded-lg bg-sky-500/10 text-sky-400 flex items-center justify-center">
                            <BookOpen className="h-4 w-4" />
                          </div>
                          {p.name}
                        </td>
                        <td className="py-3.5 px-4 text-muted-foreground">{dept?.name || "Loading..."}</td>
                        <td className="py-3.5 px-4">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-3xs font-semibold bg-accent/20 border border-border text-foreground">
                            {p.level}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 font-semibold">{p.duration} Years</td>
                        {canWrite && (
                          <td className="py-3.5 px-4 text-right">
                            <div className="flex justify-end gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleEditClick(p)}
                                className="h-8 w-8 p-0 cursor-pointer border-border text-foreground hover:bg-accent/15"
                              >
                                <Edit2 className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                variant="danger"
                                size="sm"
                                disabled={deleteMutation.isPending}
                                onClick={() => handleDeleteClick(p.programId)}
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
        title={editingProgram ? "Edit Program" : "Create Program"}
        description="Configure academic programs, level categories, and associated departments."
      >
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Input
            type="text"
            label="Program Title"
            placeholder="Bachelor of Technology"
            error={errors.name?.message}
            {...register("name")}
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              type="number"
              label="Duration (Years)"
              placeholder="4"
              error={errors.duration?.message}
              {...register("duration", { valueAsNumber: true })}
            />

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Academic Level
              </label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                {...register("level")}
              >
                <option value="UNDERGRADUATE">UNDERGRADUATE</option>
                <option value="POSTGRADUATE">POSTGRADUATE</option>
                <option value="DOCTORAL">DOCTORAL</option>
                <option value="DIPLOMA">DIPLOMA</option>
              </select>
            </div>
          </div>

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
              {editingProgram ? "Save Changes" : "Create Program"}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
