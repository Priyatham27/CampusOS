"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
import EmptyState from "@/components/ui/empty-state";
import { useToast } from "@/components/ui/toast";
import {
  Calendar as CalendarIcon,
  Plus,
  Trash2,
  CalendarCheck2,
  Clock,
  Download,
  AlertTriangle,
  Sparkles,
  Info,
  CalendarRange,
  UserCheck,
  Layers,
  CheckCircle
} from "lucide-react";
import {
  AcademicCalendar,
  AcademicYearTimeline,
  SemesterTimeline,
  Holiday,
  WorkingDay,
  SchedulingWindow,
  CalendarEvent,
  UnifiedTimeline,
  WindowType
} from "@/types/calendar";
import { AcademicYear, Semester } from "@/types/academic";

// Schema validations
const calendarSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  timezone: z.string().min(1, "Timezone is required"),
  weeklyWorkingDays: z.array(z.number()).min(1, "Select at least one working day"),
});

const yearTimelineSchema = z.object({
  calendarId: z.string().min(1, "Calendar is required"),
  academicYearId: z.string().min(1, "Academic Year is required"),
  startDate: z.string().min(1, "Start Date is required"),
  endDate: z.string().min(1, "End Date is required"),
  status: z.string(),
});

const semesterTimelineSchema = z.object({
  academicYearTimelineId: z.string().min(1, "Academic Year Timeline is required"),
  semesterId: z.string().min(1, "Semester is required"),
  startDate: z.string().min(1, "Start Date is required"),
  endDate: z.string().min(1, "End Date is required"),
  status: z.string(),
});

const holidaySchema = z.object({
  calendarId: z.string().min(1, "Calendar is required"),
  name: z.string().min(2, "Name must be at least 2 characters"),
  date: z.string().min(1, "Date is required"),
  type: z.enum(["PUBLIC", "RESTRICTED", "INSTITUTIONAL"]),
  description: z.string().optional(),
});

const workingDaySchema = z.object({
  calendarId: z.string().min(1, "Calendar is required"),
  date: z.string().min(1, "Date is required"),
  description: z.string().optional(),
});

const windowSchema = z.object({
  calendarId: z.string().min(1, "Calendar is required"),
  semesterTimelineId: z.string().optional(),
  windowType: z.enum(["REGISTRATION", "EXAMINATION", "GRADING", "CERTIFICATE", "ADMISSION"]),
  activityType: z.string().min(1, "Activity Type is required"),
  name: z.string().min(2, "Name must be at least 2 characters"),
  startDate: z.string().min(1, "Start Date is required"),
  endDate: z.string().min(1, "End Date is required"),
  isActive: z.boolean(),
});

const eventSchema = z.object({
  calendarId: z.string().min(1, "Calendar is required"),
  name: z.string().min(2, "Name must be at least 2 characters"),
  startDate: z.string().min(1, "Start Date is required"),
  endDate: z.string().min(1, "End Date is required"),
  description: z.string().optional(),
  category: z.enum(["ACADEMIC", "EXAM", "CULTURAL", "SPORTS", "HOLIDAY", "OTHER"]),
});

type CalendarFormValues = z.infer<typeof calendarSchema>;
type YearTimelineFormValues = z.infer<typeof yearTimelineSchema>;
type SemesterTimelineFormValues = z.infer<typeof semesterTimelineSchema>;
type HolidayFormValues = z.infer<typeof holidaySchema>;
type WorkingDayFormValues = z.infer<typeof workingDaySchema>;
type WindowFormValues = z.infer<typeof windowSchema>;
type EventFormValues = z.infer<typeof eventSchema>;

export default function AcademicCalendarDashboard() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const orgId = user?.tenant?.organizationId || "";
  const { success, error: toastError } = useToast();

  // Tabs state
  const [activeTab, setActiveTab] = useState<"overview" | "timelines" | "exceptions" | "windows" | "events" | "checker">("overview");

  // Modals state
  const [calModalOpen, setCalModalOpen] = useState(false);
  const [yearTimelineModalOpen, setYearTimelineModalOpen] = useState(false);
  const [semTimelineModalOpen, setSemTimelineModalOpen] = useState(false);
  const [holidayModalOpen, setHolidayModalOpen] = useState(false);
  const [wkdModalOpen, setWkdModalOpen] = useState(false);
  const [windowModalOpen, setWindowModalOpen] = useState(false);
  const [eventModalOpen, setEventModalOpen] = useState(false);

  // Checker inputs
  const [checkWindowType, setCheckWindowType] = useState<WindowType>("REGISTRATION");
  const [checkActivityType, setCheckActivityType] = useState("COURSES");
  const [checkDateVal, setCheckDateVal] = useState("");
  const [checkedResult, setCheckedResult] = useState<boolean | null>(null);

  // Zod forms binding
  const calForm = useForm<CalendarFormValues>({
    resolver: zodResolver(calendarSchema),
    defaultValues: { name: "", timezone: "UTC", weeklyWorkingDays: [0, 1, 2, 3, 4] }
  });

  const yearTimelineForm = useForm<YearTimelineFormValues>({
    resolver: zodResolver(yearTimelineSchema),
    defaultValues: { calendarId: "", academicYearId: "", startDate: "", endDate: "", status: "ACTIVE" }
  });

  const semTimelineForm = useForm<SemesterTimelineFormValues>({
    resolver: zodResolver(semesterTimelineSchema),
    defaultValues: { academicYearTimelineId: "", semesterId: "", startDate: "", endDate: "", status: "ACTIVE" }
  });

  const holidayForm = useForm<HolidayFormValues>({
    resolver: zodResolver(holidaySchema),
    defaultValues: { calendarId: "", name: "", date: "", type: "PUBLIC", description: "" }
  });

  const wkdForm = useForm<WorkingDayFormValues>({
    resolver: zodResolver(workingDaySchema),
    defaultValues: { calendarId: "", date: "", description: "" }
  });

  const windowForm = useForm<WindowFormValues>({
    resolver: zodResolver(windowSchema),
    defaultValues: { calendarId: "", semesterTimelineId: "", windowType: "REGISTRATION", activityType: "", name: "", startDate: "", endDate: "", isActive: true }
  });

  const eventForm = useForm<EventFormValues>({
    resolver: zodResolver(eventSchema),
    defaultValues: { calendarId: "", name: "", startDate: "", endDate: "", description: "", category: "ACADEMIC" }
  });

  // Queries
  const { data: calendars = [], isLoading: calLoading } = useQuery<AcademicCalendar[]>({
    queryKey: ["calendars", orgId],
    queryFn: () => api.get<AcademicCalendar[]>(`/organizations/${orgId}/calendars`),
    enabled: !!orgId,
  });

  const { data: unified, isLoading: uniLoading } = useQuery<UnifiedTimeline>({
    queryKey: ["unified_timeline", orgId],
    queryFn: () => api.get<UnifiedTimeline>(`/organizations/${orgId}/timeline`),
    enabled: !!orgId,
  });

  const { data: academicYears = [] } = useQuery<AcademicYear[]>({
    queryKey: ["academic_years", orgId],
    queryFn: () => api.get<AcademicYear[]>(`/organizations/${orgId}/academic-years`),
    enabled: !!orgId,
  });

  const { data: semesters = [] } = useQuery<Semester[]>({
    queryKey: ["semesters", orgId],
    queryFn: () => api.get<Semester[]>(`/organizations/${orgId}/semesters`),
    enabled: !!orgId,
  });

  const { data: yearTimelines = [] } = useQuery<AcademicYearTimeline[]>({
    queryKey: ["academic_year_timelines", orgId],
    queryFn: () => api.get<AcademicYearTimeline[]>(`/organizations/${orgId}/academic-year-timelines`),
    enabled: !!orgId,
  });

  // Mutations
  const createCalMutation = useMutation({
    mutationFn: (data: CalendarFormValues) =>
      api.post<AcademicCalendar>(`/organizations/${orgId}/calendars`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calendars", orgId] });
      queryClient.invalidateQueries({ queryKey: ["unified_timeline", orgId] });
      success("Calendar Created", "A new academic calendar template has been created.");
      setCalModalOpen(false);
      calForm.reset();
    },
    onError: (err: any) => toastError("Error Creating Calendar", err?.detail || "Invalid schema data")
  });

  const activateCalMutation = useMutation({
    mutationFn: (id: string) =>
      api.post<AcademicCalendar>(`/organizations/${orgId}/calendars/${id}/activate`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calendars", orgId] });
      queryClient.invalidateQueries({ queryKey: ["unified_timeline", orgId] });
      success("Calendar Activated", "Authoritative calendar context set successfully.");
    },
    onError: (err: any) => toastError("Activation Failed", err?.detail || "Operation failed")
  });

  const deleteCalMutation = useMutation({
    mutationFn: (id: string) =>
      api.delete(`/organizations/${orgId}/calendars/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calendars", orgId] });
      queryClient.invalidateQueries({ queryKey: ["unified_timeline", orgId] });
      success("Calendar Deleted", "Academic calendar soft deleted.");
    },
    onError: (err: any) => toastError("Deletion Failed", err?.detail || "Operation failed")
  });

  const createYearTimelineMutation = useMutation({
    mutationFn: (data: YearTimelineFormValues) => {
      const payload = {
        ...data,
        startDate: new Date(data.startDate).toISOString(),
        endDate: new Date(data.endDate).toISOString(),
      };
      return api.post<AcademicYearTimeline>(`/organizations/${orgId}/academic-year-timelines`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academic_year_timelines", orgId] });
      queryClient.invalidateQueries({ queryKey: ["unified_timeline", orgId] });
      success("Year Timeline Created", "Academic year timeline registered successfully.");
      setYearTimelineModalOpen(false);
      yearTimelineForm.reset();
    },
    onError: (err: any) => toastError("Failed to Config", err?.detail || "Date boundary conflict.")
  });

  const deleteYearTimelineMutation = useMutation({
    mutationFn: (id: string) =>
      api.delete(`/organizations/${orgId}/academic-year-timelines/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academic_year_timelines", orgId] });
      queryClient.invalidateQueries({ queryKey: ["unified_timeline", orgId] });
      success("Timeline Removed", "Academic Year timeline deleted.");
    },
    onError: (err: any) => toastError("Delete Failed", err?.detail || "Check child timelines dependencies.")
  });

  const createSemTimelineMutation = useMutation({
    mutationFn: (data: SemesterTimelineFormValues) => {
      const payload = {
        ...data,
        startDate: new Date(data.startDate).toISOString(),
        endDate: new Date(data.endDate).toISOString(),
      };
      return api.post<SemesterTimeline>(`/organizations/${orgId}/semester-timelines`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["unified_timeline", orgId] });
      success("Semester Timeline Added", "Semester limits defined without overlaps.");
      setSemTimelineModalOpen(false);
      semTimelineForm.reset();
    },
    onError: (err: any) => toastError("Timeline Conflict", err?.detail || "Overlaps detected.")
  });

  const deleteSemTimelineMutation = useMutation({
    mutationFn: (id: string) =>
      api.delete(`/organizations/${orgId}/semester-timelines/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["unified_timeline", orgId] });
      success("Timeline Removed", "Semester timeline soft deleted.");
    },
    onError: (err: any) => toastError("Failed", err?.detail || "Could not delete.")
  });

  const createHolidayMutation = useMutation({
    mutationFn: (data: HolidayFormValues) => {
      const payload = { ...data, date: new Date(data.date).toISOString() };
      return api.post<Holiday>(`/organizations/${orgId}/holidays`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["unified_timeline", orgId] });
      success("Holiday Registered", "Holiday exception added.");
      setHolidayModalOpen(false);
      holidayForm.reset();
    },
    onError: (err: any) => toastError("Failed", err?.detail || "Invalid date parameters.")
  });

  const deleteHolidayMutation = useMutation({
    mutationFn: (id: string) =>
      api.delete(`/organizations/${orgId}/holidays/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["unified_timeline", orgId] });
      success("Holiday Deleted", "Removed from calendar context.");
    },
    onError: (err: any) => toastError("Failed", err?.detail || "Failed to remove.")
  });

  const createWkdMutation = useMutation({
    mutationFn: (data: WorkingDayFormValues) => {
      const payload = { ...data, date: new Date(data.date).toISOString() };
      return api.post<WorkingDay>(`/organizations/${orgId}/working-days`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["unified_timeline", orgId] });
      success("Working Day Override Configured", "Compensation weekend set as active working day.");
      setWkdModalOpen(false);
      wkdForm.reset();
    },
    onError: (err: any) => toastError("Failed", err?.detail || "Duplicate exception date.")
  });

  const deleteWkdMutation = useMutation({
    mutationFn: (id: string) =>
      api.delete(`/organizations/${orgId}/working-days/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["unified_timeline", orgId] });
      success("Working day deleted", "Restored standard weekend rules.");
    },
    onError: (err: any) => toastError("Failed", err?.detail || "Failed to delete.")
  });

  const createWindowMutation = useMutation({
    mutationFn: (data: WindowFormValues) => {
      const payload = {
        ...data,
        startDate: new Date(data.startDate).toISOString(),
        endDate: new Date(data.endDate).toISOString(),
        semesterTimelineId: data.semesterTimelineId || undefined
      };
      return api.post<SchedulingWindow>(`/organizations/${orgId}/scheduling-windows`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["unified_timeline", orgId] });
      success("Scheduling Window Defined", "Active registration/examination limits configured.");
      setWindowModalOpen(false);
      windowForm.reset();
    },
    onError: (err: any) => toastError("Window Conflict", err?.detail || "Conflict for similar activity overlaps.")
  });

  const deleteWindowMutation = useMutation({
    mutationFn: (id: string) =>
      api.delete(`/organizations/${orgId}/scheduling-windows/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["unified_timeline", orgId] });
      success("Scheduling Window Deleted", "Removed scheduling restrictions.");
    },
    onError: (err: any) => toastError("Failed", err?.detail || "Could not delete.")
  });

  const createEventMutation = useMutation({
    mutationFn: (data: EventFormValues) => {
      const payload = {
        ...data,
        startDate: new Date(data.startDate).toISOString(),
        endDate: new Date(data.endDate).toISOString(),
      };
      return api.post<CalendarEvent>(`/organizations/${orgId}/calendar-events`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["unified_timeline", orgId] });
      success("Event Created", "New academic schedule activity registered.");
      setEventModalOpen(false);
      eventForm.reset();
    },
    onError: (err: any) => toastError("Failed", err?.detail || "Failed to create.")
  });

  const deleteEventMutation = useMutation({
    mutationFn: (id: string) =>
      api.delete(`/organizations/${orgId}/calendar-events/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["unified_timeline", orgId] });
      success("Event Deleted", "Activity removed from agenda.");
    },
    onError: (err: any) => toastError("Failed", err?.detail || "Could not delete.")
  });

  // Typed onSubmit Handlers
  const onCalSubmit = (data: CalendarFormValues) => createCalMutation.mutate(data);
  const onYearTimelineSubmit = (data: YearTimelineFormValues) => createYearTimelineMutation.mutate(data);
  const onSemTimelineSubmit = (data: SemesterTimelineFormValues) => createSemTimelineMutation.mutate(data);
  const onHolidaySubmit = (data: HolidayFormValues) => createHolidayMutation.mutate(data);
  const onWkdSubmit = (data: WorkingDayFormValues) => createWkdMutation.mutate(data);
  const onWindowSubmit = (data: WindowFormValues) => createWindowMutation.mutate(data);
  const onEventSubmit = (data: EventFormValues) => createEventMutation.mutate(data);

  // Export ICS
  const handleExportICS = async () => {
    try {
      window.open(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/organizations/${orgId}/timeline/export`, "_blank");
      success("iCal File Generated", "Starting download of calendar feed standard file.");
    } catch (err) {
      toastError("Export Failed", "Could not compile active timeline.");
    }
  };

  // Test live window checker
  const handleCheckWindow = async () => {
    try {
      const dateParam = checkDateVal ? new Date(checkDateVal).toISOString() : new Date().toISOString();
      const queryParams = new URLSearchParams({
        windowType: checkWindowType,
        activityType: checkActivityType,
        checkDate: dateParam
      }).toString();
      const res = await api.get<boolean>(`/organizations/${orgId}/timeline/check-window?${queryParams}`);
      setCheckedResult(res);
    } catch (err: any) {
      toastError("Check Failed", err?.detail || "Verify timeline constraints.");
    }
  };

  const getDayName = (dayNum: number) => {
    const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
    return days[dayNum] || "";
  };

  const canWrite = user?.role?.permissions.includes("*") || user?.role?.permissions.includes("academic:write");

  const activeCalendar = unified?.activeCalendar;

  return (
    <div className="flex flex-col gap-6">
      {/* Sub menu controls */}
      <div className="flex flex-col md:flex-row gap-4 items-stretch md:items-center justify-between border-b border-border pb-4">
        <div className="flex items-center gap-4 overflow-x-auto scrollbar-thin">
          <Button
            variant={activeTab === "overview" ? "primary" : "outline"}
            onClick={() => setActiveTab("overview")}
            className="text-xs font-semibold cursor-pointer"
          >
            <Clock className="mr-2 h-4 w-4" /> Console Overview
          </Button>
          <Button
            variant={activeTab === "timelines" ? "primary" : "outline"}
            onClick={() => setActiveTab("timelines")}
            className="text-xs font-semibold cursor-pointer"
          >
            <Layers className="mr-2 h-4 w-4" /> Year & Semester Timelines
          </Button>
          <Button
            variant={activeTab === "exceptions" ? "primary" : "outline"}
            onClick={() => setActiveTab("exceptions")}
            className="text-xs font-semibold cursor-pointer"
          >
            <CalendarIcon className="mr-2 h-4 w-4" /> Holidays & Exceptions
          </Button>
          <Button
            variant={activeTab === "windows" ? "primary" : "outline"}
            onClick={() => setActiveTab("windows")}
            className="text-xs font-semibold cursor-pointer"
          >
            <CalendarRange className="mr-2 h-4 w-4" /> Registration & Exam Windows
          </Button>
          <Button
            variant={activeTab === "events" ? "primary" : "outline"}
            onClick={() => setActiveTab("events")}
            className="text-xs font-semibold cursor-pointer"
          >
            <Sparkles className="mr-2 h-4 w-4" /> Custom Events
          </Button>
          <Button
            variant={activeTab === "checker" ? "primary" : "outline"}
            onClick={() => setActiveTab("checker")}
            className="text-xs font-semibold cursor-pointer"
          >
            <UserCheck className="mr-2 h-4 w-4" /> Live Checker Tool
          </Button>
        </div>

        <div className="flex items-center gap-2">
          {activeCalendar && (
            <Button variant="outline" size="sm" onClick={handleExportICS} className="text-xs">
              <Download className="mr-2 h-4 w-4" /> Export iCal (.ics)
            </Button>
          )}
          {canWrite && (
            <Button size="sm" onClick={() => setCalModalOpen(true)} className="text-xs">
              <Plus className="mr-2 h-4 w-4" /> Create Calendar
            </Button>
          )}
        </div>
      </div>

      {/* OVERVIEW PANEL */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Active Calendar Summary */}
          <Card className="lg:col-span-2 glass">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <CalendarCheck2 className="h-5 w-5 text-primary" /> Active Academic Calendar
              </CardTitle>
              <CardDescription>The single source of time isolation for this institution</CardDescription>
            </CardHeader>
            <CardContent>
              {calLoading || uniLoading ? (
                <div className="space-y-4">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ) : activeCalendar ? (
                <div className="flex flex-col gap-6">
                  <div className="flex items-start justify-between border-b border-border pb-4">
                    <div>
                      <h3 className="text-lg font-bold text-foreground">{activeCalendar.name}</h3>
                      <p className="text-xs text-muted-foreground mt-1">Calendar ID: {activeCalendar.calendarId}</p>
                    </div>
                    <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
                      ACTIVE
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="text-muted-foreground">Timezone Setting</span>
                      <p className="font-semibold text-foreground mt-1 flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5" /> {activeCalendar.timezone}
                      </p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Weekly Working Days</span>
                      <p className="font-semibold text-foreground mt-1">
                        {activeCalendar.weeklyWorkingDays.map(d => getDayName(d)).join(", ")}
                      </p>
                    </div>
                  </div>

                  <div className="bg-primary/5 rounded-xl border border-primary/10 p-4 flex gap-3">
                    <Info className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                    <div className="text-xs">
                      <h4 className="font-bold text-primary">Integration Guidelines</h4>
                      <p className="text-muted-foreground mt-1">
                        All modules in CampusOS (including course schedules, attendance lists, placement sessions, and certificate credentials) automatically read windows and holidays registered in this calendar.
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <EmptyState
                  title="No Active Calendar"
                  description="An active calendar is required to configure academic timelines and scheduling windows."
                  actionText="Create Calendar"
                  onAction={() => setCalModalOpen(true)}
                />
              )}
            </CardContent>
          </Card>

          {/* List of Calendars / Quick Actions */}
          <div className="flex flex-col gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Quick Statistics</CardTitle>
              </CardHeader>
              <CardContent className="text-xs space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <span className="text-muted-foreground">Year Timelines</span>
                  <span className="font-bold text-foreground">{unified?.academicYearTimelines?.length || 0}</span>
                </div>
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <span className="text-muted-foreground">Semester Timelines</span>
                  <span className="font-bold text-foreground">{unified?.semesterTimelines?.length || 0}</span>
                </div>
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <span className="text-muted-foreground">Holidays</span>
                  <span className="font-bold text-foreground">{unified?.holidays?.length || 0}</span>
                </div>
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <span className="text-muted-foreground">Working Day Exceptions</span>
                  <span className="font-bold text-foreground">{unified?.workingDays?.length || 0}</span>
                </div>
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <span className="text-muted-foreground">Scheduling Windows</span>
                  <span className="font-bold text-foreground">{unified?.schedulingWindows?.length || 0}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Available Calendars</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {calendars.map((cal) => (
                  <div key={cal.calendarId} className="flex items-center justify-between border border-border p-3 rounded-xl text-xs">
                    <div>
                      <p className="font-semibold text-foreground">{cal.name}</p>
                      <p className="text-[10px] text-muted-foreground">{cal.timezone}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {!cal.isActive && canWrite && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => activateCalMutation.mutate(cal.calendarId)}
                          className="h-7 text-[10px] uppercase font-bold text-primary hover:bg-primary/10 cursor-pointer"
                        >
                          Activate
                        </Button>
                      )}
                      {cal.isActive && (
                        <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-bold uppercase text-[9px]">
                          Active
                        </span>
                      )}
                      {!cal.isActive && canWrite && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            if (confirm("Are you sure you want to delete this calendar?")) {
                              deleteCalMutation.mutate(cal.calendarId);
                            }
                          }}
                          className="h-7 text-destructive hover:bg-destructive/10 cursor-pointer"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* TIMELINES PANEL */}
      {activeTab === "timelines" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Academic Year Timelines */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <div>
                <CardTitle className="text-base">Academic Year Timelines</CardTitle>
                <CardDescription>Map calendar rules to specific academic year periods</CardDescription>
              </div>
              {canWrite && activeCalendar && (
                <Button
                  size="sm"
                  onClick={() => {
                    yearTimelineForm.setValue("calendarId", activeCalendar.calendarId);
                    setYearTimelineModalOpen(true);
                  }}
                  className="h-8 text-xs"
                >
                  <Plus className="mr-1.5 h-3.5 w-3.5" /> Config Year
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {unified?.academicYearTimelines && unified.academicYearTimelines.length > 0 ? (
                <div className="space-y-4">
                  {unified.academicYearTimelines.map((ayt) => {
                    const mappedYear = academicYears.find(y => y.id === ayt.academicYearId || y.academicYearId === ayt.academicYearId);
                    return (
                      <div key={ayt.timelineId} className="border border-border rounded-xl p-4 flex flex-col gap-3">
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="font-bold text-foreground text-sm">
                              {mappedYear?.name || "Academic Year Timeline"}
                            </span>
                            <p className="text-[10px] text-muted-foreground mt-0.5">Timeline ID: {ayt.timelineId}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary uppercase text-[9px] font-semibold">
                              {ayt.status}
                            </span>
                            {canWrite && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  if (confirm("Delete this academic year timeline? This will not affect the academic year itself.")) {
                                    deleteYearTimelineMutation.mutate(ayt.timelineId);
                                  }
                                }}
                                className="h-7 text-destructive hover:bg-destructive/10 cursor-pointer"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            )}
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-xs border-t border-border pt-3 mt-1 text-muted-foreground">
                          <div>
                            <span>Start Date</span>
                            <p className="font-semibold text-foreground mt-0.5">
                              {new Date(ayt.startDate).toLocaleDateString()}
                            </p>
                          </div>
                          <div>
                            <span>End Date</span>
                            <p className="font-semibold text-foreground mt-0.5">
                              {new Date(ayt.endDate).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <EmptyState
                  title="No Academic Year Timelines"
                  description="Register year boundaries mapped to your active calendar config."
                />
              )}
            </CardContent>
          </Card>

          {/* Semester Timelines */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <div>
                <CardTitle className="text-base">Semester Timelines</CardTitle>
                <CardDescription>View and configure semester durations (non-overlapping constraint)</CardDescription>
              </div>
              {canWrite && unified?.academicYearTimelines && unified.academicYearTimelines.length > 0 && (
                <Button
                  size="sm"
                  onClick={() => {
                    semTimelineForm.setValue("academicYearTimelineId", unified.academicYearTimelines[0].timelineId);
                    setSemTimelineModalOpen(true);
                  }}
                  className="h-8 text-xs"
                >
                  <Plus className="mr-1.5 h-3.5 w-3.5" /> Add Semester
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {unified?.semesterTimelines && unified.semesterTimelines.length > 0 ? (
                <div className="space-y-4">
                  {unified.semesterTimelines.map((semt) => {
                    const semModel = semesters.find(s => s.id === semt.semesterId || s.semesterId === semt.semesterId);
                    return (
                      <div key={semt.timelineId} className="border border-border rounded-xl p-4 flex flex-col gap-3">
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="font-bold text-foreground text-sm">
                              {semModel?.name || `Semester (Number: ${semt.semesterId})`}
                            </span>
                            <p className="text-[10px] text-muted-foreground mt-0.5">Timeline ID: {semt.timelineId}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary uppercase text-[9px] font-semibold">
                              {semt.status}
                            </span>
                            {canWrite && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  if (confirm("Delete this semester timeline?")) {
                                    deleteSemTimelineMutation.mutate(semt.timelineId);
                                  }
                                }}
                                className="h-7 text-destructive hover:bg-destructive/10 cursor-pointer"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            )}
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-xs border-t border-border pt-3 mt-1 text-muted-foreground">
                          <div>
                            <span>Start Date</span>
                            <p className="font-semibold text-foreground mt-0.5">
                              {new Date(semt.startDate).toLocaleDateString()}
                            </p>
                          </div>
                          <div>
                            <span>End Date</span>
                            <p className="font-semibold text-foreground mt-0.5">
                              {new Date(semt.endDate).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <EmptyState
                  title="No Semester Timelines"
                  description="Register nested semester spans inside configured academic year limits."
                />
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* HOLIDAYS PANEL */}
      {activeTab === "exceptions" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Holidays */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <div>
                <CardTitle className="text-base">Institutional Holidays</CardTitle>
                <CardDescription>Authorized leaves and breaks overriding weekly working rules</CardDescription>
              </div>
              {canWrite && activeCalendar && (
                <Button
                  size="sm"
                  onClick={() => {
                    holidayForm.setValue("calendarId", activeCalendar.calendarId);
                    setHolidayModalOpen(true);
                  }}
                  className="h-8 text-xs"
                >
                  <Plus className="mr-1.5 h-3.5 w-3.5" /> Add Holiday
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {unified?.holidays && unified.holidays.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead>
                      <tr className="border-b border-border text-muted-foreground uppercase tracking-wider text-[10px]">
                        <th className="py-2.5 px-3">Date</th>
                        <th className="py-2.5 px-3">Name</th>
                        <th className="py-2.5 px-3">Type</th>
                        <th className="py-2.5 px-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {unified.holidays.map((h) => (
                        <tr key={h.holidayId} className="border-b border-border/50 hover:bg-foreground/[0.02]">
                          <td className="py-3 px-3 font-semibold text-foreground">
                            {new Date(h.date).toLocaleDateString()}
                          </td>
                          <td className="py-3 px-3 text-foreground">{h.name}</td>
                          <td className="py-3 px-3">
                            <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 text-[9px] font-semibold uppercase">
                              {h.type}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-right">
                            {canWrite && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  if (confirm("Delete this holiday?")) {
                                    deleteHolidayMutation.mutate(h.holidayId);
                                  }
                                }}
                                className="h-7 text-destructive hover:bg-destructive/10 cursor-pointer"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState title="No Holidays" description="Weekly working rules apply unconditionally." />
              )}
            </CardContent>
          </Card>

          {/* Working Days exceptions */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <div>
                <CardTitle className="text-base">Working Day Exceptions</CardTitle>
                <CardDescription>Weekend days converted to active instructional days</CardDescription>
              </div>
              {canWrite && activeCalendar && (
                <Button
                  size="sm"
                  onClick={() => {
                    wkdForm.setValue("calendarId", activeCalendar.calendarId);
                    setWkdModalOpen(true);
                  }}
                  className="h-8 text-xs"
                >
                  <Plus className="mr-1.5 h-3.5 w-3.5" /> Add Exception
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {unified?.workingDays && unified.workingDays.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead>
                      <tr className="border-b border-border text-muted-foreground uppercase tracking-wider text-[10px]">
                        <th className="py-2.5 px-3">Date</th>
                        <th className="py-2.5 px-3">Description</th>
                        <th className="py-2.5 px-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {unified.workingDays.map((w) => (
                        <tr key={w.workingDayId} className="border-b border-border/50 hover:bg-foreground/[0.02]">
                          <td className="py-3 px-3 font-semibold text-foreground">
                            {new Date(w.date).toLocaleDateString()}
                          </td>
                          <td className="py-3 px-3 text-foreground">{w.description || "Compensatory working day"}</td>
                          <td className="py-3 px-3 text-right">
                            {canWrite && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  if (confirm("Delete this working day exception?")) {
                                    deleteWkdMutation.mutate(w.workingDayId);
                                  }
                                }}
                                className="h-7 text-destructive hover:bg-destructive/10 cursor-pointer"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState title="No exceptions registered" description="Standard weekend rules apply." />
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* REGISTRATION & EXAM WINDOWS PANEL */}
      {activeTab === "windows" && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
            <div>
              <CardTitle className="text-base">Scheduling Windows</CardTitle>
              <CardDescription>Configure registration, examination, and grading windows for CampusOS modules</CardDescription>
            </div>
            {canWrite && activeCalendar && (
              <Button
                size="sm"
                onClick={() => {
                  windowForm.setValue("calendarId", activeCalendar.calendarId);
                  setWindowModalOpen(true);
                }}
                className="h-8 text-xs"
              >
                <Plus className="mr-1.5 h-3.5 w-3.5" /> Define Window
              </Button>
            )}
          </CardHeader>
          <CardContent>
            {unified?.schedulingWindows && unified.schedulingWindows.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground uppercase tracking-wider text-[10px]">
                      <th className="py-2.5 px-3">Name</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Activity</th>
                      <th className="py-2.5 px-3">Start Date</th>
                      <th className="py-2.5 px-3">End Date</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {unified.schedulingWindows.map((win) => {
                      const now = new Date();
                      const start = new Date(win.startDate);
                      const end = new Date(win.endDate);
                      const isCurrent = now >= start && now <= end && win.isActive;

                      return (
                        <tr key={win.windowId} className="border-b border-border/50 hover:bg-foreground/[0.02]">
                          <td className="py-3 px-3 font-semibold text-foreground">{win.name}</td>
                          <td className="py-3 px-3">
                            <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-[9px] font-semibold uppercase">
                              {win.windowType}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-muted-foreground">{win.activityType}</td>
                          <td className="py-3 px-3">{start.toLocaleDateString()}</td>
                          <td className="py-3 px-3">{end.toLocaleDateString()}</td>
                          <td className="py-3 px-3">
                            {isCurrent ? (
                              <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-0.5 text-[9px] font-bold text-emerald-400">
                                OPEN NOW
                              </span>
                            ) : (
                              <span className="inline-flex items-center rounded-full bg-zinc-500/10 px-2 py-0.5 text-[9px] font-bold text-muted-foreground">
                                CLOSED
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-3 text-right">
                            {canWrite && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  if (confirm("Delete this scheduling window?")) {
                                    deleteWindowMutation.mutate(win.windowId);
                                  }
                                }}
                                className="h-7 text-destructive hover:bg-destructive/10 cursor-pointer"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState title="No Windows" description="Platform modules will not allow any transactional actions." />
            )}
          </CardContent>
        </Card>
      )}

      {/* CUSTOM EVENTS PANEL */}
      {activeTab === "events" && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
            <div>
              <CardTitle className="text-base">Institutional Events</CardTitle>
              <CardDescription>Academic and extracurricular events displayed on student/faculty schedules</CardDescription>
            </div>
            {canWrite && activeCalendar && (
              <Button
                size="sm"
                onClick={() => {
                  eventForm.setValue("calendarId", activeCalendar.calendarId);
                  setEventModalOpen(true);
                }}
                className="h-8 text-xs"
              >
                <Plus className="mr-1.5 h-3.5 w-3.5" /> Schedule Event
              </Button>
            )}
          </CardHeader>
          <CardContent>
            {unified?.calendarEvents && unified.calendarEvents.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {unified.calendarEvents.map((evt) => (
                  <Card key={evt.eventId} className="overflow-hidden border border-border">
                    <CardHeader className="p-4 bg-muted/20 border-b border-border">
                      <div className="flex items-center justify-between">
                        <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-[9px] font-bold uppercase">
                          {evt.category}
                        </span>
                        {canWrite && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              if (confirm("Remove event from agenda?")) {
                                deleteEventMutation.mutate(evt.eventId);
                              }
                            }}
                            className="h-7 text-destructive hover:bg-destructive/10 cursor-pointer"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                      <CardTitle className="text-sm font-bold text-foreground mt-2">{evt.name}</CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 text-xs text-muted-foreground flex flex-col gap-2">
                      <p>{evt.description || "No description provided."}</p>
                      <div className="mt-2 text-[10px] border-t border-border/50 pt-2 flex items-center justify-between text-foreground">
                        <span>Starts: {new Date(evt.startDate).toLocaleDateString()}</span>
                        <span>Ends: {new Date(evt.endDate).toLocaleDateString()}</span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <EmptyState title="No Events Scheduled" description="Schedule activities or institutional events." />
            )}
          </CardContent>
        </Card>
      )}

      {/* LIVE CHECKER TOOL */}
      {activeTab === "checker" && (
        <Card className="glass">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <UserCheck className="h-5 w-5 text-primary" /> Live Scheduler Exception & Window Checker
            </CardTitle>
            <CardDescription>
              Test whether specific platform actions are allowed in the database on a given time slot.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="max-w-xl flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs text-muted-foreground font-semibold">Window Type</label>
                  <select
                    value={checkWindowType}
                    onChange={(e) => setCheckWindowType(e.target.value as WindowType)}
                    className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs"
                  >
                    <option value="REGISTRATION">REGISTRATION</option>
                    <option value="EXAMINATION">EXAMINATION</option>
                    <option value="GRADING">GRADING</option>
                    <option value="CERTIFICATE">CERTIFICATE</option>
                    <option value="ADMISSION">ADMISSION</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs text-muted-foreground font-semibold">Activity Type Code</label>
                  <input
                    type="text"
                    value={checkActivityType}
                    onChange={(e) => setCheckActivityType(e.target.value.toUpperCase())}
                    className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground uppercase"
                    placeholder="e.g. COURSES, EXAMS"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs text-muted-foreground font-semibold">Check Time (Leave empty for UTC Now)</label>
                <Input
                  type="datetime-local"
                  value={checkDateVal}
                  onChange={(e) => setCheckDateVal(e.target.value)}
                  className="w-full text-xs"
                />
              </div>

              <Button onClick={handleCheckWindow} className="w-full cursor-pointer text-xs mt-2">
                Evaluate Scheduling Status
              </Button>

              {checkedResult !== null && (
                <div className={`mt-4 p-4 rounded-xl border flex items-center gap-3 ${
                  checkedResult ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" : "bg-rose-500/10 border-rose-500/20 text-rose-400"
                }`}>
                  {checkedResult ? (
                    <>
                      <CheckCircle className="h-5 w-5 text-emerald-400 flex-shrink-0" />
                      <div className="text-xs font-semibold">
                        WINDOW ACTIVE: Actions relating to this scheduling config are allowed in the database.
                      </div>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="h-5 w-5 text-rose-400 flex-shrink-0" />
                      <div className="text-xs font-semibold">
                        WINDOW CLOSED: Actions will be blocked by calendar engine constraints.
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ========================================== MODALS ========================================== */}

      {/* CREATE CALENDAR MODAL */}
      <Dialog isOpen={calModalOpen} onClose={() => setCalModalOpen(false)} title="Create Academic Calendar">
        <form onSubmit={calForm.handleSubmit(onCalSubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-semibold">Calendar Name</label>
            <Input
              type="text"
              placeholder="e.g. Main Collegiate Calendar 2026"
              {...calForm.register("name")}
            />
            {calForm.formState.errors.name && <p className="text-[10px] text-destructive">{calForm.formState.errors.name.message}</p>}
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-semibold">Default Timezone</label>
            <Input
              type="text"
              placeholder="UTC, Asia/Kolkata, America/New_York"
              {...calForm.register("timezone")}
            />
            {calForm.formState.errors.timezone && <p className="text-[10px] text-destructive">{calForm.formState.errors.timezone.message}</p>}
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setCalModalOpen(false)} className="text-xs">
              Cancel
            </Button>
            <Button type="submit" className="text-xs">
              Create Calendar
            </Button>
          </div>
        </form>
      </Dialog>

      {/* CREATE YEAR TIMELINE MODAL */}
      <Dialog isOpen={yearTimelineModalOpen} onClose={() => setYearTimelineModalOpen(false)} title="Academic Year Timeline">
        <form onSubmit={yearTimelineForm.handleSubmit(onYearTimelineSubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-semibold">Academic Year</label>
            <select
              {...yearTimelineForm.register("academicYearId")}
              className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground"
            >
              <option value="">Select Academic Year...</option>
              {academicYears.map((ay) => (
                <option key={ay.academicYearId} value={ay.academicYearId} className="text-foreground">{ay.name}</option>
              ))}
            </select>
            {yearTimelineForm.formState.errors.academicYearId && <p className="text-[10px] text-destructive">{yearTimelineForm.formState.errors.academicYearId.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground font-semibold">Start Date</label>
              <Input type="date" {...yearTimelineForm.register("startDate")} />
              {yearTimelineForm.formState.errors.startDate && <p className="text-[10px] text-destructive">{yearTimelineForm.formState.errors.startDate.message}</p>}
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground font-semibold">End Date</label>
              <Input type="date" {...yearTimelineForm.register("endDate")} />
              {yearTimelineForm.formState.errors.endDate && <p className="text-[10px] text-destructive">{yearTimelineForm.formState.errors.endDate.message}</p>}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setYearTimelineModalOpen(false)} className="text-xs">
              Cancel
            </Button>
            <Button type="submit" className="text-xs">
              Create Timeline
            </Button>
          </div>
        </form>
      </Dialog>

      {/* CREATE SEMESTER TIMELINE MODAL */}
      <Dialog isOpen={semTimelineModalOpen} onClose={() => setSemTimelineModalOpen(false)} title="Semester Timeline Config">
        <form onSubmit={semTimelineForm.handleSubmit(onSemTimelineSubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-semibold">Academic Year Timeline</label>
            <select
              {...semTimelineForm.register("academicYearTimelineId")}
              className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground"
            >
              {unified?.academicYearTimelines?.map((ayt) => {
                const year = academicYears.find(y => y.academicYearId === ayt.academicYearId || y.id === ayt.academicYearId);
                return (
                  <option key={ayt.timelineId} value={ayt.timelineId} className="text-foreground">{year?.name || ayt.timelineId}</option>
                );
              })}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-semibold">Semester</label>
            <select
              {...semTimelineForm.register("semesterId")}
              className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground"
            >
              <option value="">Select Semester...</option>
              {semesters.map((s) => (
                <option key={s.semesterId} value={s.semesterId} className="text-foreground">{s.name}</option>
              ))}
            </select>
            {semTimelineForm.formState.errors.semesterId && <p className="text-[10px] text-destructive">{semTimelineForm.formState.errors.semesterId.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground font-semibold">Start Date</label>
              <Input type="date" {...semTimelineForm.register("startDate")} />
              {semTimelineForm.formState.errors.startDate && <p className="text-[10px] text-destructive">{semTimelineForm.formState.errors.startDate.message}</p>}
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground font-semibold">End Date</label>
              <Input type="date" {...semTimelineForm.register("endDate")} />
              {semTimelineForm.formState.errors.endDate && <p className="text-[10px] text-destructive">{semTimelineForm.formState.errors.endDate.message}</p>}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setSemTimelineModalOpen(false)} className="text-xs">
              Cancel
            </Button>
            <Button type="submit" className="text-xs">
              Create Semester Timeline
            </Button>
          </div>
        </form>
      </Dialog>

      {/* CREATE HOLIDAY MODAL */}
      <Dialog isOpen={holidayModalOpen} onClose={() => setHolidayModalOpen(false)} title="Register Institutional Holiday">
        <form onSubmit={holidayForm.handleSubmit(onHolidaySubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-semibold">Holiday Name</label>
            <Input type="text" placeholder="e.g. Independence Day Break" {...holidayForm.register("name")} />
            {holidayForm.formState.errors.name && <p className="text-[10px] text-destructive">{holidayForm.formState.errors.name.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground font-semibold">Holiday Date</label>
              <Input type="date" {...holidayForm.register("date")} />
              {holidayForm.formState.errors.date && <p className="text-[10px] text-destructive">{holidayForm.formState.errors.date.message}</p>}
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground font-semibold">Holiday Type</label>
              <select
                {...holidayForm.register("type")}
                className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground"
              >
                <option value="PUBLIC" className="text-foreground">PUBLIC</option>
                <option value="RESTRICTED" className="text-foreground">RESTRICTED</option>
                <option value="INSTITUTIONAL" className="text-foreground">INSTITUTIONAL</option>
              </select>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-semibold">Description</label>
            <Input type="text" placeholder="Details of holiday break..." {...holidayForm.register("description")} />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setHolidayModalOpen(false)} className="text-xs">
              Cancel
            </Button>
            <Button type="submit" className="text-xs">
              Register Holiday
            </Button>
          </div>
        </form>
      </Dialog>

      {/* CREATE WORKING DAY MODAL */}
      <Dialog isOpen={wkdModalOpen} onClose={() => setWkdModalOpen(false)} title="Register Working Day Exception">
        <form onSubmit={wkdForm.handleSubmit(onWkdSubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-semibold">Target Date</label>
            <Input type="date" {...wkdForm.register("date")} />
            {wkdForm.formState.errors.date && <p className="text-[10px] text-destructive">{wkdForm.formState.errors.date.message}</p>}
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-semibold">Reason/Description</label>
            <Input type="text" placeholder="e.g. Compensating for Monday holiday list" {...wkdForm.register("description")} />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setWkdModalOpen(false)} className="text-xs">
              Cancel
            </Button>
            <Button type="submit" className="text-xs">
              Register Exception
            </Button>
          </div>
        </form>
      </Dialog>

      {/* DEFINE WINDOW MODAL */}
      <Dialog isOpen={windowModalOpen} onClose={() => setWindowModalOpen(false)} title="Define Scheduling Window">
        <form onSubmit={windowForm.handleSubmit(onWindowSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground font-semibold">Window Type</label>
              <select
                {...windowForm.register("windowType")}
                className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground"
              >
                <option value="REGISTRATION" className="text-foreground">REGISTRATION</option>
                <option value="EXAMINATION" className="text-foreground">EXAMINATION</option>
                <option value="GRADING" className="text-foreground">GRADING</option>
                <option value="CERTIFICATE" className="text-foreground">CERTIFICATE</option>
                <option value="ADMISSION" className="text-foreground">ADMISSION</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground font-semibold">Activity Type Code</label>
              <Input type="text" placeholder="COURSES, EXAMS, EVENTS" {...windowForm.register("activityType")} />
              {windowForm.formState.errors.activityType && <p className="text-[10px] text-destructive">{windowForm.formState.errors.activityType.message}</p>}
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-semibold">Window Display Name</label>
            <Input type="text" placeholder="e.g. Fall Course Registration Phase 1" {...windowForm.register("name")} />
            {windowForm.formState.errors.name && <p className="text-[10px] text-destructive">{windowForm.formState.errors.name.message}</p>}
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-semibold">Associate Semester (Optional)</label>
            <select
              {...windowForm.register("semesterTimelineId")}
              className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground"
            >
              <option value="" className="text-foreground">No specific semester timeline association</option>
              {unified?.semesterTimelines?.map((semt) => {
                const s = semesters.find(x => x.semesterId === semt.semesterId || x.id === semt.semesterId);
                return (
                  <option key={semt.timelineId} value={semt.timelineId} className="text-foreground">{s?.name || semt.timelineId}</option>
                );
              })}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground font-semibold">Start Date & Time</label>
              <Input type="datetime-local" {...windowForm.register("startDate")} />
              {windowForm.formState.errors.startDate && <p className="text-[10px] text-destructive">{windowForm.formState.errors.startDate.message}</p>}
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground font-semibold">End Date & Time</label>
              <Input type="datetime-local" {...windowForm.register("endDate")} />
              {windowForm.formState.errors.endDate && <p className="text-[10px] text-destructive">{windowForm.formState.errors.endDate.message}</p>}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setWindowModalOpen(false)} className="text-xs">
              Cancel
            </Button>
            <Button type="submit" className="text-xs">
              Define Window
            </Button>
          </div>
        </form>
      </Dialog>

      {/* SCHEDULE EVENT MODAL */}
      <Dialog isOpen={eventModalOpen} onClose={() => setEventModalOpen(false)} title="Schedule Event">
        <form onSubmit={eventForm.handleSubmit(onEventSubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-semibold">Event Name</label>
            <Input type="text" placeholder="e.g. Annual Sports Meet" {...eventForm.register("name")} />
            {eventForm.formState.errors.name && <p className="text-[10px] text-destructive">{eventForm.formState.errors.name.message}</p>}
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-semibold">Category</label>
            <select
              {...eventForm.register("category")}
              className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground"
            >
              <option value="ACADEMIC" className="text-foreground">ACADEMIC</option>
              <option value="EXAM" className="text-foreground">EXAM</option>
              <option value="CULTURAL" className="text-foreground">CULTURAL</option>
              <option value="SPORTS" className="text-foreground">SPORTS</option>
              <option value="HOLIDAY" className="text-foreground">HOLIDAY</option>
              <option value="OTHER" className="text-foreground">OTHER</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground font-semibold">Start Date & Time</label>
              <Input type="datetime-local" {...eventForm.register("startDate")} />
              {eventForm.formState.errors.startDate && <p className="text-[10px] text-destructive">{eventForm.formState.errors.startDate.message}</p>}
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground font-semibold">End Date & Time</label>
              <Input type="datetime-local" {...eventForm.register("endDate")} />
              {eventForm.formState.errors.endDate && <p className="text-[10px] text-destructive">{eventForm.formState.errors.endDate.message}</p>}
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-semibold">Description</label>
            <Input type="text" placeholder="Details of activity..." {...eventForm.register("description")} />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setEventModalOpen(false)} className="text-xs">
              Cancel
            </Button>
            <Button type="submit" className="text-xs">
              Schedule Event
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
