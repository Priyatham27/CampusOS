"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import Button from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import Dialog from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import EmptyState from "@/components/ui/empty-state";
import { useToast } from "@/components/ui/toast";
import {
  Users,
  Search,
  SlidersHorizontal,
  Plus,
  FileDown,
  FileSpreadsheet,
  Trash2,
  Archive,
  RefreshCcw,
  Sparkles,
  Info,
  CheckCircle2,
  XCircle,
  Eye,
  GraduationCap
} from "lucide-react";
import { Student, StudentStatus } from "@/types/student";
import { Branch, Semester } from "@/types/academic";

const studentSchema = z.object({
  rollNumber: z.string().min(2, "Roll number is required"),
  firstName: z.string().min(1, "First name is required"),
  lastName: z.string().min(1, "Last name is required"),
  email: z.string().email("Invalid email address"),
  phone: z.string().optional(),
  dateOfBirth: z.string().min(1, "Date of birth is required"),
  gender: z.string().min(1, "Gender is required"),
  bloodGroup: z.string().optional(),
  departmentId: z.string().optional(),
  programId: z.string().optional(),
  branchId: z.string().optional(),
  semesterId: z.string().optional(),
  sectionId: z.string().optional(),
});

type StudentFormValues = z.infer<typeof studentSchema>;

export default function StudentDirectoryPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const orgId = user?.tenant?.organizationId || "";
  const { success, error: toastError } = useToast();

  // Search & Filter State
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterBranch, setFilterBranch] = useState<string>("");
  const [filterSemester, setFilterSemester] = useState<string>("");
  const [showFilters, setShowFilters] = useState(false);

  // Modals
  const [createOpen, setCreateOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

  // Bulk Import state
  const [csvText, setCsvText] = useState("");
  const [importResult, setImportResult] = useState<any>(null);

  // Pagination
  const [page, setPage] = useState(1);
  const limit = 20;

  const form = useForm<StudentFormValues>({
    resolver: zodResolver(studentSchema),
    defaultValues: {
      rollNumber: "",
      firstName: "",
      lastName: "",
      email: "",
      phone: "",
      dateOfBirth: "",
      gender: "MALE",
      bloodGroup: "",
      departmentId: "",
      programId: "",
      branchId: "",
      semesterId: "",
      sectionId: "",
    }
  });

  // Queries
  const { data: studentsData, isLoading: loadingStudents } = useQuery<{ data: Student[]; meta: { total: number } }>({
    queryKey: ["students", orgId, page, search, filterStatus, filterBranch, filterSemester],
    queryFn: () => {
      const params = new URLSearchParams({
        skip: String((page - 1) * limit),
        limit: String(limit),
      });
      if (search) params.append("searchQuery", search);
      if (filterStatus) params.append("status", filterStatus);
      if (filterBranch) params.append("branchId", filterBranch);
      if (filterSemester) params.append("semesterId", filterSemester);

      return api.get<{ data: Student[]; meta: { total: number } }>(
        `/organizations/${orgId}/students?${params.toString()}`
      );
    },
    enabled: !!orgId,
  });

  const { data: branches = [] } = useQuery<Branch[]>({
    queryKey: ["branches", orgId],
    queryFn: () => api.get<Branch[]>(`/organizations/${orgId}/branches`),
    enabled: !!orgId,
  });

  const { data: semesters = [] } = useQuery<Semester[]>({
    queryKey: ["semesters", orgId],
    queryFn: () => api.get<Semester[]>(`/organizations/${orgId}/semesters`),
    enabled: !!orgId,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: StudentFormValues) =>
      api.post<Student>(`/organizations/${orgId}/students`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["students", orgId] });
      success("Student Created", "Canonical student profile and user identity created successfully.");
      setCreateOpen(false);
      form.reset();
    },
    onError: (err: any) => toastError("Error Creating Student", err?.detail || "Roll number already registered.")
  });

  const archiveMutation = useMutation({
    mutationFn: (studentId: string) =>
      api.post(`/organizations/${orgId}/students/${studentId}/archive`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["students", orgId] });
      success("Student Archived", "Profile set to archived read-only state.");
    },
    onError: (err: any) => toastError("Archive Failed", err?.detail || "Could not archive profile.")
  });

  const restoreMutation = useMutation({
    mutationFn: (studentId: string) =>
      api.post(`/organizations/${orgId}/students/${studentId}/restore`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["students", orgId] });
      success("Student Restored", "Profile restored to active status.");
    },
    onError: (err: any) => toastError("Restore Failed", err?.detail || "Could not restore profile.")
  });

  const importMutation = useMutation({
    mutationFn: (records: any[]) =>
      api.post(`/organizations/${orgId}/students/import`, { records }),
    onSuccess: (res: any) => {
      queryClient.invalidateQueries({ queryKey: ["students", orgId] });
      setImportResult(res);
      success("Import Completed", `${res.successCount} profiles successfully created.`);
    },
    onError: (err: any) => toastError("Import Failed", err?.detail || "Verify headers structure.")
  });

  const onSubmit = (data: StudentFormValues) => {
    createMutation.mutate(data);
  };

  const handleParseCSV = () => {
    try {
      const lines = csvText.split("\n").filter(l => l.trim() !== "");
      if (lines.length < 2) {
        toastError("Invalid CSV", "Please provide a header and at least one record row.");
        return;
      }
      
      const headers = lines[0].split(",").map(h => h.trim());
      const records = [];

      for (let i = 1; i < lines.length; i++) {
        const row = lines[i].split(",").map(val => val.trim());
        if (row.length !== headers.length) continue;

        const obj: any = {};
        headers.forEach((h, index) => {
          // Map snake/camel csv names to schema fields
          const key = h.replace(/_([a-z])/g, (g) => g[1].toUpperCase());
          obj[key] = row[index];
        });
        records.push(obj);
      }

      importMutation.mutate(records);
    } catch (e) {
      toastError("CSV Parse Error", "Verify your comma separated formatting.");
    }
  };

  const handleExportCSV = () => {
    if (!studentsData?.data || studentsData.data.length === 0) return;
    
    const headers = "Student ID,Roll Number,First Name,Last Name,Email,Phone,Gender,Status\n";
    const rows = studentsData.data.map(s => 
      `"${s.studentId}","${s.rollNumber}","${s.firstName}","${s.lastName}","${s.email}","${s.phone || ""}","${s.gender}","${s.status}"`
    ).join("\n");

    const blob = new Blob([headers + rows], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.setAttribute("href", url);
    a.setAttribute("download", `campusos_students_export.csv`);
    a.click();
    success("CSV File Generated", "Started export download.");
  };

  const canWrite = user?.role?.permissions.includes("*") || user?.role?.permissions.includes("student:write");

  const totalPages = studentsData ? Math.ceil(studentsData.meta.total / limit) : 1;

  return (
    <div className="flex flex-col gap-6">
      {/* Top Header Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Users className="h-6 w-6 text-primary" /> Student Directory
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Single source of truth for academic profiles, emergency contacts, and collegiate documents
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExportCSV} className="text-xs">
            <FileDown className="mr-1.5 h-4 w-4" /> Export CSV
          </Button>
          {canWrite && (
            <>
              <Button variant="outline" size="sm" onClick={() => { setImportResult(null); setImportOpen(true); }} className="text-xs">
                <FileSpreadsheet className="mr-1.5 h-4 w-4" /> Bulk Import
              </Button>
              <Button size="sm" onClick={() => setCreateOpen(true)} className="text-xs">
                <Plus className="mr-1.5 h-4 w-4" /> Add Student
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Directory Console Search & Filters */}
      <Card className="glass">
        <CardContent className="py-4 flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="relative w-full md:max-w-md">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by name, email, roll number..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="w-full bg-background/50 border border-border rounded-xl pl-9 pr-4 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
            />
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto">
            <Button
              variant={showFilters ? "primary" : "outline"}
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              className="text-xs font-semibold"
            >
              <SlidersHorizontal className="mr-1.5 h-4 w-4" /> Filters
            </Button>

            {(filterStatus || filterBranch || filterSemester) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setFilterStatus("");
                  setFilterBranch("");
                  setFilterSemester("");
                  setPage(1);
                }}
                className="text-xs text-destructive hover:bg-destructive/10 cursor-pointer"
              >
                Clear Filters
              </Button>
            )}
          </div>
        </CardContent>

        {showFilters && (
          <div className="border-t border-border/60 bg-muted/20 px-6 py-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1">
              <label className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">Academic Status</label>
              <select
                value={filterStatus}
                onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
                className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none"
              >
                <option value="">All Statuses</option>
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
                <option value="ARCHIVED">Archived</option>
                <option value="GRADUATED">Graduated</option>
                <option value="SUSPENDED">Suspended</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">Branch/Department</label>
              <select
                value={filterBranch}
                onChange={(e) => { setFilterBranch(e.target.value); setPage(1); }}
                className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none"
              >
                <option value="">All Branches</option>
                {branches.map((b) => (
                  <option key={b.id} value={b.id}>{b.name} ({b.code})</option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">Semester Level</label>
              <select
                value={filterSemester}
                onChange={(e) => { setFilterSemester(e.target.value); setPage(1); }}
                className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none"
              >
                <option value="">All Semesters</option>
                {semesters.map((s) => (
                  <option key={s.id} value={s.id}>{s.name} (Term {s.number})</option>
                ))}
              </select>
            </div>
          </div>
        )}
      </Card>

      {/* Directory Table Grid */}
      {loadingStudents ? (
        <div className="space-y-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : studentsData && studentsData.data.length > 0 ? (
        <div className="flex flex-col gap-4">
          <div className="border border-border/80 rounded-xl overflow-hidden glass">
            <div className="overflow-x-auto scrollbar-thin">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-border/80 bg-muted/30 text-muted-foreground font-semibold uppercase tracking-wider">
                    <th className="py-3 px-4">Roll Number</th>
                    <th className="py-3 px-4">Student Name</th>
                    <th className="py-3 px-4">Contact Email</th>
                    <th className="py-3 px-4">Academic Status</th>
                    <th className="py-3 px-4">Emergency</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40 text-foreground">
                  {studentsData.data.map((student) => {
                    const statusColors: Record<StudentStatus, string> = {
                      ACTIVE: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
                      INACTIVE: "bg-amber-500/10 text-amber-400 border-amber-500/20",
                      ARCHIVED: "bg-blue-500/10 text-blue-400 border-blue-500/20",
                      GRADUATED: "bg-purple-500/10 text-purple-400 border-purple-500/20",
                      SUSPENDED: "bg-rose-500/10 text-rose-400 border-rose-500/20",
                    };

                    return (
                      <tr key={student.id} className="hover:bg-muted/10 transition-colors">
                        <td className="py-3.5 px-4 font-mono font-bold text-primary">{student.rollNumber}</td>
                        <td className="py-3.5 px-4 font-semibold text-foreground">
                          {student.firstName} {student.lastName}
                        </td>
                        <td className="py-3.5 px-4 text-muted-foreground">{student.email}</td>
                        <td className="py-3.5 px-4">
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold border ${statusColors[student.status]}`}>
                            {student.status}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-muted-foreground">
                          {student.emergencyContact ? (
                            <span>{student.emergencyContact.name} ({student.emergencyContact.phone})</span>
                          ) : (
                            <span className="text-[10px] italic">Not Set</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Link href={`/dashboard/students/${student.studentId}`}>
                              <Button variant="ghost" size="sm" className="h-8 text-primary hover:bg-primary/10 cursor-pointer">
                                <Eye className="h-4 w-4" />
                              </Button>
                            </Link>
                            {canWrite && (
                              <>
                                {!student.isArchived ? (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => {
                                      if (confirm(`Archive student profile for ${student.firstName}? This locks modifications.`)) {
                                        archiveMutation.mutate(student.studentId);
                                      }
                                    }}
                                    className="h-8 text-amber-500 hover:bg-amber-500/10 cursor-pointer"
                                    title="Archive Profile"
                                  >
                                    <Archive className="h-4 w-4" />
                                  </Button>
                                ) : (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => restoreMutation.mutate(student.studentId)}
                                    className="h-8 text-emerald-500 hover:bg-emerald-500/10 cursor-pointer"
                                    title="Restore Profile"
                                  >
                                    <RefreshCcw className="h-4 w-4" />
                                  </Button>
                                )}
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-border pt-4 text-xs">
              <span className="text-muted-foreground">
                Showing Page <strong>{page}</strong> of <strong>{totalPages}</strong> (Total: {studentsData.meta.total} records)
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === 1}
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  className="text-xs"
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === totalPages}
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  className="text-xs"
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <EmptyState
          title="No Students Registered"
          description="Create manual academic profiles or run CSV uploads to import students."
          actionText={canWrite ? "Register Student" : undefined}
          onAction={canWrite ? () => setCreateOpen(true) : undefined}
        />
      )}

      {/* CREATE STUDENT DIALOG */}
      <Dialog isOpen={createOpen} onClose={() => setCreateOpen(false)} title="Register Student Profile">
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">Roll Number</label>
              <Input {...form.register("rollNumber")} placeholder="e.g. CSE-2026-001" className="text-xs" />
              {form.formState.errors.rollNumber && (
                <p className="text-[10px] text-rose-400 font-medium">{form.formState.errors.rollNumber.message}</p>
              )}
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">Contact Email</label>
              <Input {...form.register("email")} type="email" placeholder="johndoe@college.edu" className="text-xs" />
              {form.formState.errors.email && (
                <p className="text-[10px] text-rose-400 font-medium">{form.formState.errors.email.message}</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">First Name</label>
              <Input {...form.register("firstName")} placeholder="John" className="text-xs" />
              {form.formState.errors.firstName && (
                <p className="text-[10px] text-rose-400 font-medium">{form.formState.errors.firstName.message}</p>
              )}
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">Last Name</label>
              <Input {...form.register("lastName")} placeholder="Doe" className="text-xs" />
              {form.formState.errors.lastName && (
                <p className="text-[10px] text-rose-400 font-medium">{form.formState.errors.lastName.message}</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">Gender</label>
              <select
                {...form.register("gender")}
                className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none"
              >
                <option value="MALE">Male</option>
                <option value="FEMALE">Female</option>
                <option value="OTHER">Other</option>
              </select>
            </div>

            <div className="space-y-1 col-span-2">
              <label className="text-xs text-muted-foreground font-semibold">Date of Birth</label>
              <Input {...form.register("dateOfBirth")} type="date" className="text-xs" />
              {form.formState.errors.dateOfBirth && (
                <p className="text-[10px] text-rose-400 font-medium">{form.formState.errors.dateOfBirth.message}</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 border-t border-border pt-4 mt-2">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">Academic Branch</label>
              <select
                {...form.register("branchId")}
                className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none"
              >
                <option value="">Select Branch</option>
                {branches.map(b => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">Semester Level</label>
              <select
                {...form.register("semesterId")}
                className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none"
              >
                <option value="">Select Semester</option>
                {semesters.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 border-t border-border pt-4 mt-4">
            <Button variant="outline" size="sm" type="button" onClick={() => setCreateOpen(false)} className="text-xs">
              Cancel
            </Button>
            <Button size="sm" type="submit" disabled={createMutation.isPending} className="text-xs">
              Register Student
            </Button>
          </div>
        </form>
      </Dialog>

      {/* BULK IMPORT CSV WIZARD */}
      <Dialog isOpen={importOpen} onClose={() => setImportOpen(false)} title="Bulk Student CSV Import Wizard">
        <div className="space-y-4">
          <div className="bg-primary/5 rounded-xl border border-primary/10 p-4 flex gap-3 text-xs text-muted-foreground">
            <Info className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-primary">Required CSV Headers Mapping</h4>
              <p className="mt-1">
                Your CSV format must match the schema keys precisely:
              </p>
              <p className="font-mono bg-background px-2 py-1 rounded border border-border/80 text-[10px] text-foreground mt-2 overflow-x-auto">
                roll_number,first_name,last_name,email,phone,date_of_birth,gender,blood_group
              </p>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-semibold">Paste Comma Separated CSV Data</label>
            <textarea
              value={csvText}
              onChange={(e) => setCsvText(e.target.value)}
              className="w-full h-44 bg-background border border-border rounded-xl p-3 text-[11px] font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary"
              placeholder={`roll_number,first_name,last_name,email,date_of_birth,gender\nCSE-2026-10,Betty,Cooper,betty@school.com,2004-03-12,FEMALE`}
            />
          </div>

          {importResult && (
            <div className="border border-border rounded-xl p-4 space-y-3 bg-muted/10 text-xs">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                <span className="font-semibold text-foreground">
                  Processed: {importResult.successCount} Successful imports, {importResult.failedCount} Failures
                </span>
              </div>
              
              {importResult.errors && importResult.errors.length > 0 && (
                <div className="space-y-1.5 border-t border-border pt-2.5">
                  <span className="font-bold text-rose-400">Failed Records Log:</span>
                  <div className="max-h-24 overflow-y-auto space-y-1 font-mono text-[10px]">
                    {importResult.errors.map((err: any, idx: number) => (
                      <p key={idx} className="text-rose-400/90">
                        Row {err.row} (Roll: {err.rollNumber}): {err.error}
                      </p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 border-t border-border pt-4 mt-4">
            <Button variant="outline" size="sm" onClick={() => setImportOpen(false)} className="text-xs">
              Close
            </Button>
            <Button size="sm" onClick={handleParseCSV} disabled={importMutation.isPending} className="text-xs">
              Validate and Import
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
