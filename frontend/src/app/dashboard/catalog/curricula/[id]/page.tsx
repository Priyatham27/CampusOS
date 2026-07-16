"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ArrowLeft,
  BookText,
  Layers,
  PlusCircle,
  Pencil,
  Trash2,
  GitMerge,
  X,
  BookOpen,
  FlaskConical,
  FolderOpen,
  Presentation,
  CheckCircle2,
  FileEdit,
  Archive,
  ClipboardList,
} from "lucide-react";
import {
  Curriculum,
  Subject,
  SubjectType,
  FullCurriculum,
  SubjectCreatePayload,
} from "@/types/catalog";

const subjectTypeIcons: Record<SubjectType, React.ElementType> = {
  CORE: BookOpen,
  ELECTIVE: FolderOpen,
  LAB: FlaskConical,
  PROJECT: ClipboardList,
  SEMINAR: Presentation,
};

const subjectTypeColors: Record<SubjectType, string> = {
  CORE: "bg-sky-500/10 text-sky-400",
  ELECTIVE: "bg-violet-500/10 text-violet-400",
  LAB: "bg-emerald-500/10 text-emerald-400",
  PROJECT: "bg-amber-500/10 text-amber-400",
  SEMINAR: "bg-pink-500/10 text-pink-400",
};

const statusColors: Record<string, string> = {
  ACTIVE: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/25",
  DRAFT: "bg-amber-500/10 text-amber-400 border border-amber-500/25",
  ARCHIVED: "bg-zinc-500/10 text-zinc-400 border border-zinc-500/25",
};

export default function CurriculumDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const orgId = user?.tenant?.organizationId || "";
  const qc = useQueryClient();

  const [addingSem, setAddingSem] = useState<number | null>(null);
  const [subjectForm, setSubjectForm] = useState<Partial<SubjectCreatePayload>>({
    subjectType: "CORE",
    isElective: false,
    prerequisites: [],
    credits: 3,
  });
  const [deleteConfirm, setDeleteConfirm] = useState<Subject | null>(null);

  const { data: fullCurriculum, isLoading } = useQuery<FullCurriculum>({
    queryKey: ["full_curriculum", orgId, id],
    queryFn: async () => {
      const res = await api.get<any>(`/organizations/${orgId}/catalog/curricula/${id}/full`);
      return res;
    },
    enabled: !!orgId && !!id,
  });

  const curriculum = fullCurriculum?.curriculum;
  const semesters = fullCurriculum?.semesters || {};
  const semesterKeys = Object.keys(semesters)
    .map(Number)
    .sort((a, b) => a - b);
  const maxSem = semesterKeys.length > 0 ? Math.max(...semesterKeys) : 0;

  const createSubjectMutation = useMutation({
    mutationFn: (payload: SubjectCreatePayload) =>
      api.post(`/organizations/${orgId}/catalog/curricula/${id}/subjects`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["full_curriculum", orgId, id] });
      setAddingSem(null);
      setSubjectForm({ subjectType: "CORE", isElective: false, prerequisites: [], credits: 3 });
    },
  });

  const deleteSubjectMutation = useMutation({
    mutationFn: (subjectId: string) =>
      api.delete(`/organizations/${orgId}/catalog/curricula/${id}/subjects/${subjectId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["full_curriculum", orgId, id] });
      setDeleteConfirm(null);
    },
  });

  const allSubjects = Object.values(semesters).flat() as Subject[];
  const totalCredits = allSubjects.reduce((sum, s) => sum + s.credits, 0);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-24 w-full" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (!curriculum) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
        <BookText className="h-10 w-10 text-muted-foreground opacity-30" />
        <p className="text-sm font-semibold">Curriculum not found.</p>
        <Link
          href="/dashboard/catalog/curricula"
          className="text-xs text-primary hover:underline"
        >
          ← Back to Curricula
        </Link>
      </div>
    );
  }

  const handleAddSubject = () => {
    if (!addingSem || !subjectForm.name || !subjectForm.subjectCode) return;
    createSubjectMutation.mutate({
      semesterNumber: addingSem,
      subjectCode: subjectForm.subjectCode!,
      name: subjectForm.name!,
      credits: subjectForm.credits || 3,
      subjectType: subjectForm.subjectType as SubjectType || "CORE",
      isElective: subjectForm.isElective || false,
      electiveGroup: subjectForm.electiveGroup,
      prerequisites: subjectForm.prerequisites || [],
    });
  };

  // Render semesters — show up to maxSem + 1 to allow adding new semesters
  const displaySems = Array.from(
    { length: Math.max(maxSem + 1, 4) },
    (_, i) => i + 1
  );

  return (
    <div className="flex flex-col gap-6">
      {/* Back */}
      <Link
        href="/dashboard/catalog/curricula"
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Curricula
      </Link>

      {/* Header */}
      <Card glass>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-bold">{curriculum.name}</h2>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-3xs font-bold uppercase tracking-wider ${
                  statusColors[curriculum.status]
                }`}
              >
                {curriculum.status}
              </span>
              <span className="text-xs text-muted-foreground font-semibold">
                v{curriculum.version}
              </span>
            </div>
            {curriculum.description && (
              <p className="text-xs text-muted-foreground max-w-2xl">{curriculum.description}</p>
            )}
            <div className="flex items-center gap-4 mt-1">
              <span className="text-2xs text-muted-foreground">
                <strong className="text-foreground">{fullCurriculum?.totalSubjects || 0}</strong> Subjects
              </span>
              <span className="text-2xs text-muted-foreground">
                <strong className="text-foreground">{totalCredits.toFixed(1)}</strong> Credits
              </span>
              {curriculum.admissionBatch && (
                <span className="text-2xs text-muted-foreground">
                  Batch <strong className="text-foreground">{curriculum.admissionBatch}</strong>
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href={`/dashboard/catalog/curricula/${id}/prerequisites`}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border text-xs font-semibold hover:bg-accent/10 transition-colors"
            >
              <GitMerge className="h-4 w-4" />
              Prerequisite Graph
            </Link>
          </div>
        </div>
      </Card>

      {/* Semester Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {displaySems.map((semNum) => {
          const semSubjects = (semesters[semNum] || []) as Subject[];
          const semCredits = semSubjects.reduce((s, sub) => s + sub.credits, 0);

          return (
            <Card key={semNum} glass className="flex flex-col gap-4">
              {/* Semester Header */}
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <div className="h-6 w-6 rounded bg-violet-500/10 text-violet-400 flex items-center justify-center">
                    <span className="text-2xs font-bold">{semNum}</span>
                  </div>
                  <span className="text-xs font-bold uppercase tracking-wider">Semester {semNum}</span>
                  {semSubjects.length > 0 && (
                    <span className="text-3xs text-muted-foreground">
                      {semSubjects.length} subjects · {semCredits.toFixed(1)} cr
                    </span>
                  )}
                </div>
                {curriculum.status === "DRAFT" && (
                  <button
                    onClick={() => setAddingSem(semNum)}
                    className="h-6 w-6 flex items-center justify-center rounded border border-border text-muted-foreground hover:text-violet-400 hover:border-violet-500/30 transition-colors"
                    title="Add Subject"
                  >
                    <PlusCircle className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>

              {/* Subject List */}
              {semSubjects.length === 0 ? (
                <p className="text-2xs text-muted-foreground text-center py-2">
                  No subjects yet.
                  {curriculum.status === "DRAFT" && (
                    <button
                      onClick={() => setAddingSem(semNum)}
                      className="ml-1 text-violet-400 hover:underline"
                    >
                      Add one
                    </button>
                  )}
                </p>
              ) : (
                <div className="flex flex-col gap-2">
                  {semSubjects.map((subject) => {
                    const Icon = subjectTypeIcons[subject.subjectType] || BookOpen;
                    return (
                      <div
                        key={subject.subjectId}
                        className="flex items-center gap-3 p-2.5 rounded-lg border border-border/50 bg-accent/5 hover:bg-accent/10 transition-colors group"
                      >
                        <div
                          className={`h-7 w-7 rounded flex items-center justify-center flex-shrink-0 ${
                            subjectTypeColors[subject.subjectType]
                          }`}
                        >
                          <Icon className="h-3.5 w-3.5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-2xs font-mono font-bold text-muted-foreground">
                              {subject.subjectCode}
                            </span>
                            {subject.isElective && (
                              <span className="text-3xs px-1.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20">
                                Elective
                              </span>
                            )}
                          </div>
                          <p className="text-xs font-semibold truncate">{subject.name}</p>
                        </div>
                        <div className="flex flex-col items-end flex-shrink-0">
                          <span className="text-2xs font-bold tabular-nums">
                            {subject.credits} cr
                          </span>
                          {subject.prerequisites.length > 0 && (
                            <span className="text-3xs text-muted-foreground">
                              {subject.prerequisites.length} prereq
                            </span>
                          )}
                        </div>
                        {curriculum.status === "DRAFT" && (
                          <button
                            onClick={() => setDeleteConfirm(subject)}
                            className="opacity-0 group-hover:opacity-100 h-6 w-6 flex items-center justify-center rounded text-muted-foreground hover:text-rose-400 transition-all"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </Card>
          );
        })}
      </div>

      {/* Add Subject Modal */}
      {addingSem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <Card glass className="w-full max-w-lg flex flex-col gap-5">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold">Add Subject — Semester {addingSem}</h2>
              <button onClick={() => setAddingSem(null)}>
                <X className="h-5 w-5 text-muted-foreground hover:text-foreground" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Subject Code *
                </label>
                <input
                  type="text"
                  placeholder="CS101"
                  value={subjectForm.subjectCode || ""}
                  onChange={(e) =>
                    setSubjectForm({ ...subjectForm, subjectCode: e.target.value.toUpperCase() })
                  }
                  className="h-9 px-3 rounded-lg border border-border bg-background text-sm font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Credits *
                </label>
                <input
                  type="number"
                  min={0.5}
                  max={30}
                  step={0.5}
                  value={subjectForm.credits || 3}
                  onChange={(e) =>
                    setSubjectForm({ ...subjectForm, credits: parseFloat(e.target.value) })
                  }
                  className="h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>
              <div className="col-span-2 flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Subject Name *
                </label>
                <input
                  type="text"
                  placeholder="e.g., Data Structures and Algorithms"
                  value={subjectForm.name || ""}
                  onChange={(e) => setSubjectForm({ ...subjectForm, name: e.target.value })}
                  className="h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Type
                </label>
                <select
                  value={subjectForm.subjectType || "CORE"}
                  onChange={(e) =>
                    setSubjectForm({ ...subjectForm, subjectType: e.target.value as SubjectType })
                  }
                  className="h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  <option value="CORE">Core</option>
                  <option value="ELECTIVE">Elective</option>
                  <option value="LAB">Lab</option>
                  <option value="PROJECT">Project</option>
                  <option value="SEMINAR">Seminar</option>
                </select>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Elective Group
                </label>
                <input
                  type="text"
                  placeholder="e.g., OE-Group-A"
                  value={subjectForm.electiveGroup || ""}
                  onChange={(e) =>
                    setSubjectForm({ ...subjectForm, electiveGroup: e.target.value })
                  }
                  className="h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>
              <div className="col-span-2">
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={subjectForm.isElective || false}
                    onChange={(e) =>
                      setSubjectForm({ ...subjectForm, isElective: e.target.checked })
                    }
                    className="rounded border-border accent-violet-500"
                  />
                  <span className="text-xs font-semibold">Is Elective (student chooses from group)</span>
                </label>
              </div>
            </div>

            {createSubjectMutation.isError && (
              <p className="text-xs text-rose-400">
                {(createSubjectMutation.error as any)?.detail || "Failed to create subject."}
              </p>
            )}

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setAddingSem(null)}
                className="px-4 py-2 rounded-lg border border-border text-xs font-semibold hover:bg-accent/10 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddSubject}
                disabled={createSubjectMutation.isPending}
                className="px-5 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-xs font-semibold transition-colors"
              >
                {createSubjectMutation.isPending ? "Adding…" : "Add Subject"}
              </button>
            </div>
          </Card>
        </div>
      )}

      {/* Delete Subject Confirm */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <Card glass className="w-full max-w-md flex flex-col gap-5">
            <h2 className="text-base font-bold">Delete Subject?</h2>
            <p className="text-sm text-muted-foreground">
              Remove <strong>{deleteConfirm.name}</strong> ({deleteConfirm.subjectCode}) from Semester{" "}
              {deleteConfirm.semesterNumber}? This cannot be undone if other subjects depend on it as a prerequisite.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 rounded-lg border border-border text-xs font-semibold hover:bg-accent/10 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteSubjectMutation.mutate(deleteConfirm.subjectId)}
                disabled={deleteSubjectMutation.isPending}
                className="px-5 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white text-xs font-semibold transition-colors"
              >
                {deleteSubjectMutation.isPending ? "Deleting…" : "Delete"}
              </button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
