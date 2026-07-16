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
  Layers,
  RefreshCw,
  Search,
  AlertTriangle,
} from "lucide-react";
import { Semester, AcademicYear } from "@/types/academic";

const semesterSchema = z.object({
  number: z.number().min(1, "Semester number must be at least 1").max(20, "Semester number must be less than 20"),
  name: z.string().min(3, "Name must be at least 3 characters"),
  status: z.enum(["ACTIVE", "INACTIVE"]),
  academicYearId: z.string().optional().or(z.literal("")),
});

type FormValues = z.infer<typeof semesterSchema>;

export default function SemestersPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const orgId = user?.tenant?.organizationId || "";
  const { success, error: toastError } = useToast();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingSemester, setEditingSemester] = useState<Semester | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Fetch list of semesters
  const { data: semesters = [], isLoading, refetch } = useQuery<Semester[]>({
    queryKey: ["semesters", orgId],
    queryFn: () => api.get<Semester[]>(`/organizations/${orgId}/semesters`),
    enabled: !!orgId,
  });

  // Fetch academic years for dropdown selector
  const { data: years = [] } = useQuery<AcademicYear[]>({
    queryKey: ["academic_years", orgId],
    queryFn: () => api.get<AcademicYear[]>(`/organizations/${orgId}/academic-years`),
    enabled: !!orgId,
  });

  // Sort semesters by number ascending
  const sortedSemesters = [...semesters].sort((a, b) => a.number - b.number);
  const nextExpectedNumber = sortedSemesters.length > 0 ? sortedSemesters[sortedSemesters.length - 1].number + 1 : 1;

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(semesterSchema),
    defaultValues: {
      status: "ACTIVE",
    },
  });

  // Mutate create
  const createMutation = useMutation({
    mutationFn: (data: FormValues) => {
      const payload: any = { ...data };
      if (!payload.academicYearId) delete payload.academicYearId;
      return api.post<Semester>(`/organizations/${orgId}/semesters`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["semesters", orgId] });
      success("Semester Created", "The semester has been registered.");
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
      if (!payload.academicYearId) payload.academicYearId = null;
      return api.patch<Semester>(`/organizations/${orgId}/semesters/${id}`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["semesters", orgId] });
      success("Semester Updated", "Details updated successfully.");
      setModalOpen(false);
      setEditingSemester(null);
      reset();
    },
    onError: (err: any) => {
      toastError("Failed to Update", err?.detail || "An error occurred.");
    },
  });

  // Mutate delete
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/organizations/${orgId}/semesters/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["semesters", orgId] });
      success("Deleted", "Semester soft-deleted successfully.");
    },
    onError: (err: any) => {
      toastError("Failed to Delete", err?.detail || "An error occurred.");
    },
  });

  const onSubmit = (data: FormValues) => {
    if (editingSemester) {
      updateMutation.mutate({ id: editingSemester.semesterId, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleEditClick = (sem: Semester) => {
    setEditingSemester(sem);
    setValue("number", sem.number);
    setValue("name", sem.name);
    setValue("status", sem.status);
    setValue("academicYearId", sem.academicYearId || "");
    setModalOpen(true);
  };

  const handleDeleteClick = (sem: Semester) => {
    // Show warnings regarding the sequence deletion rule
    const maxSem = sortedSemesters.length > 0 ? sortedSemesters[sortedSemesters.length - 1].number : 0;
    if (sem.number < maxSem) {
      alert(`Cannot delete Semester ${sem.number}. Only the highest semester (${maxSem}) can be deleted first to maintain sequence integrity.`);
      return;
    }

    if (confirm(`Are you sure you want to delete ${sem.name}?`)) {
      deleteMutation.mutate(sem.semesterId);
    }
  };

  // Filter local lists by search query
  const filteredSemesters = sortedSemesters.filter((s) =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const canWrite =
    user?.role?.permissions.includes("*") || user?.role?.permissions.includes("academic:write");

  return (
    <div className="flex flex-col gap-6">
      {/* Sequence warning banner */}
      {canWrite && sortedSemesters.length > 0 && (
        <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/5 text-amber-500 text-2xs flex gap-3 items-start leading-relaxed">
          <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <div className="flex flex-col gap-0.5">
            <span className="font-bold">Semester Sequence Enforced</span>
            <span>
              The system requires semester numbers to be registered sequentially without gaps. The next expected semester is **Semester {nextExpectedNumber}**. Deleting semesters is restricted to the highest registered semester number only.
            </span>
          </div>
        </div>
      )}

      {/* Search and Action Toolbar */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-stretch md:items-center">
        {/* Search */}
        <div className="relative max-w-sm w-full">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search semesters..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-9 rounded-lg bg-accent/10 border border-input pl-10 pr-4 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary focus-visible:ring-offset-0 placeholder:text-muted-foreground transition-all duration-200"
          />
        </div>

        {/* Buttons */}
        <div className="flex items-center gap-3">
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
                setEditingSemester(null);
                reset({ number: nextExpectedNumber, name: `Semester ${nextExpectedNumber}`, status: "ACTIVE", academicYearId: "" });
                setModalOpen(true);
              }}
              size="sm"
              className="flex items-center gap-1.5"
            >
              <Plus className="h-4 w-4" /> Add Semester
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
          ) : filteredSemesters.length === 0 ? (
            <EmptyState
              title="No Semesters Found"
              description="Configure semester levels sequentially for the academic calendar."
              actionText={canWrite ? "Register First Semester" : undefined}
              onAction={
                canWrite
                  ? () => {
                      setEditingSemester(null);
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
                    <th className="py-3 px-4">Semester Name</th>
                    <th className="py-3 px-4">Sequence Number</th>
                    <th className="py-3 px-4">Linked Session Year</th>
                    <th className="py-3 px-4">Status</th>
                    {canWrite && <th className="py-3 px-4 text-right">Actions</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredSemesters.map((s) => {
                    const matchedYear = years.find((y) => y.academicYearId === s.academicYearId || y.id === s.academicYearId);
                    return (
                      <tr key={s.semesterId} className="hover:bg-accent/5 transition-colors">
                        <td className="py-3.5 px-4 font-semibold text-foreground flex items-center gap-2">
                          <div className="h-7 w-7 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                            <Layers className="h-4 w-4" />
                          </div>
                          {s.name}
                        </td>
                        <td className="py-3.5 px-4 font-mono font-bold text-xs">Seq #{s.number}</td>
                        <td className="py-3.5 px-4 text-muted-foreground">{matchedYear?.name || "Unlinked / All Years"}</td>
                        <td className="py-3.5 px-4">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-3xs font-bold uppercase tracking-wider border ${
                              s.status === "ACTIVE"
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                            }`}
                          >
                            {s.status}
                          </span>
                        </td>
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
                                onClick={() => handleDeleteClick(s)}
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
        title={editingSemester ? "Edit Semester" : "Create Semester"}
        description="Configure class semester sequential positions, status, and linked years."
      >
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Input
            type="number"
            label="Sequence Position Number"
            placeholder={nextExpectedNumber.toString()}
            disabled={true} // Strict backend rule: Direct number modification is not permitted
            error={errors.number?.message}
            {...register("number", { valueAsNumber: true })}
          />

          <Input
            type="text"
            label="Semester Name"
            placeholder={`Semester ${nextExpectedNumber}`}
            error={errors.name?.message}
            {...register("name")}
          />

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Linked Academic Year (Optional)
            </label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              {...register("academicYearId")}
            >
              <option value="">Link to all active sessions...</option>
              {years.map((y) => (
                <option key={y.academicYearId} value={y.academicYearId}>
                  {y.name} {y.current ? "(Current Session)" : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Semester Status
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
              {editingSemester ? "Save Changes" : "Create Semester"}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
