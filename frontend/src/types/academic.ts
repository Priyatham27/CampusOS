export interface AcademicYear {
  id: string;
  academicYearId: string;
  organizationId: string;
  name: string;
  startDate: string;
  endDate: string;
  current: boolean;
}

export interface Department {
  id: string;
  departmentId: string;
  organizationId: string;
  name: string;
  code: string;
  hod?: string;
  description?: string;
  status: "ACTIVE" | "INACTIVE";
}

export interface Program {
  id: string;
  programId: string;
  organizationId: string;
  departmentId: string;
  name: string;
  duration: number;
  level: "UNDERGRADUATE" | "POSTGRADUATE" | "DOCTORAL" | "DIPLOMA";
}

export interface Branch {
  id: string;
  branchId: string;
  organizationId: string;
  departmentId: string;
  code: string;
  name: string;
}

export interface Semester {
  id: string;
  semesterId: string;
  organizationId: string;
  academicYearId?: string;
  number: number;
  name: string;
  status: "ACTIVE" | "INACTIVE";
}

export interface Section {
  id: string;
  sectionId: string;
  organizationId: string;
  branchId: string;
  semesterId: string;
  name: string;
  strength: number;
}

export interface Course {
  id: string;
  courseId: string;
  organizationId: string;
  programId: string;
  name: string;
  courseCode: string;
  credits: number;
  semester: string;
}

export interface AuditLog {
  id: string;
  organizationId: string;
  action: string;
  timestamp: string;
  performedBy: string;
  module: string;
  details: Record<string, any>;
}
