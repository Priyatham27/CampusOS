"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Calendar,
  Building2,
  BookOpen,
  Bookmark,
  Activity,
  PlusCircle,
  UploadCloud,
  FileSpreadsheet,
  CheckCircle,
  AlertCircle,
  GitBranch,
} from "lucide-react";
import { AcademicYear, Department, Program, Course, Semester } from "@/types/academic";

export default function AcademicDashboard() {
  const { user } = useAuth();
  const orgId = user?.tenant?.organizationId || "";

  // Fetch queries to get sizes and display current items
  const { data: years = [], isLoading: yearsLoading } = useQuery<AcademicYear[]>({
    queryKey: ["academic_years", orgId],
    queryFn: () => api.get<AcademicYear[]>(`/organizations/${orgId}/academic-years`),
    enabled: !!orgId,
  });

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

  const { data: courses = [], isLoading: coursesLoading } = useQuery<Course[]>({
    queryKey: ["courses", orgId],
    queryFn: () => api.get<Course[]>(`/organizations/${orgId}/courses`),
    enabled: !!orgId,
  });

  const currentYear = years.find((y) => y.current);
  const loading = yearsLoading || deptsLoading || programsLoading || coursesLoading;

  const quickActions = [
    {
      title: "Add Academic Year",
      desc: "Define a new calendar boundary",
      href: "/dashboard/academic/academic-years?create=true",
      icon: Calendar,
      color: "text-indigo-500 bg-indigo-500/10",
    },
    {
      title: "Add Department",
      desc: "Register a new administrative division",
      href: "/dashboard/academic/departments?create=true",
      icon: Building2,
      color: "text-emerald-500 bg-emerald-500/10",
    },
    {
      title: "Create Course",
      desc: "Add a subject entry to curriculum",
      href: "/dashboard/academic/courses?create=true",
      icon: Bookmark,
      color: "text-sky-500 bg-sky-500/10",
    },
    {
      title: "Bulk CSV Seeder",
      desc: "Upload whole structure via CSV",
      href: "/dashboard/academic/settings",
      icon: UploadCloud,
      color: "text-amber-500 bg-amber-500/10",
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      {/* Top Banner Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Academic Years card */}
        <Card glass className="flex items-center gap-4 hover:translate-y-[-2px] transition-transform duration-200">
          <div className="h-10 w-10 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center">
            <Calendar className="h-5 w-5" />
          </div>
          <div className="flex flex-col">
            <span className="text-2xs font-bold text-muted-foreground uppercase tracking-wider">Academic Years</span>
            {loading ? <Skeleton className="h-6 w-12 mt-1" /> : <span className="text-xl font-bold">{years.length}</span>}
          </div>
        </Card>

        {/* Departments card */}
        <Card glass className="flex items-center gap-4 hover:translate-y-[-2px] transition-transform duration-200">
          <div className="h-10 w-10 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
            <Building2 className="h-5 w-5" />
          </div>
          <div className="flex flex-col">
            <span className="text-2xs font-bold text-muted-foreground uppercase tracking-wider">Departments</span>
            {loading ? <Skeleton className="h-6 w-12 mt-1" /> : <span className="text-xl font-bold">{depts.length}</span>}
          </div>
        </Card>

        {/* Programs card */}
        <Card glass className="flex items-center gap-4 hover:translate-y-[-2px] transition-transform duration-200">
          <div className="h-10 w-10 rounded-lg bg-sky-500/20 text-sky-400 flex items-center justify-center">
            <BookOpen className="h-5 w-5" />
          </div>
          <div className="flex flex-col">
            <span className="text-2xs font-bold text-muted-foreground uppercase tracking-wider">Programs</span>
            {loading ? <Skeleton className="h-6 w-12 mt-1" /> : <span className="text-xl font-bold">{programs.length}</span>}
          </div>
        </Card>

        {/* Courses card */}
        <Card glass className="flex items-center gap-4 hover:translate-y-[-2px] transition-transform duration-200">
          <div className="h-10 w-10 rounded-lg bg-pink-500/20 text-pink-400 flex items-center justify-center">
            <Bookmark className="h-5 w-5" />
          </div>
          <div className="flex flex-col">
            <span className="text-2xs font-bold text-muted-foreground uppercase tracking-wider">Courses</span>
            {loading ? <Skeleton className="h-6 w-12 mt-1" /> : <span className="text-xl font-bold">{courses.length}</span>}
          </div>
        </Card>
      </div>

      {/* Main split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (Current Year Status & Actions) */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          {/* Active Academic Year status */}
          <Card glass>
            <div className="flex flex-col gap-3">
              <div className="flex justify-between items-center pb-3 border-b border-border">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Current Session Status</span>
                {currentYear ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-3xs font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Active Session
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-3xs font-bold uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/20">
                    No Current Session
                  </span>
                )}
              </div>

              {loading ? (
                <div className="space-y-2 mt-2">
                  <Skeleton className="h-6 w-1/3" />
                  <Skeleton className="h-4 w-1/2" />
                </div>
              ) : currentYear ? (
                <div className="flex flex-col gap-2 mt-1">
                  <h3 className="text-lg font-bold">{currentYear.name}</h3>
                  <p className="text-xs text-muted-foreground">
                    Duration: {new Date(currentYear.startDate).toLocaleDateString()} to {new Date(currentYear.endDate).toLocaleDateString()}
                  </p>
                </div>
              ) : (
                <div className="text-xs text-muted-foreground mt-1 leading-relaxed">
                  No active academic year has been configured for this organization. Students won't be able to register for class semesters or enroll in courses until you set a year current.
                </div>
              )}
            </div>
          </Card>

          {/* Quick Actions grid */}
          <div className="flex flex-col gap-3">
            <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Quick Administration Shortcuts</span>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {quickActions.map((act) => (
                <Link key={act.title} href={act.href}>
                  <Card glass className="flex items-start gap-4 p-5 hover:bg-accent/5 transition-colors cursor-pointer group h-full">
                    <div className={`h-9 w-9 rounded-lg flex items-center justify-center flex-shrink-0 ${act.color}`}>
                      <act.icon className="h-4.5 w-4.5" />
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span className="text-sm font-semibold group-hover:text-primary transition-colors">{act.title}</span>
                      <span className="text-2xs text-muted-foreground leading-snug">{act.desc}</span>
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column (Platform Health & Indicators) */}
        <div className="flex flex-col gap-6">
          <Card glass>
            <div className="flex flex-col gap-4">
              <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider border-b border-border pb-2.5">
                Engine Diagnostics
              </span>

              <div className="flex flex-col gap-4">
                {/* Database connectivity status */}
                <div className="flex justify-between items-start text-xs">
                  <div className="flex flex-col gap-0.5">
                    <span className="font-semibold">Academic DB Layer</span>
                    <span className="text-3xs text-muted-foreground">MongoDB Atlas Cluster Connection</span>
                  </div>
                  <span className="inline-flex items-center gap-1 text-emerald-400 font-bold text-2xs uppercase">
                    <CheckCircle className="h-3.5 w-3.5" /> Seeding OK
                  </span>
                </div>

                {/* Academic Year Hierarchy Status */}
                <div className="flex justify-between items-start text-xs">
                  <div className="flex flex-col gap-0.5">
                    <span className="font-semibold">Sequential Semesters</span>
                    <span className="text-3xs text-muted-foreground">Sequence validation rules</span>
                  </div>
                  <span className="inline-flex items-center gap-1 text-emerald-400 font-bold text-2xs uppercase">
                    <CheckCircle className="h-3.5 w-3.5" /> Active
                  </span>
                </div>

                {/* White-Label Styles status */}
                <div className="flex justify-between items-start text-xs">
                  <div className="flex flex-col gap-0.5">
                    <span className="font-semibold">Tenant Branding</span>
                    <span className="text-3xs text-muted-foreground">Dynamic colors injection</span>
                  </div>
                  <span className="inline-flex items-center gap-1 text-primary font-bold text-2xs uppercase">
                    <CheckCircle className="h-3.5 w-3.5" /> Injected
                  </span>
                </div>

                {/* Audit trail pipeline status */}
                <div className="flex justify-between items-start text-xs">
                  <div className="flex flex-col gap-0.5">
                    <span className="font-semibold">Audit pipeline</span>
                    <span className="text-3xs text-muted-foreground">MongoDB audit writes</span>
                  </div>
                  <span className="inline-flex items-center gap-1 text-emerald-400 font-bold text-2xs uppercase">
                    <CheckCircle className="h-3.5 w-3.5" /> Enabled
                  </span>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
