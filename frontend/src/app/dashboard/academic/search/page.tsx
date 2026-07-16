"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Search,
  Building2,
  BookOpen,
  GitBranch,
  Layers,
  Grid,
  Bookmark,
  ArrowRight,
} from "lucide-react";
import { Department, Program, Branch, Semester, Section, Course } from "@/types/academic";

interface SearchResult {
  id: string;
  type: "department" | "program" | "branch" | "semester" | "section" | "course";
  title: string;
  subtitle: string;
  code?: string;
  lineage?: string;
}

export default function AcademicSearchPage() {
  const { user } = useAuth();
  const orgId = user?.tenant?.organizationId || "";

  const [query, setQuery] = useState("");

  // Fetch all lists for local indexing & fast responsive lookup
  const { data: depts = [], isLoading: deptsLoading } = useQuery<Department[]>({
    queryKey: ["departments", orgId],
    queryFn: () => api.get<Department[]>(`/organizations/${orgId}/departments`),
    enabled: !!orgId,
  });

  const { data: programs = [], isLoading: programsLoading } = useQuery<Program[]>({
    queryKey: ["programs", orgId],
    queryFn: () => api.get<Program[]>(`/organizations/${orgId}/programs`),
    enabled: !!orgId,
  });

  const { data: branches = [], isLoading: branchesLoading } = useQuery<Branch[]>({
    queryKey: ["branches", orgId],
    queryFn: () => api.get<Branch[]>(`/organizations/${orgId}/branches`),
    enabled: !!orgId,
  });

  const { data: semesters = [], isLoading: semestersLoading } = useQuery<Semester[]>({
    queryKey: ["semesters", orgId],
    queryFn: () => api.get<Semester[]>(`/organizations/${orgId}/semesters`),
    enabled: !!orgId,
  });

  const { data: sections = [], isLoading: sectionsLoading } = useQuery<Section[]>({
    queryKey: ["sections", orgId],
    queryFn: () => api.get<Section[]>(`/organizations/${orgId}/sections`),
    enabled: !!orgId,
  });

  const { data: courses = [], isLoading: coursesLoading } = useQuery<Course[]>({
    queryKey: ["courses", orgId],
    queryFn: () => api.get<Course[]>(`/organizations/${orgId}/courses`),
    enabled: !!orgId,
  });

  const loading = deptsLoading || programsLoading || branchesLoading || semestersLoading || sectionsLoading || coursesLoading;

  // Build searchable index items
  const results: SearchResult[] = [];

  depts.forEach((d) => {
    results.push({
      id: d.departmentId,
      type: "department",
      title: d.name,
      subtitle: d.hod ? `HoD: ${d.hod}` : "No Head assigned",
      code: d.code,
    });
  });

  programs.forEach((p) => {
    const dept = depts.find((d) => d.id === p.departmentId);
    results.push({
      id: p.programId,
      type: "program",
      title: p.name,
      subtitle: `${p.level} • ${p.duration} Years`,
      lineage: dept ? `Dept: ${dept.name}` : undefined,
    });
  });

  branches.forEach((b) => {
    const dept = depts.find((d) => d.id === b.departmentId);
    results.push({
      id: b.branchId,
      type: "branch",
      title: b.name,
      subtitle: `Affiliated Specialization`,
      code: b.code,
      lineage: dept ? `Dept: ${dept.name}` : undefined,
    });
  });

  semesters.forEach((s) => {
    results.push({
      id: s.semesterId,
      type: "semester",
      title: s.name,
      subtitle: `Sequence Position #${s.number}`,
    });
  });

  sections.forEach((s) => {
    const branch = branches.find((b) => b.id === s.branchId);
    const sem = semesters.find((se) => se.id === s.semesterId);
    results.push({
      id: s.sectionId,
      type: "section",
      title: `Section ${s.name}`,
      subtitle: `Capacity: ${s.strength} Seats`,
      lineage: [branch?.name, sem?.name].filter(Boolean).join(" • "),
    });
  });

  courses.forEach((c) => {
    const prog = programs.find((p) => p.id === c.programId);
    results.push({
      id: c.courseId,
      type: "course",
      title: c.name,
      subtitle: `${c.credits} Credits • ${c.semester}`,
      code: c.courseCode,
      lineage: prog ? `Program: ${prog.name}` : undefined,
    });
  });

  // Filter items matching query
  const searchResults = query.trim()
    ? results.filter(
        (r) =>
          r.title.toLowerCase().includes(query.toLowerCase()) ||
          r.subtitle.toLowerCase().includes(query.toLowerCase()) ||
          r.code?.toLowerCase().includes(query.toLowerCase()) ||
          r.lineage?.toLowerCase().includes(query.toLowerCase())
      )
    : results.slice(0, 15); // Show first 15 by default

  const iconsMap = {
    department: Building2,
    program: BookOpen,
    branch: GitBranch,
    semester: Layers,
    section: Grid,
    course: Bookmark,
  };

  const colorsMap = {
    department: "bg-emerald-500/10 text-emerald-400",
    program: "bg-sky-500/10 text-sky-400",
    branch: "bg-pink-500/10 text-pink-400",
    semester: "bg-indigo-500/10 text-indigo-400",
    section: "bg-violet-500/10 text-violet-400",
    course: "bg-amber-500/10 text-amber-400",
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Central Input search box */}
      <div className="relative w-full max-w-2xl mx-auto">
        <Search className="absolute left-4 top-3.5 h-5 w-5 text-muted-foreground" />
        <input
          type="text"
          placeholder="Global academic lookup (Type course codes, department names, sections)..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full h-12 rounded-xl bg-accent/10 border border-input pl-12 pr-4 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-0 placeholder:text-muted-foreground transition-all duration-200 shadow-lg"
        />
      </div>

      {/* Results Display */}
      <div className="max-w-2xl w-full mx-auto flex flex-col gap-3">
        <span className="text-3xs font-bold uppercase tracking-widest text-muted-foreground border-b border-border pb-1.5 mb-1">
          {query ? `Search Results (${searchResults.length})` : "Default Overview"}
        </span>

        {loading ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-14 w-full rounded-xl" />
            <Skeleton className="h-14 w-full rounded-xl" />
            <Skeleton className="h-14 w-full rounded-xl" />
          </div>
        ) : searchResults.length === 0 ? (
          <EmptyState
            title="No Results Found"
            description="We couldn't find any academic records matching your terms."
          />
        ) : (
          <div className="flex flex-col gap-3">
            {searchResults.map((res) => {
              const Icon = iconsMap[res.type];
              const colorClass = colorsMap[res.type];

              return (
                <Card
                  key={`${res.type}-${res.id}`}
                  glass
                  className="flex items-center justify-between p-4 hover:bg-accent/5 transition-all duration-200 group"
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className={`h-9 w-9 rounded-xl flex items-center justify-center flex-shrink-0 ${colorClass}`}>
                      <Icon className="h-4.5 w-4.5" />
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="text-xs uppercase font-bold text-muted-foreground tracking-wide leading-none mb-1">
                        {res.type} {res.code && `• ${res.code}`}
                      </span>
                      <span className="text-sm font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                        {res.title}
                      </span>
                      <span className="text-2xs text-muted-foreground mt-0.5">{res.subtitle}</span>
                    </div>
                  </div>

                  {res.lineage && (
                    <div className="flex items-center gap-1 text-2xs text-muted-foreground/60 font-semibold uppercase tracking-wider ml-4 flex-shrink-0">
                      <span>{res.lineage}</span>
                      <ArrowRight className="h-3 w-3" />
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
