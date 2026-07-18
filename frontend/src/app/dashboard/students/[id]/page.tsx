"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import Button from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import Dialog from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import {
  Contact,
  ShieldCheck,
  Award,
  Layers,
  ArrowLeft,
  Mail,
  Phone,
  Calendar,
  Sparkles,
  Plus,
  Trash2,
  CheckCircle,
  Clock,
  UserCheck,
  FileText,
  Bookmark,
  FileCheck2,
  CheckCircle2,
  XCircle,
  HelpCircle,
  CalendarDays
} from "lucide-react";
import { StudentProfilePayload, Guardian, StudentDocument, StudentAchievement, StudentSkill } from "@/types/student";

const guardianSchema = z.object({
  name: z.string().min(2, "Name is required"),
  relation: z.string().min(2, "Relation is required"),
  phone: z.string().min(5, "Phone is required"),
  email: z.string().email("Invalid email").optional().or(z.literal("")),
  occupation: z.string().optional(),
  address: z.string().optional(),
  isPrimary: z.boolean(),
});

const docSchema = z.object({
  name: z.string().min(2, "Document name is required"),
  filePath: z.string().min(1, "File path is required"),
  fileType: z.string(),
  fileSize: z.number().min(1, "Size is required"),
  category: z.enum(["ACADEMIC", "IDENTITY", "MEDICAL", "OTHER"]),
});

const achSchema = z.object({
  title: z.string().min(2, "Title is required"),
  description: z.string().optional(),
  dateEarned: z.string().min(1, "Date is required"),
  category: z.enum(["ACADEMIC", "SPORTS", "CULTURAL", "OTHER"]),
  certificatePath: z.string().optional(),
});

const skillSchema = z.object({
  name: z.string().min(1, "Skill name is required"),
  level: z.enum(["BEGINNER", "INTERMEDIATE", "ADVANCED"]),
});

type GuardianFormValues = z.infer<typeof guardianSchema>;
type DocFormValues = z.infer<typeof docSchema>;
type AchFormValues = z.infer<typeof achSchema>;
type SkillFormValues = z.infer<typeof skillSchema>;

export default function StudentProfilePage() {
  const router = useRouter();
  const params = useParams();
  const studentId = params.id as string;
  const { user } = useAuth();
  const orgId = user?.tenant?.organizationId || "";
  const queryClient = useQueryClient();
  const { success, error: toastError } = useToast();

  const [activeTab, setActiveTab] = useState<"summary" | "guardians" | "documents" | "achievements" | "skills">("summary");

  // Modals state
  const [guardianModal, setGuardianModal] = useState(false);
  const [docModal, setDocModal] = useState(false);
  const [achModal, setAchModal] = useState(false);
  const [skillModal, setSkillModal] = useState(false);

  // Forms
  const gForm = useForm<GuardianFormValues>({ resolver: zodResolver(guardianSchema), defaultValues: { name: "", relation: "", phone: "", email: "", occupation: "", address: "", isPrimary: false } });
  const dForm = useForm<DocFormValues>({ resolver: zodResolver(docSchema), defaultValues: { name: "", filePath: "s3://campusos/docs/file.pdf", fileType: "PDF", fileSize: 1048576, category: "ACADEMIC" } });
  const aForm = useForm<AchFormValues>({ resolver: zodResolver(achSchema), defaultValues: { title: "", description: "", dateEarned: "", category: "ACADEMIC", certificatePath: "" } });
  const sForm = useForm<SkillFormValues>({ resolver: zodResolver(skillSchema), defaultValues: { name: "", level: "BEGINNER" } });

  // Note text state
  const [noteContent, setNoteContent] = useState("");

  // Query Profile payload
  const { data: payload, isLoading: loadingProfile } = useQuery<StudentProfilePayload>({
    queryKey: ["student_profile", orgId, studentId],
    queryFn: () => api.get<StudentProfilePayload>(`/organizations/${orgId}/students/${studentId}/profile`),
    enabled: !!orgId && !!studentId,
  });

  const student = payload?.student;

  // Mutations
  const addGuardianMutation = useMutation({
    mutationFn: (data: GuardianFormValues) =>
      api.post<Guardian>(`/organizations/${orgId}/students/${studentId}/guardians`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["student_profile", orgId, studentId] });
      success("Guardian Added", "Guardian details logged successfully.");
      setGuardianModal(false);
      gForm.reset();
    },
    onError: (err: any) => toastError("Error", err?.detail || "Action failed.")
  });

  const deleteGuardianMutation = useMutation({
    mutationFn: (guardianId: string) =>
      api.delete(`/organizations/${orgId}/students/${studentId}/guardians/${guardianId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["student_profile", orgId, studentId] });
      success("Guardian Deleted", "Record removed.");
    },
    onError: (err: any) => toastError("Error", err?.detail || "Action failed.")
  });

  const addDocMutation = useMutation({
    mutationFn: (data: DocFormValues) =>
      api.post<StudentDocument>(`/organizations/${orgId}/students/${studentId}/documents`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["student_profile", orgId, studentId] });
      success("Document Registered", "Upload metadata logged.");
      setDocModal(false);
      dForm.reset();
    },
    onError: (err: any) => toastError("Error", err?.detail || "Action failed.")
  });

  const deleteDocMutation = useMutation({
    mutationFn: (docId: string) =>
      api.delete(`/organizations/${orgId}/students/${studentId}/documents/${docId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["student_profile", orgId, studentId] });
      success("Document Deleted", "Metadata record removed.");
    },
    onError: (err: any) => toastError("Error", err?.detail || "Action failed.")
  });

  const verifyDocMutation = useMutation({
    mutationFn: ({ docId, verified }: { docId: string; verified: boolean }) =>
      api.post<StudentDocument>(`/organizations/${orgId}/students/${studentId}/documents/${docId}/verify?verified=${verified}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["student_profile", orgId, studentId] });
      success("Verification Updated", "Verification flag toggled.");
    },
    onError: (err: any) => toastError("Error", err?.detail || "Action failed.")
  });

  const addAchMutation = useMutation({
    mutationFn: (data: AchFormValues) =>
      api.post<StudentAchievement>(`/organizations/${orgId}/students/${studentId}/achievements`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["student_profile", orgId, studentId] });
      success("Achievement Logged", "Record registered.");
      setAchModal(false);
      aForm.reset();
    },
    onError: (err: any) => toastError("Error", err?.detail || "Action failed.")
  });

  const deleteAchMutation = useMutation({
    mutationFn: (achId: string) =>
      api.delete(`/organizations/${orgId}/students/${studentId}/achievements/${achId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["student_profile", orgId, studentId] });
      success("Achievement Deleted", "Record removed.");
    },
    onError: (err: any) => toastError("Error", err?.detail || "Action failed.")
  });

  const addSkillMutation = useMutation({
    mutationFn: (data: SkillFormValues) =>
      api.post<StudentSkill>(`/organizations/${orgId}/students/${studentId}/skills`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["student_profile", orgId, studentId] });
      success("Skill Added", "Skill badge updated.");
      setSkillModal(false);
      sForm.reset();
    },
    onError: (err: any) => toastError("Error", err?.detail || "Action failed.")
  });

  const deleteSkillMutation = useMutation({
    mutationFn: (skillId: string) =>
      api.delete(`/organizations/${orgId}/students/${studentId}/skills/${skillId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["student_profile", orgId, studentId] });
      success("Skill Deleted", "Record removed.");
    },
    onError: (err: any) => toastError("Error", err?.detail || "Action failed.")
  });

  const addNoteMutation = useMutation({
    mutationFn: (content: string) =>
      api.post(`/organizations/${orgId}/students/${studentId}/notes`, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["student_profile", orgId, studentId] });
      success("Note Logged", "Advisement note successfully added.");
      setNoteContent("");
    },
    onError: (err: any) => toastError("Error", err?.detail || "Action failed.")
  });

  if (loadingProfile) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-44 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (!student) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center text-xs">
        <XCircle className="h-10 w-10 text-rose-500 mb-2" />
        <h3 className="font-bold text-foreground">Profile Not Found</h3>
        <p className="text-muted-foreground mt-1">Verify student ID registry coordinates.</p>
        <Button size="sm" onClick={() => router.push("/dashboard/students")} className="mt-4">
          Return to Directory
        </Button>
      </div>
    );
  }

  const isArchived = student.isArchived || student.status === "ARCHIVED";
  const canWrite = (user?.role?.permissions.includes("*") || user?.role?.permissions.includes("student:write")) && !isArchived;

  // Format Bytes to human readable
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Return Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => router.push("/dashboard/students")} className="h-8 w-8 p-0 cursor-pointer">
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground">Collegiate Profile Console</span>
          <h2 className="text-lg font-bold text-foreground mt-0.5">Student Academic Profile</h2>
        </div>
      </div>

      {/* GORGEOUS AVATAR HEADER PANEL */}
      <div className="relative rounded-2xl overflow-hidden border border-border/80 glass bg-gradient-to-r from-primary/5 via-transparent to-primary/5 p-6 flex flex-col md:flex-row gap-6 items-start md:items-center">
        {/* Avatar circle */}
        <div className="h-20 w-20 rounded-2xl bg-primary/10 text-primary border border-primary/20 font-bold flex items-center justify-center text-3xl flex-shrink-0">
          {student.firstName[0]}
          {student.lastName[0]}
        </div>

        <div className="flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-bold text-foreground">
              {student.firstName} {student.lastName}
            </h1>
            <span className="font-mono text-xs bg-muted/60 text-muted-foreground px-2 py-0.5 rounded border border-border">
              {student.rollNumber}
            </span>
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[9px] font-bold border ${
              student.status === "ACTIVE" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-blue-500/10 text-blue-400 border-blue-500/20"
            }`}>
              {student.status}
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-muted-foreground pt-1.5">
            <div className="flex items-center gap-1.5">
              <Mail className="h-3.5 w-3.5 text-primary" /> {student.email}
            </div>
            {student.phone && (
              <div className="flex items-center gap-1.5">
                <Phone className="h-3.5 w-3.5 text-primary" /> {student.phone}
              </div>
            )}
            <div className="flex items-center gap-1.5">
              <CalendarDays className="h-3.5 w-3.5 text-primary" /> Adm: {new Date(student.admissionDate).toLocaleDateString()}
            </div>
          </div>
        </div>
      </div>

      {/* HORIZONTAL PROFILE TABS */}
      <div className="flex items-center gap-2 border-b border-border pb-2 overflow-x-auto scrollbar-thin select-none">
        <Button variant={activeTab === "summary" ? "primary" : "outline"} onClick={() => setActiveTab("summary")} className="text-xs font-semibold">
          <Contact className="mr-1.5 h-4 w-4" /> Personal Summary
        </Button>
        <Button variant={activeTab === "guardians" ? "primary" : "outline"} onClick={() => setActiveTab("guardians")} className="text-xs font-semibold">
          <UserCheck className="mr-1.5 h-4 w-4" /> Guardians
        </Button>
        <Button variant={activeTab === "documents" ? "primary" : "outline"} onClick={() => setActiveTab("documents")} className="text-xs font-semibold">
          <FileText className="mr-1.5 h-4 w-4" /> Documents
        </Button>
        <Button variant={activeTab === "achievements" ? "primary" : "outline"} onClick={() => setActiveTab("achievements")} className="text-xs font-semibold">
          <Award className="mr-1.5 h-4 w-4" /> Achievements
        </Button>
        <Button variant={activeTab === "skills" ? "primary" : "outline"} onClick={() => setActiveTab("skills")} className="text-xs font-semibold">
          <Layers className="mr-1.5 h-4 w-4" /> Skill Badges
        </Button>
      </div>

      {/* TAB PANELS */}

      {/* 1. SUMMARY TAB */}
      {activeTab === "summary" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Details details */}
          <Card className="lg:col-span-2 glass">
            <CardHeader>
              <CardTitle className="text-sm">Personal & Academic Specifications</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4 border-b border-border pb-3">
                <div>
                  <span className="text-muted-foreground">Gender Identity</span>
                  <p className="font-semibold text-foreground mt-0.5">{student.gender}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Date of Birth</span>
                  <p className="font-semibold text-foreground mt-0.5">{new Date(student.dateOfBirth).toLocaleDateString()}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 border-b border-border pb-3">
                <div>
                  <span className="text-muted-foreground">Blood Group Type</span>
                  <p className="font-semibold text-foreground mt-0.5">{student.bloodGroup || "Not Provided"}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Tags</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {student.tags.map((t, idx) => (
                      <span key={idx} className="bg-primary/10 text-primary border border-primary/20 px-2 py-0.5 rounded text-[10px] font-semibold">
                        {t}
                      </span>
                    ))}
                    {student.tags.length === 0 && <span className="italic text-[10px] text-muted-foreground">No tags mapped</span>}
                  </div>
                </div>
              </div>

              {/* Emergency info */}
              <div className="bg-primary/5 rounded-xl border border-primary/10 p-4">
                <h4 className="font-bold text-primary text-xs mb-2">Emergency Contacts Block</h4>
                {student.emergencyContact ? (
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <span className="text-muted-foreground">Primary Contact</span>
                      <p className="font-bold text-foreground mt-0.5">{student.emergencyContact.name} ({student.emergencyContact.relation})</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Emergency Telephone</span>
                      <p className="font-bold text-foreground mt-0.5">{student.emergencyContact.phone}</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-muted-foreground italic text-xs">No emergency contacts set yet.</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Academic notes sidebar */}
          <div className="flex flex-col gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Academic Advisement Notes</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="max-h-60 overflow-y-auto space-y-3 pr-1 text-xs">
                  {student.notes.map((note) => (
                    <div key={note.noteId} className="border border-border/80 p-2.5 rounded-xl bg-muted/20">
                      <div className="flex items-center justify-between text-[9px] text-muted-foreground">
                        <span className="font-bold text-primary">{note.author}</span>
                        <span>{new Date(note.createdAt).toLocaleDateString()}</span>
                      </div>
                      <p className="text-foreground mt-1 text-xs">{note.content}</p>
                    </div>
                  ))}
                  {student.notes.length === 0 && (
                    <p className="text-muted-foreground text-center italic text-xs py-4">No advisement logs entered.</p>
                  )}
                </div>

                {canWrite && (
                  <div className="space-y-2 border-t border-border pt-3">
                    <textarea
                      placeholder="Add an advisement log..."
                      value={noteContent}
                      onChange={(e) => setNoteContent(e.target.value)}
                      className="w-full text-xs bg-background border border-border rounded-xl p-2 h-16 focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <Button
                      size="sm"
                      onClick={() => {
                        if (noteContent.trim()) addNoteMutation.mutate(noteContent);
                      }}
                      className="w-full text-xs"
                      disabled={addNoteMutation.isPending}
                    >
                      Log Note
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* 2. GUARDIANS TAB */}
      {activeTab === "guardians" && (
        <div className="flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-sm text-foreground">Parents & Guardians</h3>
            {canWrite && (
              <Button size="sm" onClick={() => setGuardianModal(true)} className="text-xs">
                <Plus className="mr-1.5 h-4 w-4" /> Add Guardian
              </Button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {payload?.guardians.map((g) => (
              <Card key={g.id} className="relative overflow-hidden border border-border/80 bg-background hover:border-primary/40 transition-colors">
                <CardContent className="p-4 text-xs space-y-2.5">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-bold text-foreground text-sm flex items-center gap-1.5">
                        {g.name}
                        {g.isPrimary && (
                          <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[9px] font-bold">
                            PRIMARY
                          </span>
                        )}
                      </h4>
                      <p className="text-[10px] text-muted-foreground mt-0.5 uppercase tracking-wider">{g.relation}</p>
                    </div>

                    {canWrite && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          if (confirm(`Remove guardian ${g.name}?`)) {
                            deleteGuardianMutation.mutate(g.guardianId);
                          }
                        }}
                        className="h-8 text-destructive hover:bg-destructive/10 cursor-pointer"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>

                  <div className="space-y-1.5 text-muted-foreground border-t border-border/40 pt-2.5">
                    <p className="flex items-center gap-1.5"><Phone className="h-3.5 w-3.5" /> {g.phone}</p>
                    {g.email && <p className="flex items-center gap-1.5"><Mail className="h-3.5 w-3.5" /> {g.email}</p>}
                    {g.occupation && <p className="flex items-center gap-1.5"><Bookmark className="h-3.5 w-3.5" /> {g.occupation}</p>}
                  </div>
                </CardContent>
              </Card>
            ))}

            {payload?.guardians.length === 0 && (
              <div className="col-span-full border border-dashed border-border rounded-xl p-8 text-center text-xs text-muted-foreground">
                No guardians registered. Add parent contacts using the action above.
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3. DOCUMENTS TAB */}
      {activeTab === "documents" && (
        <div className="flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-sm text-foreground">Student Verification Documents</h3>
            {canWrite && (
              <Button size="sm" onClick={() => setDocModal(true)} className="text-xs">
                <Plus className="mr-1.5 h-4 w-4" /> Log Document
              </Button>
            )}
          </div>

          <Card className="glass">
            <CardContent className="p-0">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-border bg-muted/20 text-muted-foreground uppercase tracking-wider font-semibold">
                    <th className="py-3 px-4">Document Title</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4">Size</th>
                    <th className="py-3 px-4">Verification</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {payload?.documents.map((d) => (
                    <tr key={d.id} className="hover:bg-muted/5">
                      <td className="py-3.5 px-4 font-semibold text-foreground flex items-center gap-2">
                        <FileText className="h-4 w-4 text-primary" /> {d.name}
                      </td>
                      <td className="py-3.5 px-4 text-muted-foreground">{d.category}</td>
                      <td className="py-3.5 px-4 text-muted-foreground">{formatBytes(d.fileSize)}</td>
                      <td className="py-3.5 px-4">
                        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-bold border ${
                          d.isVerified 
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" 
                            : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                        }`}>
                          {d.isVerified ? (
                            <><CheckCircle2 className="h-3 w-3" /> VERIFIED</>
                          ) : (
                            <><Clock className="h-3 w-3" /> PENDING</>
                          )}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {user?.role?.permissions.includes("*") && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => verifyDocMutation.mutate({ docId: d.documentId, verified: !d.isVerified })}
                              className="h-8 text-primary hover:bg-primary/10 cursor-pointer"
                              title={d.isVerified ? "Mark Pending" : "Verify Document"}
                            >
                              <FileCheck2 className="h-4 w-4" />
                            </Button>
                          )}
                          {canWrite && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                if (confirm(`Delete document record ${d.name}?`)) {
                                  deleteDocMutation.mutate(d.documentId);
                                }
                              }}
                              className="h-8 text-destructive hover:bg-destructive/10 cursor-pointer"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {payload?.documents.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-muted-foreground italic">
                        No documents logged.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 4. ACHIEVEMENTS TAB */}
      {activeTab === "achievements" && (
        <div className="flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-sm text-foreground">Co-Curricular Achievements</h3>
            {canWrite && (
              <Button size="sm" onClick={() => setAchModal(true)} className="text-xs">
                <Plus className="mr-1.5 h-4 w-4" /> Add Achievement
              </Button>
            )}
          </div>

          <div className="relative border-l border-border pl-6 ml-4 space-y-6 py-2">
            {payload?.achievements.map((a) => (
              <div key={a.id} className="relative">
                {/* Timeline circle node */}
                <div className="absolute -left-[31px] top-1 bg-background border-2 border-primary h-4 w-4 rounded-full flex items-center justify-center" />
                
                <Card className="glass">
                  <CardContent className="p-4 text-xs space-y-2">
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-bold text-foreground text-sm flex items-center gap-2">
                          {a.title}
                          <span className="px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 text-[9px] font-bold">
                            {a.category}
                          </span>
                        </h4>
                        <p className="text-[10px] text-muted-foreground mt-0.5 flex items-center gap-1.5">
                          <Calendar className="h-3.5 w-3.5 text-primary" /> {new Date(a.dateEarned).toLocaleDateString()}
                        </p>
                      </div>

                      {canWrite && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            if (confirm(`Remove achievement ${a.title}?`)) {
                              deleteAchMutation.mutate(a.achievementId);
                            }
                          }}
                          className="h-8 text-destructive hover:bg-destructive/10 cursor-pointer"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                    {a.description && <p className="text-muted-foreground">{a.description}</p>}
                  </CardContent>
                </Card>
              </div>
            ))}

            {payload?.achievements.length === 0 && (
              <div className="border border-dashed border-border rounded-xl p-8 text-center text-xs text-muted-foreground ml-[-25px]">
                No achievement milestones registered.
              </div>
            )}
          </div>
        </div>
      )}

      {/* 5. SKILLS TAB */}
      {activeTab === "skills" && (
        <div className="flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-sm text-foreground">Skill Badges Registry</h3>
            {canWrite && (
              <Button size="sm" onClick={() => setSkillModal(true)} className="text-xs">
                <Plus className="mr-1.5 h-4 w-4" /> Add Skill
              </Button>
            )}
          </div>

          <div className="flex flex-wrap gap-3">
            {payload?.skills.map((k) => {
              const levelColors: Record<string, string> = {
                BEGINNER: "bg-blue-500/10 text-blue-400 border-blue-500/20",
                INTERMEDIATE: "bg-amber-500/10 text-amber-400 border-amber-500/20",
                ADVANCED: "bg-purple-500/10 text-purple-400 border-purple-500/20",
              };

              return (
                <div key={k.id} className="border border-border/80 bg-background rounded-xl p-3 flex items-center gap-3 text-xs font-semibold">
                  <div>
                    <p className="text-foreground">{k.name}</p>
                    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[9px] font-bold border mt-1.5 ${levelColors[k.level]}`}>
                      {k.level}
                    </span>
                  </div>

                  {canWrite && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteSkillMutation.mutate(k.skillId)}
                      className="h-8 text-destructive hover:bg-destructive/10 cursor-pointer flex-shrink-0"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              );
            })}

            {payload?.skills.length === 0 && (
              <div className="w-full border border-dashed border-border rounded-xl p-8 text-center text-xs text-muted-foreground">
                No skill badges logged yet.
              </div>
            )}
          </div>
        </div>
      )}

      {/* DIALOG MODALS */}

      {/* 1. ADD GUARDIAN */}
      <Dialog isOpen={guardianModal} onClose={() => setGuardianModal(false)} title="Add Guardian Info">
        <form onSubmit={gForm.handleSubmit((values: GuardianFormValues) => addGuardianMutation.mutate(values))} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">Name</label>
              <Input {...gForm.register("name")} placeholder="Alice Cooper" className="text-xs" />
              {gForm.formState.errors.name && <p className="text-[10px] text-rose-400">{gForm.formState.errors.name.message}</p>}
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">Relation</label>
              <Input {...gForm.register("relation")} placeholder="e.g. MOTHER" className="text-xs" />
              {gForm.formState.errors.relation && <p className="text-[10px] text-rose-400">{gForm.formState.errors.relation.message}</p>}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">Phone</label>
              <Input {...gForm.register("phone")} placeholder="+1 555 1234" className="text-xs" />
              {gForm.formState.errors.phone && <p className="text-[10px] text-rose-400">{gForm.formState.errors.phone.message}</p>}
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">Email</label>
              <Input {...gForm.register("email")} placeholder="parent@mail.com" className="text-xs" />
            </div>
          </div>

          <div className="flex items-center gap-2 mt-2">
            <input type="checkbox" {...gForm.register("isPrimary")} id="chkPrimary" className="rounded" />
            <label htmlFor="chkPrimary" className="text-xs text-muted-foreground select-none">Set as Primary Emergency Contact</label>
          </div>

          <div className="flex items-center justify-end gap-2 border-t border-border pt-4 mt-4">
            <Button variant="outline" size="sm" type="button" onClick={() => setGuardianModal(false)} className="text-xs">
              Cancel
            </Button>
            <Button size="sm" type="submit" disabled={addGuardianMutation.isPending} className="text-xs">
              Save Contact
            </Button>
          </div>
        </form>
      </Dialog>

      {/* 2. LOG DOCUMENT */}
      <Dialog isOpen={docModal} onClose={() => setDocModal(false)} title="Register Verification Document">
        <form onSubmit={dForm.handleSubmit((values: DocFormValues) => addDocMutation.mutate(values))} className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground font-semibold">Document Title</label>
            <Input {...dForm.register("name")} placeholder="e.g. 10th Standard Marksheet" className="text-xs" />
            {dForm.formState.errors.name && <p className="text-[10px] text-rose-400">{dForm.formState.errors.name.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">Document Category</label>
              <select
                {...dForm.register("category")}
                className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none"
              >
                <option value="ACADEMIC">Academic Transcript</option>
                <option value="IDENTITY">Identity Verification</option>
                <option value="MEDICAL">Medical Record</option>
                <option value="OTHER">Other Attachment</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">Mock S3 file path</label>
              <Input {...dForm.register("filePath")} className="text-xs" />
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 border-t border-border pt-4 mt-4">
            <Button variant="outline" size="sm" type="button" onClick={() => setDocModal(false)} className="text-xs">
              Cancel
            </Button>
            <Button size="sm" type="submit" disabled={addDocMutation.isPending} className="text-xs">
              Log Document
            </Button>
          </div>
        </form>
      </Dialog>

      {/* 3. ADD ACHIEVEMENT */}
      <Dialog isOpen={achModal} onClose={() => setAchModal(false)} title="Add Achievement Milestone">
        <form onSubmit={aForm.handleSubmit((values: AchFormValues) => addAchMutation.mutate(values))} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">Achievement Title</label>
              <Input {...aForm.register("title")} placeholder="e.g. Hackathon Winner" className="text-xs" />
              {aForm.formState.errors.title && <p className="text-[10px] text-rose-400">{aForm.formState.errors.title.message}</p>}
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">Date Earned</label>
              <Input {...aForm.register("dateEarned")} type="date" className="text-xs" />
              {aForm.formState.errors.dateEarned && <p className="text-[10px] text-rose-400">{aForm.formState.errors.dateEarned.message}</p>}
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground font-semibold">Category</label>
            <select
              {...aForm.register("category")}
              className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none"
            >
              <option value="ACADEMIC">Academic</option>
              <option value="SPORTS">Sports</option>
              <option value="CULTURAL">Cultural</option>
              <option value="OTHER">Other</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground font-semibold">Brief Description</label>
            <Input {...aForm.register("description")} placeholder="Won first place out of 40 regional collegiate entries." className="text-xs" />
          </div>

          <div className="flex items-center justify-end gap-2 border-t border-border pt-4 mt-4">
            <Button variant="outline" size="sm" type="button" onClick={() => setAchModal(false)} className="text-xs">
              Cancel
            </Button>
            <Button size="sm" type="submit" disabled={addAchMutation.isPending} className="text-xs">
              Save Achievement
            </Button>
          </div>
        </form>
      </Dialog>

      {/* 4. ADD SKILL */}
      <Dialog isOpen={skillModal} onClose={() => setSkillModal(false)} title="Add Skill Badge">
        <form onSubmit={sForm.handleSubmit((values: SkillFormValues) => addSkillMutation.mutate(values))} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">Skill Name</label>
              <Input {...sForm.register("name")} placeholder="e.g. React" className="text-xs" />
              {sForm.formState.errors.name && <p className="text-[10px] text-rose-400">{sForm.formState.errors.name.message}</p>}
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground font-semibold">Proficiency Level</label>
              <select
                {...sForm.register("level")}
                className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none"
              >
                <option value="BEGINNER">Beginner</option>
                <option value="INTERMEDIATE">Intermediate</option>
                <option value="ADVANCED">Advanced</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 border-t border-border pt-4 mt-4">
            <Button variant="outline" size="sm" type="button" onClick={() => setSkillModal(false)} className="text-xs">
              Cancel
            </Button>
            <Button size="sm" type="submit" disabled={addSkillMutation.isPending} className="text-xs">
              Add Badge
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
