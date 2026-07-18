export type StudentStatus = "ACTIVE" | "INACTIVE" | "ARCHIVED" | "GRADUATED" | "SUSPENDED";

export type DocumentCategory = "ACADEMIC" | "IDENTITY" | "MEDICAL" | "OTHER";

export type AchievementCategory = "ACADEMIC" | "SPORTS" | "CULTURAL" | "OTHER";

export type SkillLevel = "BEGINNER" | "INTERMEDIATE" | "ADVANCED";

export interface EmergencyContact {
  name: string;
  relation: string;
  phone: string;
  alternativePhone?: string;
  email?: string;
}

export interface StudentPreference {
  notificationsEnabled: boolean;
  theme: string;
  language: string;
}

export interface StudentNote {
  noteId: string;
  author: string;
  content: string;
  createdAt: string;
}

export interface Student {
  id: string;
  studentId: string;
  userId: string;
  organizationId: string;
  rollNumber: string;
  firstName: string;
  lastName: string;
  email: string;
  phone?: string;
  dateOfBirth: string;
  gender: string;
  bloodGroup?: string;
  admissionDate: string;
  status: StudentStatus;
  isArchived: boolean;
  academicYearId?: string;
  departmentId?: string;
  programId?: string;
  branchId?: string;
  semesterId?: string;
  sectionId?: string;
  emergencyContact?: EmergencyContact;
  preferences: StudentPreference;
  tags: string[];
  notes: StudentNote[];
}

export interface Guardian {
  id: string;
  guardianId: string;
  studentId: string;
  organizationId: string;
  name: string;
  relation: string;
  phone: string;
  email?: string;
  occupation?: string;
  address?: string;
  isPrimary: boolean;
}

export interface StudentDocument {
  id: string;
  documentId: string;
  studentId: string;
  organizationId: string;
  name: string;
  filePath: string;
  fileType: string;
  fileSize: number;
  uploadedAt: string;
  category: DocumentCategory;
  isVerified: boolean;
}

export interface StudentAchievement {
  id: string;
  achievementId: string;
  studentId: string;
  organizationId: string;
  title: string;
  description?: string;
  dateEarned: string;
  category: AchievementCategory;
  certificatePath?: string;
}

export interface StudentSkill {
  id: string;
  skillId: string;
  studentId: string;
  organizationId: string;
  name: string;
  level: SkillLevel;
  verified: boolean;
}

export interface StudentProfilePayload {
  student: Student;
  guardians: Guardian[];
  documents: StudentDocument[];
  achievements: StudentAchievement[];
  skills: StudentSkill[];
}
