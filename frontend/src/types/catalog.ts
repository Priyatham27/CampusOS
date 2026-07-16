// ─────────────────────────────────────────────
// Catalog Engine — TypeScript Types
// Story 3.3 — Academic Catalog Engine
// ─────────────────────────────────────────────

export type CurriculumStatus = "DRAFT" | "ACTIVE" | "ARCHIVED";

export type SubjectType = "CORE" | "ELECTIVE" | "LAB" | "PROJECT" | "SEMINAR";

export type BloomLevel =
  | "REMEMBER"
  | "UNDERSTAND"
  | "APPLY"
  | "ANALYZE"
  | "EVALUATE"
  | "CREATE";

export interface Curriculum {
  id: string;
  curriculumId: string;
  organizationId: string;
  programId: string;
  name: string;
  version: number;
  status: CurriculumStatus;
  effectiveFrom: string;
  totalCredits: number;
  description?: string;
  parentCurriculumId?: string;
  admissionBatch?: string;
  createdAt: string;
  updatedAt: string;
  createdBy?: string;
}

export interface LearningOutcome {
  code: string;
  description: string;
  bloomLevel: BloomLevel;
}

export interface AssessmentComponent {
  component: string;
  weight: number;
  maxMarks: number;
}

export interface AssessmentScheme {
  components: AssessmentComponent[];
  passingPercentage: number;
}

export interface Subject {
  id: string;
  subjectId: string;
  organizationId: string;
  curriculumId: string;
  semesterNumber: number;
  subjectCode: string;
  name: string;
  credits: number;
  subjectType: SubjectType;
  isElective: boolean;
  electiveGroup?: string;
  prerequisites: string[];
  learningOutcomes: LearningOutcome[];
  assessmentScheme?: AssessmentScheme;
  createdAt: string;
  updatedAt: string;
}

export interface PrerequisiteGraphNode {
  id: string;      // subject_id
  code: string;
  name: string;
  semesterNumber: number;
  type: SubjectType;
  credits: number;
  isElective: boolean;
}

export interface PrerequisiteGraphEdge {
  from: string;   // subject that has the prerequisite
  to: string;     // the prerequisite subject
}

export interface PrerequisiteGraph {
  curriculumId: string;
  nodes: PrerequisiteGraphNode[];
  edges: PrerequisiteGraphEdge[];
}

export interface FullCurriculum {
  curriculum: Curriculum;
  semesters: Record<string, Subject[]>;
  totalSubjects: number;
}

// ─── Form Payloads ───────────────────────────

export interface CurriculumCreatePayload {
  programId: string;
  name: string;
  effectiveFrom: string;
  description?: string;
  admissionBatch?: string;
}

export interface CurriculumUpdatePayload {
  name?: string;
  effectiveFrom?: string;
  description?: string;
  admissionBatch?: string;
}

export interface SubjectCreatePayload {
  semesterNumber: number;
  subjectCode: string;
  name: string;
  credits: number;
  subjectType: SubjectType;
  isElective: boolean;
  electiveGroup?: string;
  prerequisites: string[];
}

export interface SubjectUpdatePayload {
  semesterNumber?: number;
  name?: string;
  credits?: number;
  subjectType?: SubjectType;
  isElective?: boolean;
  electiveGroup?: string;
  prerequisites?: string[];
}

export interface AssessmentSchemePayload {
  components: AssessmentComponent[];
  passingPercentage: number;
}

export interface LearningOutcomesPayload {
  learningOutcomes: LearningOutcome[];
}
