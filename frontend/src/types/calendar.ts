export type CalendarStatus = "DRAFT" | "ACTIVE" | "ARCHIVED";
export type TimelineStatus = "DRAFT" | "ACTIVE" | "ARCHIVED";
export type HolidayType = "PUBLIC" | "RESTRICTED" | "INSTITUTIONAL";
export type WindowType = "REGISTRATION" | "EXAMINATION" | "GRADING" | "CERTIFICATE" | "ADMISSION";

export interface AcademicCalendar {
  id: string;
  calendarId: string;
  organizationId: string;
  name: string;
  timezone: string;
  weeklyWorkingDays: number[];
  isActive: boolean;
  status: CalendarStatus;
  createdAt?: string;
  updatedAt?: string;
}

export interface AcademicYearTimeline {
  id: string;
  timelineId: string;
  calendarId: string;
  academicYearId: string;
  organizationId: string;
  startDate: string;
  endDate: string;
  status: TimelineStatus;
  createdAt?: string;
  updatedAt?: string;
}

export interface SemesterTimeline {
  id: string;
  timelineId: string;
  academicYearTimelineId: string;
  semesterId: string;
  organizationId: string;
  startDate: string;
  endDate: string;
  status: TimelineStatus;
  createdAt?: string;
  updatedAt?: string;
}

export interface Holiday {
  id: string;
  holidayId: string;
  calendarId: string;
  organizationId: string;
  name: string;
  date: string;
  type: HolidayType;
  description?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface WorkingDay {
  id: string;
  workingDayId: string;
  calendarId: string;
  organizationId: string;
  date: string;
  description?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface SchedulingWindow {
  id: string;
  windowId: string;
  calendarId: string;
  organizationId: string;
  semesterTimelineId?: string;
  windowType: WindowType;
  activityType: string;
  name: string;
  startDate: string;
  endDate: string;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface CalendarEvent {
  id: string;
  eventId: string;
  calendarId: string;
  organizationId: string;
  name: string;
  startDate: string;
  endDate: string;
  description?: string;
  category: "ACADEMIC" | "EXAM" | "CULTURAL" | "SPORTS" | "HOLIDAY" | "OTHER";
  createdAt?: string;
  updatedAt?: string;
}

export interface UnifiedTimeline {
  activeCalendar: AcademicCalendar | null;
  academicYearTimelines: AcademicYearTimeline[];
  semesterTimelines: SemesterTimeline[];
  holidays: Holiday[];
  workingDays: WorkingDay[];
  schedulingWindows: SchedulingWindow[];
  calendarEvents: CalendarEvent[];
}
