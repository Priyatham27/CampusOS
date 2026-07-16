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
  Grid,
  RefreshCw,
  Search,
} from "lucide-react";
import { Section, Branch, Semester } from "@/types/academic";

const sectionSchema = z.object({
  name: z.string().min(1, "Section Name must be at least 1 character (e.g. A)"),
  strength: z.number().min(1, "Class strength must be at least 1").max(500, "Must be less than 500"),
  branchId: z.string().min(1, "Branch Specialization is required"),
  semesterId: z.string().min(1, "Semester is required"),
});

type FormValues = z.infer<typeof sectionSchema>;

export default function SectionsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const orgId = user?.tenant?.organizationId || "";
  const { success, error: toastError } = useToast();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingSection, setEditingSection] = useState<Section | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Fetch list of sections
  const { data: sections = [], isLoading, refetch } = useQuery<Section[]>({
    queryKey: ["sections", orgId],
    queryFn: () => api.get<Section[]>(`/organizations/${orgId}/sections`),
    enabled: !!orgId,
  });

  // Fetch list of branches
  const { data: branches = [] } = useQuery<Branch[]>({
    queryKey: ["branches", orgId],
    queryFn: () => api.get<Branch[]>(`/organizations/${orgId}/branches`),
    enabled: !!orgId,
  });

  // Fetch list of semesters
  const { data: semesters = [] } = useQuery<Semester[]>({
    queryKey: ["semesters", orgId],
    queryFn: () => api.get<Semester[]>(`/organizations/${orgId}/semesters`),
    enabled: !!orgId,
  });

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(sectionSchema),
  });

  // Mutate create
  const createMutation = useMutation({
    mutationFn: (data: FormValues) => api.post<Section>(`/organizations/${orgId}/sections`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sections", orgId] });
      success("Section Created", "The class section has been registered.");
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
      api.patch<Section>(`/organizations/${orgId}/sections/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sections", orgId] });
      success("Section Updated", "Details updated successfully.");
      setModalOpen(false);
      setEditingSection(null);
      reset();
    },
    onError: (err: any) => {
      toastError("Failed to Update", err?.detail || "An error occurred.");
    },
  });

  // Mutate delete
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/organizations/${orgId}/sections/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sections", orgId] });
      success("Deleted", "Section soft-deleted successfully.");
    },
    onError: (err: any) => {
      toastError("Failed to Delete", err?.detail || "An error occurred.");
    },
  });

  // Bulk delete
  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) =>
      api.post(`/organizations/${orgId}/sections/bulk`, { ids }, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sections", orgId] });
      success("Bulk Deleted", "Selected sections removed.");
      setSelectedIds([]);
    },
    onError: (err: any) => {
      toastError("Bulk Delete Failed", err?.detail || "An error occurred.");
    },
  });

  const onSubmit = (data: FormValues) => {
    if (editingSection) {
      updateMutation.mutate({ id: editingSection.sectionId, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleEditClick = (sec: Section) => {
    setEditingSection(sec);
    setValue("name", sec.name);
    setValue("strength", sec.strength);
    setValue("branchId", sec.branchId);
    setValue("semesterId", sec.semesterId);
    setModalOpen(true);
  };

  const handleDeleteClick = (id: string) => {
    if (confirm("Are you sure you want to delete this section?")) {
      deleteMutation.mutate(id);
    }
  };

  const handleBulkDelete = () => {
    if (confirm(`Are you sure you want to delete the ${selectedIds.length} selected sections?`)) {
      bulkDeleteMutation.mutate(selectedIds);
    }
  };

  const toggleSelectRow = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredSections.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredSections.map((s) => s.sectionId));
    }
  };

  // Filter local lists by search query
  const filteredSections = sections.filter((s) =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase())
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
            placeholder="Search sections..."
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
                setEditingSection(null);
                reset({ name: "", strength: 60, branchId: "", semesterId: "" });
                setModalOpen(true);
              }}
              size="sm"
              className="flex items-center gap-1.5"
            >
              <Plus className="h-4 w-4" /> Create Section
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
          ) : filteredSections.length === 0 ? (
            <EmptyState
              title="No Sections Found"
              description="Configure class sections (batches) under active branches and semesters."
              actionText={canWrite ? "Create Section" : undefined}
              onAction={
                canWrite
                  ? () => {
                      setEditingSection(null);
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
                          checked={selectedIds.length === filteredSections.length && filteredSections.length > 0}
                          onChange={toggleSelectAll}
                          className="rounded border-input text-primary focus:ring-primary cursor-pointer h-4 w-4"
                        />
                      </th>
                    )}
                    <th className="py-3 px-4">Section Name</th>
                    <th className="py-3 px-4">Branch Affiliate</th>
                    <th className="py-3 px-4">Active Semester</th>
                    <th className="py-3 px-4">Class Strength Capacity</th>
                    {canWrite && <th className="py-3 px-4 text-right">Actions</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredSections.map((s) => {
                    const branch = branches.find((b) => b.id === s.branchId);
                    const semester = semesters.find((sem) => sem.id === s.semesterId);
                    return (
                      <tr key={s.sectionId} className="hover:bg-accent/5 transition-colors">
                        {canWrite && (
                          <td className="py-3.5 px-4">
                            <input
                              type="checkbox"
                              checked={selectedIds.includes(s.sectionId)}
                              onChange={() => toggleSelectRow(s.sectionId)}
                              className="rounded border-input text-primary focus:ring-primary cursor-pointer h-4 w-4"
                            />
                          </td>
                        )}
                        <td className="py-3.5 px-4 font-semibold text-foreground flex items-center gap-2">
                          <div className="h-7 w-7 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                            <Grid className="h-4 w-4" />
                          </div>
                          Section {s.name}
                        </td>
                        <td className="py-3.5 px-4 text-muted-foreground">{branch?.name || "Loading..."}</td>
                        <td className="py-3.5 px-4 text-muted-foreground">{semester?.name || "Loading..."}</td>
                        <td className="py-3.5 px-4 font-semibold">{s.strength} Seats</td>
                        {canWrite && (
                          <td className="py-3.5 px-4 text-right">
                            <div className="flex justify-end gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleEditClick(s)}
                                className="h-8 w-8 p-0 cursor-pointer border-border text-foreground hover:bg-accent/15"
                              >
                                <Edit2 className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                variant="danger"
                                size="sm"
                                disabled={deleteMutation.isPending}
                                onClick={() => handleDeleteClick(s.sectionId)}
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
        title={editingSection ? "Edit Section" : "Create Section"}
        description="Configure class sections (batches), classroom capacity, and linked specializations."
      >
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Input
            type="text"
            label="Section Name"
            placeholder="A"
            error={errors.name?.message}
            {...register("name")}
          />

          <Input
            type="number"
            label="Class Capacity strength"
            placeholder="60"
            error={errors.strength?.message}
            {...register("strength", { valueAsNumber: true })}
          />

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Branch Specialization Affiliate
            </label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              {...register("branchId")}
            >
              <option value="">Select branch specialization...</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name} ({b.code})
                </option>
              ))}
            </select>
            {errors.branchId && (
              <span className="text-xs text-rose-500 font-medium">{errors.branchId.message}</span>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Academic Semester
            </label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              {...register("semesterId")}
            >
              <option value="">Select target class semester...</option>
              {semesters.map((sem) => (
                <option key={sem.id} value={sem.id}>
                  {sem.name} (Seq #{sem.number})
                </option>
              ))}
            </select>
            {errors.semesterId && (
              <span className="text-xs text-rose-500 font-medium">{errors.semesterId.message}</span>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createMutation.isPending || updateMutation.isPending}>
              {editingSection ? "Save Changes" : "Create Section"}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
