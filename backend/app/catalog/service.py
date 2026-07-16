"""
Catalog Engine — Service Layer
==============================
Implements CurriculumService, SubjectService, and CatalogService.

Key domain rules enforced here:
- Only DRAFT curricula can be edited or deleted
- Clone operation does a deep copy of all subjects (new CURR-id, version+1, DRAFT)
- Prerequisite cycle detection via iterative DFS on every subject add/update
- Assessment scheme weights must sum to exactly 100% (also enforced by model validator)
"""
import uuid
from copy import deepcopy
from datetime import datetime
from typing import List, Optional, Dict, Any

from beanie import PydanticObjectId

from app.models.catalog.curriculum import Curriculum, CurriculumStatus
from app.models.catalog.subject import (
    Subject, SubjectType, LearningOutcome, AssessmentScheme
)
from app.repositories.catalog import CurriculumRepository, SubjectRepository
from app.catalog.exceptions import (
    CurriculumNotFound,
    DuplicateCurriculum,
    CurriculumStatusConflict,
    CurriculumImmutable,
    SubjectNotFound,
    DuplicateSubject,
    PrerequisiteCycleDetected,
    PrerequisiteNotFound,
    PrerequisiteInUse,
    AssessmentSchemeInvalid,
)
from app.core.logger import logger


def _generate_id(prefix: str) -> str:
    """Generate a professional short ID like CURR-A3F2B1."""
    return f"{prefix}-{uuid.uuid4().hex[:6].upper()}"


def _detect_cycle(graph: Dict[str, List[str]], start: str) -> Optional[List[str]]:
    """
    Iterative DFS cycle detection for a prerequisite graph.
    Returns a list representing the cycle path if found, else None.
    
    graph: { subject_id: [prerequisite_subject_ids] }
    """
    visited = set()
    rec_stack = set()
    parent = {}

    def dfs(node: str) -> Optional[List[str]]:
        stack = [(node, iter(graph.get(node, [])))]
        rec_stack.add(node)

        while stack:
            current, children = stack[-1]
            try:
                child = next(children)
                if child not in graph:
                    continue
                if child in rec_stack:
                    # Reconstruct cycle path
                    path = [child]
                    c = current
                    while c != child:
                        path.append(c)
                        c = parent.get(c, child)
                    path.append(child)
                    return list(reversed(path))
                if child not in visited:
                    parent[child] = current
                    rec_stack.add(child)
                    stack.append((child, iter(graph.get(child, []))))
            except StopIteration:
                rec_stack.discard(current)
                visited.add(current)
                stack.pop()
        return None

    return dfs(start)


class CurriculumService:
    def __init__(self):
        self.repo = CurriculumRepository()

    async def create(
        self,
        org_id: PydanticObjectId,
        program_id: PydanticObjectId,
        name: str,
        effective_from: datetime,
        description: Optional[str] = None,
        admission_batch: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Curriculum:
        # Determine version number (max_version + 1 for this program)
        max_ver = await self.repo.get_max_version(org_id, program_id)
        version = max_ver + 1

        curriculum_id = _generate_id("CURR")
        curriculum = Curriculum(
            curriculumId=curriculum_id,
            organizationId=org_id,
            programId=program_id,
            name=name,
            version=version,
            status=CurriculumStatus.DRAFT,
            effectiveFrom=effective_from,
            description=description,
            admissionBatch=admission_batch,
            createdBy=user_id,
            normalizedName=name.lower().strip(),
            searchKeywords=[w.lower() for w in name.split() if w],
        )
        created = await self.repo.create(curriculum)
        logger.info(f"Curriculum created: {curriculum_id} v{version} for program {program_id}")
        return created

    async def get(self, curriculum_id: str, org_id: PydanticObjectId) -> Curriculum:
        doc = await self.repo.find_by_id(curriculum_id, org_id)
        if not doc:
            raise CurriculumNotFound(curriculum_id)
        return doc

    async def list(
        self,
        org_id: PydanticObjectId,
        program_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "createdAt",
        sort_order: str = "desc",
    ) -> tuple[List[Curriculum], int]:
        filters: Dict[str, Any] = {}
        if program_id:
            filters["programId"] = program_id
        if status:
            filters["status"] = status

        items = await self.repo.list(org_id, skip, limit, sort_by, sort_order, filters)
        total = await self.repo.count(org_id, filters)
        return items, total

    async def update(
        self,
        curriculum_id: str,
        org_id: PydanticObjectId,
        update_data: dict,
        user_id: Optional[str] = None,
    ) -> Curriculum:
        doc = await self.get(curriculum_id, org_id)
        if doc.status != CurriculumStatus.DRAFT:
            raise CurriculumImmutable()
        update_data["updatedBy"] = user_id
        if "name" in update_data:
            update_data["normalizedName"] = update_data["name"].lower().strip()
            update_data["searchKeywords"] = [w.lower() for w in update_data["name"].split() if w]
        return await self.repo.update(doc, update_data)

    async def publish(
        self, curriculum_id: str, org_id: PydanticObjectId, user_id: Optional[str] = None
    ) -> Curriculum:
        doc = await self.get(curriculum_id, org_id)
        if doc.status != CurriculumStatus.DRAFT:
            raise CurriculumStatusConflict("publish", doc.status)
        result = await self.repo.update_status(doc, CurriculumStatus.ACTIVE)
        logger.info(f"Curriculum published: {curriculum_id}")
        return result

    async def archive(
        self, curriculum_id: str, org_id: PydanticObjectId, user_id: Optional[str] = None
    ) -> Curriculum:
        doc = await self.get(curriculum_id, org_id)
        if doc.status != CurriculumStatus.ACTIVE:
            raise CurriculumStatusConflict("archive", doc.status)
        result = await self.repo.update_status(doc, CurriculumStatus.ARCHIVED)
        logger.info(f"Curriculum archived: {curriculum_id}")
        return result

    async def clone(
        self, curriculum_id: str, org_id: PydanticObjectId, user_id: Optional[str] = None
    ) -> Curriculum:
        """
        Deep clone a curriculum to create a new DRAFT version.
        All subjects are copied with new IDs into the new curriculum.
        The original curriculum is unaffected.
        """
        source = await self.get(curriculum_id, org_id)

        # Determine new version number
        max_ver = await self.repo.get_max_version(org_id, source.program_id)
        new_version = max_ver + 1

        new_curr_id = _generate_id("CURR")
        new_curriculum = Curriculum(
            curriculumId=new_curr_id,
            organizationId=org_id,
            programId=source.program_id,
            name=source.name,
            version=new_version,
            status=CurriculumStatus.DRAFT,
            effectiveFrom=datetime.utcnow(),
            totalCredits=source.total_credits,
            description=source.description,
            parentCurriculumId=source.id,
            admissionBatch=None,  # Admin sets this on the new version
            createdBy=user_id,
            normalizedName=source.normalized_name,
            searchKeywords=source.search_keywords,
        )
        created_curriculum = await self.repo.create(new_curriculum)

        # Deep clone all subjects
        subject_repo = SubjectRepository()
        source_subjects = await subject_repo.find_all_by_curriculum(source.id, org_id)

        # Build old_subject_id → new_subject_id mapping (for preserving prerequisite links)
        id_mapping: Dict[str, str] = {}
        for sub in source_subjects:
            id_mapping[sub.subject_id] = _generate_id("SUB")

        new_subjects = []
        for sub in source_subjects:
            new_sub_id = id_mapping[sub.subject_id]
            # Remap prerequisite IDs to new IDs
            new_prereqs = [id_mapping.get(p, p) for p in sub.prerequisites]
            new_sub = Subject(
                subjectId=new_sub_id,
                organizationId=org_id,
                curriculumId=created_curriculum.id,
                semesterNumber=sub.semester_number,
                subjectCode=sub.subject_code,
                name=sub.name,
                credits=sub.credits,
                subjectType=sub.subject_type,
                isElective=sub.is_elective,
                electiveGroup=sub.elective_group,
                prerequisites=new_prereqs,
                learningOutcomes=sub.learning_outcomes,
                assessmentScheme=sub.assessment_scheme,
                createdBy=user_id,
                normalizedName=sub.normalized_name,
                searchKeywords=sub.search_keywords,
            )
            new_subjects.append(new_sub)

        if new_subjects:
            await subject_repo.bulk_create(new_subjects)

        logger.info(
            f"Curriculum cloned: {curriculum_id} → {new_curr_id} "
            f"(v{new_version}, {len(new_subjects)} subjects)"
        )
        return created_curriculum

    async def delete(
        self, curriculum_id: str, org_id: PydanticObjectId, user_id: Optional[str] = None
    ) -> bool:
        doc = await self.get(curriculum_id, org_id)
        if doc.status != CurriculumStatus.DRAFT:
            raise CurriculumImmutable()
        await self.repo.delete(doc)
        logger.info(f"Curriculum soft-deleted: {curriculum_id}")
        return True

    async def _recompute_total_credits(
        self, curriculum: Curriculum, org_id: PydanticObjectId
    ) -> None:
        """Recalculate and persist the total credits for a curriculum."""
        subject_repo = SubjectRepository()
        subjects = await subject_repo.find_all_by_curriculum(curriculum.id, org_id)
        total = sum(s.credits for s in subjects)
        await self.repo.update_total_credits(curriculum, total)


class SubjectService:
    def __init__(self):
        self.repo = SubjectRepository()
        self.curr_repo = CurriculumRepository()

    async def _get_curriculum(
        self, curriculum_id: str, org_id: PydanticObjectId
    ) -> Curriculum:
        doc = await self.curr_repo.find_by_id(curriculum_id, org_id)
        if not doc:
            raise CurriculumNotFound(curriculum_id)
        return doc

    async def _validate_prerequisites(
        self,
        subject_id: str,
        prereq_ids: List[str],
        curriculum_oid: PydanticObjectId,
        org_id: PydanticObjectId,
    ) -> None:
        """
        Validate that all prerequisites exist in this curriculum
        and that adding them doesn't create a cycle.
        """
        # Fetch all subjects in curriculum to build graph
        all_subjects = await self.repo.find_all_by_curriculum(curriculum_oid, org_id)
        subject_id_set = {s.subject_id for s in all_subjects}

        # Check that all stated prerequisites actually exist
        for prereq_id in prereq_ids:
            if prereq_id != subject_id and prereq_id not in subject_id_set:
                raise PrerequisiteNotFound(prereq_id)

        # Build adjacency graph (subject → its prerequisites)
        graph: Dict[str, List[str]] = {}
        for sub in all_subjects:
            if sub.subject_id == subject_id:
                # Use the proposed new prerequisites for the subject being created/updated
                graph[subject_id] = prereq_ids
            else:
                graph[sub.subject_id] = sub.prerequisites

        # Ensure new subject is in graph even if it didn't exist yet
        if subject_id not in graph:
            graph[subject_id] = prereq_ids

        # Run DFS cycle detection from the current node
        cycle = _detect_cycle(graph, subject_id)
        if cycle:
            raise PrerequisiteCycleDetected(" → ".join(cycle))

    async def create(
        self,
        org_id: PydanticObjectId,
        curriculum_id: str,
        semester_number: int,
        subject_code: str,
        name: str,
        credits: float,
        subject_type: SubjectType = SubjectType.CORE,
        is_elective: bool = False,
        elective_group: Optional[str] = None,
        prerequisites: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ) -> Subject:
        curriculum = await self._get_curriculum(curriculum_id, org_id)

        # Duplicate code check
        if await self.repo.exists(curriculum.id, subject_code):
            raise DuplicateSubject(subject_code.upper())

        prereqs = prerequisites or []

        # Validate prerequisites (existence + cycle check)
        new_subject_id = _generate_id("SUB")
        if prereqs:
            await self._validate_prerequisites(new_subject_id, prereqs, curriculum.id, org_id)

        subject = Subject(
            subjectId=new_subject_id,
            organizationId=org_id,
            curriculumId=curriculum.id,
            semesterNumber=semester_number,
            subjectCode=subject_code.upper(),
            name=name,
            credits=credits,
            subjectType=subject_type,
            isElective=is_elective,
            electiveGroup=elective_group,
            prerequisites=prereqs,
            createdBy=user_id,
            normalizedName=name.lower().strip(),
            searchKeywords=[w.lower() for w in name.split() if w],
        )
        created = await self.repo.create(subject)

        # Recompute total credits on curriculum
        total = await self._compute_total_credits(curriculum.id, org_id)
        await self.curr_repo.update_total_credits(curriculum, total)

        return created

    async def get(
        self, subject_id: str, curriculum_id: str, org_id: PydanticObjectId
    ) -> Subject:
        curriculum = await self._get_curriculum(curriculum_id, org_id)
        doc = await self.repo.find_by_id(subject_id, curriculum.id, org_id)
        if not doc:
            raise SubjectNotFound(subject_id)
        return doc

    async def list(
        self,
        curriculum_id: str,
        org_id: PydanticObjectId,
        semester_number: Optional[int] = None,
        subject_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Subject], int]:
        curriculum = await self._get_curriculum(curriculum_id, org_id)
        filters: Dict[str, Any] = {}
        if semester_number is not None:
            filters["semesterNumber"] = semester_number
        if subject_type:
            filters["subjectType"] = subject_type

        items = await self.repo.list_by_curriculum(
            curriculum.id, org_id, skip, limit, filters=filters
        )
        total = await self.repo.count_by_curriculum(curriculum.id, org_id)
        return items, total

    async def update(
        self,
        subject_id: str,
        curriculum_id: str,
        org_id: PydanticObjectId,
        update_data: dict,
        user_id: Optional[str] = None,
    ) -> Subject:
        curriculum = await self._get_curriculum(curriculum_id, org_id)
        doc = await self.repo.find_by_id(subject_id, curriculum.id, org_id)
        if not doc:
            raise SubjectNotFound(subject_id)

        # If prerequisites are being updated, re-validate
        if "prerequisites" in update_data:
            await self._validate_prerequisites(
                subject_id, update_data["prerequisites"], curriculum.id, org_id
            )

        update_data["updatedBy"] = user_id
        if "name" in update_data:
            update_data["normalizedName"] = update_data["name"].lower().strip()
            update_data["searchKeywords"] = [w.lower() for w in update_data["name"].split() if w]
        if "subjectCode" in update_data:
            update_data["subjectCode"] = update_data["subjectCode"].upper()

        updated = await self.repo.update(doc, update_data)

        # Recompute credits if changed
        if "credits" in update_data:
            total = await self._compute_total_credits(curriculum.id, org_id)
            await self.curr_repo.update_total_credits(curriculum, total)

        return updated

    async def update_assessment_scheme(
        self,
        subject_id: str,
        curriculum_id: str,
        org_id: PydanticObjectId,
        scheme: AssessmentScheme,
        user_id: Optional[str] = None,
    ) -> Subject:
        # AssessmentScheme model validator already enforces 100% sum
        curriculum = await self._get_curriculum(curriculum_id, org_id)
        doc = await self.repo.find_by_id(subject_id, curriculum.id, org_id)
        if not doc:
            raise SubjectNotFound(subject_id)

        update_data = {
            "assessmentScheme": scheme.model_dump(by_alias=True),
            "updatedBy": user_id,
        }
        return await self.repo.update(doc, update_data)

    async def update_learning_outcomes(
        self,
        subject_id: str,
        curriculum_id: str,
        org_id: PydanticObjectId,
        outcomes: List[LearningOutcome],
        user_id: Optional[str] = None,
    ) -> Subject:
        curriculum = await self._get_curriculum(curriculum_id, org_id)
        doc = await self.repo.find_by_id(subject_id, curriculum.id, org_id)
        if not doc:
            raise SubjectNotFound(subject_id)

        update_data = {
            "learningOutcomes": [lo.model_dump(by_alias=True) for lo in outcomes],
            "updatedBy": user_id,
        }
        return await self.repo.update(doc, update_data)

    async def delete(
        self,
        subject_id: str,
        curriculum_id: str,
        org_id: PydanticObjectId,
        user_id: Optional[str] = None,
    ) -> bool:
        curriculum = await self._get_curriculum(curriculum_id, org_id)
        doc = await self.repo.find_by_id(subject_id, curriculum.id, org_id)
        if not doc:
            raise SubjectNotFound(subject_id)

        # Check if any other subject lists this as a prerequisite
        dependents = await self.repo.find_subjects_with_prerequisite(
            subject_id, curriculum.id
        )
        if dependents:
            dep_names = ", ".join(f"'{s.subject_code}'" for s in dependents)
            raise PrerequisiteInUse(subject_id, dep_names)

        await self.repo.delete(doc)

        # Recompute total credits
        total = await self._compute_total_credits(curriculum.id, org_id)
        await self.curr_repo.update_total_credits(curriculum, total)

        return True

    async def _compute_total_credits(
        self, curriculum_oid: PydanticObjectId, org_id: PydanticObjectId
    ) -> float:
        subjects = await self.repo.find_all_by_curriculum(curriculum_oid, org_id)
        return sum(s.credits for s in subjects)


class CatalogService:
    """Aggregate service for read-heavy, cross-entity catalog queries."""

    def __init__(self):
        self.curr_repo = CurriculumRepository()
        self.sub_repo = SubjectRepository()

    async def get_full_curriculum(
        self, curriculum_id: str, org_id: PydanticObjectId
    ) -> Dict[str, Any]:
        """Return curriculum metadata + all subjects organized by semester."""
        doc = await self.curr_repo.find_by_id(curriculum_id, org_id)
        if not doc:
            raise CurriculumNotFound(curriculum_id)

        subjects = await self.sub_repo.find_all_by_curriculum(doc.id, org_id)

        # Group subjects by semester
        by_semester: Dict[int, List[Subject]] = {}
        for sub in subjects:
            sem = sub.semester_number
            by_semester.setdefault(sem, []).append(sub)

        return {
            "curriculum": doc,
            "semesters": {
                k: sorted(v, key=lambda s: s.subject_code)
                for k, v in sorted(by_semester.items())
            },
            "totalSubjects": len(subjects),
        }

    async def get_prerequisite_graph(
        self, curriculum_id: str, org_id: PydanticObjectId
    ) -> Dict[str, Any]:
        """
        Return a graph-ready data structure for the frontend visualizer.
        
        Format:
        {
          "nodes": [{ "id": "SUB-XXX", "code": "CS101", "name": "...", "semesterNumber": 1, "type": "CORE" }],
          "edges": [{ "from": "SUB-YYY", "to": "SUB-XXX" }]   // "YYY requires XXX"
        }
        """
        curr = await self.curr_repo.find_by_id(curriculum_id, org_id)
        if not curr:
            raise CurriculumNotFound(curriculum_id)

        subjects = await self.sub_repo.find_all_by_curriculum(curr.id, org_id)

        nodes = [
            {
                "id": s.subject_id,
                "code": s.subject_code,
                "name": s.name,
                "semesterNumber": s.semester_number,
                "type": s.subject_type,
                "credits": s.credits,
                "isElective": s.is_elective,
            }
            for s in subjects
        ]

        edges = [
            {"from": s.subject_id, "to": prereq_id}
            for s in subjects
            for prereq_id in s.prerequisites
        ]

        return {
            "curriculumId": curriculum_id,
            "nodes": nodes,
            "edges": edges,
        }
