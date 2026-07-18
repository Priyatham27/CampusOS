import logging

from app.models.org_engine.academic import AcademicYear, Semester, Department, Branch, Section
from app.models.org_engine.curriculum import Program, Course
from app.models.calendar import AcademicCalendar

logger = logging.getLogger("campusos.academic.bootstrap")

class AcademicBootstrapService:
    """
    Service running at lifespan startup to verify database connection health,
    ODM indexes compilation, and collection configuration.
    """
    @classmethod
    async def bootstrap(cls) -> None:
        logger.info("Academic Platform Bootstrap: Initiating readiness verification...")
        
        models_to_check = [
            AcademicYear,
            Semester,
            Department,
            Branch,
            Section,
            Program,
            Course,
            AcademicCalendar
        ]
        
        for model in models_to_check:
            try:
                # Test Beanie registration
                model_name = model.__name__
                # Try simple query count to confirm Beanie compilation
                count = await model.count()
                logger.info(f"Academic Platform Bootstrap: [OK] Model '{model_name}' verified. Total documents in DB: {count}")
            except Exception as e:
                logger.critical(
                    f"Academic Platform Bootstrap: [FAIL] Model '{model.__name__}' failed readiness check. Beanie connection or index issue: {e}"
                )
                # We do not raise here to prevent startup crash, but critical log will warn operators.
        
        logger.info("Academic Platform Bootstrap: Readiness verification completed.")
