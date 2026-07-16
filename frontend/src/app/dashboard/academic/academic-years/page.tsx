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
  Calendar,
  CheckCircle,
  AlertCircle,
  FileDown,
  RefreshCw,
  Search,
} from "lucide-react";
import { AcademicYear } from "@/types/academic";

const academicYearSchema = z.object({
  name: z.string().min(4, "Name must be at least 4 characters (e.g. 2026-2027)"),
  startDate: z.string().min(1, "Start Date is required"),
  endDate: z.string().min(1, "End Date is required"),
  current: z.boolean(),
});

type FormValues = z.infer<typeof academicYearSchema>;

export default function AcademicYearsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const orgId = user?.tenant?.organizationId || "";
  const { success, error: toastError } = useToast();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingYear, setEditingYear] = useState<AcademicYear | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Fetch list
  const { data: years = [], isLoading, refetch } = useQuery<AcademicYear[]>({
    queryKey: ["academic_years", orgId],
    queryFn: () => api.get<AcademicYear[]>(`/organizations/${orgId}/academic-years`),
    enabled: !!orgId,
  });

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(academicYearSchema),
    defaultValues: {
      current: false,
    },
  });

  // Mutate create
  const createMutation = useMutation({
    mutationFn: (data: FormValues) => {
      // API expects ISO dates
      const payload = {
        ...data,
        startDate: new Date(data.startDate).toISOString(),
        endDate: new Date(data.endDate).toISOString(),
      };
      return api.post<AcademicYear>(`/organizations/${orgId}/academic-years`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academic_years", orgId] });
      success("Academic Year Created", "The academic year has been added.");
      setModalOpen(false);
      reset();
    },
    onError: (err: any) => {
      toastError("Failed to Create", err?.detail || "An error occurred.");
    },
  });

  // Mutate update
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<FormValues> }) => {
      const payload: any = { ...data };
      if (data.startDate) payload.startDate = new Date(data.startDate).toISOString();
      if (data.endDate) payload.endDate = new Date(data.endDate).toISOString();
      return api.patch<AcademicYear>(`/organizations/${orgId}/academic-years/${id}`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academic_years", orgId] });
      success("Academic Year Updated", "Branding details updated successfully.");
      setModalOpen(false);
      setEditingYear(null);
      reset();
    },
    onError: (err: any) => {
      toastError("Failed to Update", err?.detail || "An error occurred.");
    },
  });

  // Mutate delete
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/organizations/${orgId}/academic-years/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academic_years", orgId] });
      success("Deleted", "Academic year soft-deleted successfully.");
    },
    onError: (err: any) => {
      toastError("Failed to Delete", err?.detail || "An error occurred.");
    },
  });

  // Bulk delete
  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) =>
      api.post(`/organizations/${orgId}/academic-years/bulk`, { ids }, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academic_years", orgId] });
      success("Bulk Deleted", "Selected academic years removed.");
      setSelectedIds([]);
    },
    onError: (err: any) => {
      toastError("Bulk Delete Failed", err?.detail || "An error occurred.");
    },
  });

  const onSubmit = (data: FormValues) => {
    if (editingYear) {
      updateMutation.mutate({ id: editingYear.academicYearId, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleEditClick = (year: AcademicYear) => {
    setEditingYear(year);
    // Convert ISO string back to YYYY-MM-DD for standard html date picker input value!
    const formatDate = (iso: string) => new Date(iso).toISOString().split("T")[0];
    setValue("name", year.name);
    setValue("startDate", formatDate(year.startDate));
    setValue("endDate", formatDate(year.endDate));
    setValue("current", year.current);
    setModalOpen(true);
  };

  const handleDeleteClick = (id: string) => {
    if (confirm("Are you sure you want to delete this academic year?")) {
      deleteMutation.mutate(id);
    }
  };

  const handleBulkDelete = () => {
    if (confirm(`Are you sure you want to delete the ${selectedIds.length} selected items?`)) {
      bulkDeleteMutation.mutate(selectedIds);
    }
  };

  const toggleSelectRow = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredYears.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredYears.map((y) => y.academicYearId));
    }
  };

  // Filter local lists by search query
  const filteredYears = years.filter((y) =>
    y.name.toLowerCase().includes(searchQuery.toLowerCase())
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
            placeholder="Search academic years..."
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
            <RefreshCw className="h-4 w-4 mr-2" /> RefreshData
          </Button>

          {canWrite && (
            <Button
              onClick={() => {
                setEditingYear(null);
                reset({ current: false, name: "", startDate: "", endDate: "" });
                setModalOpen(true);
              }}
              size="sm"
              className="flex items-center gap-1.5"
            >
              <Plus className="h-4 w-4" /> Create Year
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
          ) : filteredYears.length === 0 ? (
            <EmptyState
              title="No Academic Years Found"
              description="Configure your first academic calendar block or check search parameters."
              actionText={canWrite ? "Create Academic Year" : undefined}
              onAction={
                canWrite
                  ? () => {
                      setEditingYear(null);
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
                          checked={selectedIds.length === filteredYears.length && filteredYears.length > 0}
                          onChange={toggleSelectAll}
                          className="rounded border-input text-primary focus:ring-primary cursor-pointer h-4 w-4"
                        />
                      </th>
                    )}
                    <th className="py-3 px-4">Academic Session Name</th>
                    <th className="py-3 px-4">Start Boundary</th>
                    <th className="py-3 px-4">End Boundary</th>
                    <th className="py-3 px-4">Active Configuration</th>
                    {canWrite && <th className="py-3 px-4 text-right">Actions</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredYears.map((y) => (
                    <tr key={y.academicYearId} className="hover:bg-accent/5 transition-colors">
                      {canWrite && (
                        <td className="py-3.5 px-4">
                          <input
                            type="checkbox"
                            checked={selectedIds.includes(y.academicYearId)}
                            onChange={() => toggleSelectRow(y.academicYearId)}
                            className="rounded border-input text-primary focus:ring-primary cursor-pointer h-4 w-4"
                          />
                        </td>
                      )}
                      <td className="py-3.5 px-4 font-semibold text-foreground flex items-center gap-2">
                        <div className="h-7 w-7 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                          <Calendar className="h-4 w-4" />
                        </div>
                        {y.name}
                      </td>
                      <td className="py-3.5 px-4 text-muted-foreground">
                        {new Date(y.startDate).toLocaleDateString()}
                      </td>
                      <td className="py-3.5 px-4 text-muted-foreground">
                        {new Date(y.endDate).toLocaleDateString()}
                      </td>
                      <td className="py-3.5 px-4">
                        {y.current ? (
                          <span className="inline-flex items-center gap-1 text-emerald-500 font-medium text-xs">
                            <CheckCircle className="h-3.5 w-3.5" /> Current Session
                          </span>
                        ) : (
                          <span className="text-muted-foreground text-xs">—</span>
                        )}
                      </td>
                      {canWrite && (
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleEditClick(y)}
                              className="h-8 w-8 p-0 cursor-pointer border-border text-foreground hover:bg-accent/15"
                            >
                              <Edit2 className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              variant="danger"
                              size="sm"
                              onClick={() => handleDeleteClick(y.academicYearId)}
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

      {/* Creation Modal */}
      <Dialog
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingYear ? "Edit Academic Year" : "Create Academic Year"}
        description={
          editingYear
            ? "Modify start dates, end dates, and current session settings."
            : "Define calendar boundary sessions. Mark as current to set as active platform focus."
        }
      >
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Input
            type="text"
            label="Academic Session Name"
            placeholder="2026-2027"
            error={errors.name?.message}
            {...register("name")}
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              type="date"
              label="Start Date"
              error={errors.startDate?.message}
              {...register("startDate")}
            />

            <Input
              type="date"
              label="End Date"
              error={errors.endDate?.message}
              {...register("endDate")}
            />
          </div>

          <div className="flex items-center gap-3 py-2 border-t border-b border-border my-1">
            <input
              id="current-switch"
              type="checkbox"
              className="rounded border-input text-primary focus:ring-primary cursor-pointer h-4.5 w-4.5"
              {...register("current")}
            />
            <label htmlFor="current-switch" className="text-xs font-semibold text-foreground cursor-pointer flex flex-col gap-0.5">
              <span>Set as Current Session</span>
              <span className="text-3xs text-muted-foreground font-normal">This will automatically unset any other current year inside this tenant.</span>
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createMutation.isPending || updateMutation.isPending}>
              {editingYear ? "Save Changes" : "Create Session"}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
