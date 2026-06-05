"""Repository pattern for database operations."""

from collections import Counter
from datetime import UTC, datetime, timedelta
import json
import uuid
from typing import Any, Iterable, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, or_

from .models import Skill, SkillTrend, SalaryData, JobPosting, IngestionBatch


class SkillRepository:
    """Repository for skill-related database operations."""
    
    def __init__(self, session: Session):
        """Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
    
    def create_skill(self, name: str, category: str = None) -> Skill:
        """Create a new skill.
        
        Args:
            name: Skill name
            category: Skill category
            
        Returns:
            Created Skill object
        """
        skill = Skill(
            id=str(uuid.uuid4()),
            name=name,
            category=category
        )
        self.session.add(skill)
        self.session.commit()
        return skill
    
    def get_skill_by_name(self, name: str) -> Optional[Skill]:
        """Get skill by name.
        
        Args:
            name: Skill name
            
        Returns:
            Skill object or None
        """
        return self.session.query(Skill).filter(Skill.name == name).first()
    
    def get_or_create_skill(self, name: str, category: str = None) -> Skill:
        """Get skill by name or create if not exists.
        
        Args:
            name: Skill name
            category: Skill category
            
        Returns:
            Skill object
        """
        skill = self.get_skill_by_name(name)
        if not skill:
            skill = self.create_skill(name, category)
        return skill
    
    def get_all_skills(self) -> List[Skill]:
        """Get all skills from database.
        
        Returns:
            List of Skill objects
        """
        return self.session.query(Skill).all()


class SkillTrendRepository:
    """Repository for skill trend data."""
    
    def __init__(self, session: Session):
        """Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
    
    def create_trend(
        self,
        skill_id: str,
        month: datetime,
        occurrences: int,
        percentage: float = None,
        salary_premium: float = None,
        growth_percentage: float = None
    ) -> SkillTrend:
        """Create a new skill trend record.
        
        Args:
            skill_id: Skill ID
            month: Month date
            occurrences: Number of occurrences
            percentage: Percentage of all skills
            salary_premium: Salary premium percentage
            growth_percentage: Month-over-month growth
            
        Returns:
            Created SkillTrend object
        """
        trend = SkillTrend(
            id=str(uuid.uuid4()),
            skill_id=skill_id,
            month=month,
            occurrences=occurrences,
            percentage=percentage,
            salary_premium=salary_premium,
            growth_percentage=growth_percentage
        )
        self.session.add(trend)
        self.session.commit()
        return trend
    
    def get_trend_by_skill_and_month(self, skill_id: str, month: datetime) -> Optional[SkillTrend]:
        """Get trend for specific skill and month.
        
        Args:
            skill_id: Skill ID
            month: Month date
            
        Returns:
            SkillTrend object or None
        """
        return self.session.query(SkillTrend).filter(
            SkillTrend.skill_id == skill_id,
            SkillTrend.month == month
        ).first()
    
    def get_trends_by_skill(self, skill_id: str, limit: int = 12) -> List[SkillTrend]:
        """Get recent trends for a skill.
        
        Args:
            skill_id: Skill ID
            limit: Number of months to retrieve
            
        Returns:
            List of SkillTrend objects
        """
        return self.session.query(SkillTrend).filter(
            SkillTrend.skill_id == skill_id
        ).order_by(desc(SkillTrend.month)).limit(limit).all()
    
    def get_top_trending_skills(self, month: datetime = None, limit: int = 10) -> List[tuple]:
        """Get top skills by occurrences for a month.
        
        Args:
            month: Month date (defaults to latest)
            limit: Number of skills
            
        Returns:
            List of (Skill, SkillTrend) tuples
        """
        if not month:
            # Get latest month with data
            latest = self.session.query(func.max(SkillTrend.month)).scalar()
            month = latest
        
        trends = self.session.query(SkillTrend).filter(
            SkillTrend.month == month
        ).order_by(desc(SkillTrend.occurrences)).limit(limit).all()
        
        return trends


class SalaryRepository:
    """Repository for salary data."""
    
    def __init__(self, session: Session):
        """Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
    
    def create_salary_data(
        self,
        role: str,
        location: str,
        min_salary: int,
        max_salary: int,
        median_salary: int,
        sample_size: int
    ) -> SalaryData:
        """Create salary data record.
        
        Args:
            role: Job role/title
            location: Location
            min_salary: Minimum salary
            max_salary: Maximum salary
            median_salary: Median salary
            sample_size: Number of samples
            
        Returns:
            Created SalaryData object
        """
        salary = SalaryData(
            id=str(uuid.uuid4()),
            role=role,
            location=location,
            min_salary=min_salary,
            max_salary=max_salary,
            median_salary=median_salary,
            mean_salary=(min_salary + max_salary) / 2,
            sample_size=sample_size
        )
        self.session.add(salary)
        self.session.commit()
        return salary
    
    def get_salary_by_role_location(self, role: str, location: str = None) -> Optional[SalaryData]:
        """Get salary data for role and location.
        
        Args:
            role: Job role
            location: Optional location filter
            
        Returns:
            SalaryData object or None
        """
        query = self.session.query(SalaryData).filter(SalaryData.role == role)
        if location:
            query = query.filter(SalaryData.location == location)
        return query.first()
    
    def get_top_paid_roles(self, location: str = None, limit: int = 10) -> List[SalaryData]:
        """Get highest paid roles.
        
        Args:
            location: Optional location filter
            limit: Number of roles
            
        Returns:
            List of SalaryData objects
        """
        query = self.session.query(SalaryData)
        if location:
            query = query.filter(SalaryData.location == location)
        return query.order_by(desc(SalaryData.median_salary)).limit(limit).all()


class IngestionBatchRepository:
    """Repository for auditable ingestion batch metadata."""

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _serialize_source(source: str | list[str]) -> str:
        if isinstance(source, list):
            return json.dumps(source)
        return str(source)

    @staticmethod
    def _deserialize_source(source: str | None) -> str | list[str] | None:
        if source in (None, ""):
            return source
        try:
            parsed = json.loads(str(source))
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except json.JSONDecodeError:
            pass
        return source

    @classmethod
    def to_dict(cls, batch: IngestionBatch) -> dict:
        """Serialize an ingestion batch row."""
        return {
            "id": batch.id,
            "source": cls._deserialize_source(batch.source),
            "status": batch.status,
            "fetched_count": batch.fetched_count or 0,
            "saved_count": batch.saved_count or 0,
            "expired_count": batch.expired_count or 0,
            "started_at": batch.started_at,
            "finished_at": batch.finished_at,
            "error_message": batch.error_message,
            "created_at": batch.created_at,
            "updated_at": batch.updated_at,
        }

    def start_batch(
        self,
        batch_id: str,
        source: str | list[str],
        started_at: datetime,
        status: str = "running",
    ) -> IngestionBatch:
        """Create an ingestion batch audit row."""
        batch = IngestionBatch(
            id=batch_id,
            source=self._serialize_source(source),
            status=status,
            fetched_count=0,
            saved_count=0,
            expired_count=0,
            started_at=started_at,
        )
        self.session.add(batch)
        self.session.commit()
        self.session.refresh(batch)
        return batch

    def complete_batch(
        self,
        batch_id: str,
        status: str,
        fetched_count: int,
        saved_count: int,
        expired_count: int,
        finished_at: datetime,
        error_message: str | None = None,
    ) -> IngestionBatch | None:
        """Update an ingestion batch audit row with terminal counts."""
        batch = self.session.get(IngestionBatch, batch_id)
        if not batch:
            return None
        batch.status = status
        batch.fetched_count = fetched_count
        batch.saved_count = saved_count
        batch.expired_count = expired_count
        batch.finished_at = finished_at
        batch.error_message = error_message
        batch.updated_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(batch)
        return batch

    def fail_batch(
        self,
        batch_id: str,
        error_message: str,
        finished_at: datetime | None = None,
    ) -> IngestionBatch | None:
        """Mark an ingestion batch failed."""
        return self.complete_batch(
            batch_id=batch_id,
            status="failed",
            fetched_count=0,
            saved_count=0,
            expired_count=0,
            finished_at=finished_at or datetime.now(UTC),
            error_message=error_message,
        )

    def get_batch(self, batch_id: str) -> IngestionBatch | None:
        """Fetch one ingestion batch row."""
        return self.session.get(IngestionBatch, batch_id)

    def get_batch_dict(self, batch_id: str) -> dict | None:
        """Fetch one ingestion batch as a dictionary."""
        batch = self.get_batch(batch_id)
        return self.to_dict(batch) if batch else None

    def list_batches(self, limit: int = 20) -> list[IngestionBatch]:
        """Return recent ingestion batches."""
        return (
            self.session.query(IngestionBatch)
            .order_by(desc(IngestionBatch.started_at))
            .limit(limit)
            .all()
        )

    def list_batch_dicts(self, limit: int = 20) -> list[dict]:
        """Return recent ingestion batches as dictionaries."""
        return [self.to_dict(batch) for batch in self.list_batches(limit=limit)]


class JobPostingRepository:
    """Repository for job posting data."""

    WRITABLE_FIELDS = {
        "title",
        "company",
        "location",
        "country",
        "city",
        "federal_state",
        "salary_min",
        "salary_max",
        "salary_period",
        "salary_is_estimated",
        "salary_confidence",
        "job_type",
        "employment_type",
        "description",
        "required_skills",
        "source",
        "source_posting_id",
        "url",
        "application_url",
        "company_career_url",
        "remote_status",
        "role_type",
        "occupation_group",
        "experience_level",
        "source_legal_basis",
        "ingestion_batch_id",
        "posted_date",
        "posted_at",
        "expires_at",
        "last_seen_at",
        "is_expired",
    }
    
    def __init__(self, session: Session):
        """Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session

    @staticmethod
    def _normalize_datetime(value: Any) -> datetime | None:
        """Normalize datetime-like values before writing them to SQLAlchemy."""
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(normalized)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except ValueError:
                return None
        return value

    @staticmethod
    def _normalize_skills(value: Any) -> str | None:
        """Store skills as compact JSON text until a full job_skills relation is used."""
        if value in (None, ""):
            return None
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return json.dumps([str(item) for item in parsed])
            except json.JSONDecodeError:
                pass
            return json.dumps([skill.strip() for skill in value.split(";") if skill.strip()])
        if isinstance(value, list):
            return json.dumps([str(item) for item in value])
        return json.dumps([str(value)])

    @staticmethod
    def _deserialize_skills(value: Any) -> list[str]:
        """Return skills in the API/search shape."""
        if value in (None, ""):
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        try:
            parsed = json.loads(str(value))
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except json.JSONDecodeError:
            pass
        return [skill.strip() for skill in str(value).split(";") if skill.strip()]

    @classmethod
    def _record_from_job(cls, job: Any) -> dict:
        """Convert a Pydantic model, ORM model, or dict into repository fields."""
        if isinstance(job, dict):
            record = dict(job)
        elif hasattr(job, "model_dump"):
            record = job.model_dump(mode="python")
        elif hasattr(job, "dict"):
            record = job.dict()
        else:
            record = {
                field: getattr(job, field)
                for field in ["id", *sorted(cls.WRITABLE_FIELDS)]
                if hasattr(job, field)
            }

        for field in ["posted_date", "posted_at", "expires_at", "last_seen_at"]:
            if field in record:
                record[field] = cls._normalize_datetime(record[field])
        if "required_skills" in record:
            record["required_skills"] = cls._normalize_skills(record["required_skills"])
        if "salary_min" in record and record["salary_min"] is not None:
            record["salary_min"] = int(float(record["salary_min"]))
        if "salary_max" in record and record["salary_max"] is not None:
            record["salary_max"] = int(float(record["salary_max"]))
        if "country" not in record or not record.get("country"):
            record["country"] = "Germany"
        if "posted_date" not in record or record.get("posted_date") is None:
            record["posted_date"] = datetime.now(UTC)
        if "is_expired" not in record:
            record["is_expired"] = False
        return record

    @classmethod
    def to_dict(cls, job: JobPosting) -> dict:
        """Serialize a database job into the normalized search/API shape."""
        return {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "country": job.country,
            "city": job.city,
            "federal_state": job.federal_state,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_period": job.salary_period,
            "salary_is_estimated": bool(job.salary_is_estimated),
            "salary_confidence": job.salary_confidence,
            "job_type": job.job_type,
            "employment_type": job.employment_type,
            "description": job.description,
            "required_skills": cls._deserialize_skills(job.required_skills),
            "source": job.source,
            "source_posting_id": job.source_posting_id,
            "url": job.url,
            "application_url": job.application_url,
            "company_career_url": job.company_career_url,
            "remote_status": job.remote_status,
            "role_type": job.role_type,
            "occupation_group": job.occupation_group,
            "experience_level": job.experience_level,
            "source_legal_basis": job.source_legal_basis,
            "ingestion_batch_id": job.ingestion_batch_id,
            "posted_date": job.posted_date,
            "posted_at": job.posted_at,
            "expires_at": job.expires_at,
            "last_seen_at": job.last_seen_at,
            "is_expired": bool(job.is_expired),
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }

    def _base_active_query(self):
        """Return the base query used for user-facing job search."""
        return self.session.query(JobPosting).filter(JobPosting.is_expired.is_(False))

    def _find_existing(self, record: dict) -> JobPosting | None:
        """Find an existing posting by provider identity, then by platform id."""
        source = record.get("source")
        source_posting_id = record.get("source_posting_id")
        if source and source_posting_id:
            existing = self.session.query(JobPosting).filter(
                JobPosting.source == source,
                JobPosting.source_posting_id == source_posting_id,
            ).first()
            if existing:
                return existing
        if record.get("id"):
            return self.session.get(JobPosting, record["id"])
        return None

    def save_job(self, job: Any, commit: bool = True) -> JobPosting:
        """Save one normalized provider result, deduplicating by source identity."""
        record = self._record_from_job(job)
        existing = self._find_existing(record)
        if existing:
            for field, value in record.items():
                if field in self.WRITABLE_FIELDS:
                    setattr(existing, field, value)
            existing.updated_at = datetime.now(UTC)
            saved = existing
        else:
            record.setdefault("id", str(uuid.uuid4()))
            allowed_record = {
                field: value
                for field, value in record.items()
                if field == "id" or field in self.WRITABLE_FIELDS
            }
            saved = JobPosting(**allowed_record)
            self.session.add(saved)
        if commit:
            self.session.commit()
            self.session.refresh(saved)
        return saved

    def save_jobs(self, jobs: Iterable[Any]) -> list[JobPosting]:
        """Save a batch of normalized provider results."""
        saved = [self.save_job(job, commit=False) for job in jobs]
        self.session.commit()
        for job in saved:
            self.session.refresh(job)
        return saved

    def get_job_by_id(self, job_id: str, include_expired: bool = False) -> JobPosting | None:
        """Fetch one posting by platform id."""
        query = self.session.query(JobPosting).filter(JobPosting.id == str(job_id))
        if not include_expired:
            query = query.filter(JobPosting.is_expired.is_(False))
        return query.first()

    def get_job_dict_by_id(self, job_id: str, include_expired: bool = False) -> dict | None:
        """Fetch one posting by id in API/search shape."""
        job = self.get_job_by_id(job_id, include_expired=include_expired)
        return self.to_dict(job) if job else None

    def query_jobs(
        self,
        query: str = "",
        location: str | None = None,
        work_mode: str | None = None,
        company: str | None = None,
        role_type: str | None = None,
        employment_type: str | None = None,
        limit: int = 25,
        include_expired: bool = False,
    ) -> list[JobPosting]:
        """Query jobs by filters and lightweight text search."""
        db_query = self.session.query(JobPosting)
        if not include_expired:
            db_query = db_query.filter(JobPosting.is_expired.is_(False))

        if location:
            like = f"%{location.strip()}%"
            db_query = db_query.filter(or_(
                JobPosting.location.ilike(like),
                JobPosting.city.ilike(like),
                JobPosting.federal_state.ilike(like),
            ))
        if work_mode and work_mode.lower() != "any":
            db_query = db_query.filter(JobPosting.remote_status.ilike(work_mode.strip()))
        if company:
            db_query = db_query.filter(JobPosting.company.ilike(f"%{company.strip()}%"))
        if role_type:
            db_query = db_query.filter(JobPosting.role_type.ilike(f"%{role_type.strip()}%"))
        if employment_type:
            db_query = db_query.filter(JobPosting.employment_type.ilike(f"%{employment_type.strip()}%"))
        if query:
            terms = [term for term in query.strip().split() if term]
            for term in terms:
                like = f"%{term}%"
                db_query = db_query.filter(or_(
                    JobPosting.title.ilike(like),
                    JobPosting.company.ilike(like),
                    JobPosting.location.ilike(like),
                    JobPosting.description.ilike(like),
                    JobPosting.role_type.ilike(like),
                    JobPosting.job_type.ilike(like),
                    JobPosting.required_skills.ilike(like),
                ))

        return db_query.order_by(desc(JobPosting.posted_date), JobPosting.title).limit(limit).all()

    def query_job_dicts(self, **filters: Any) -> list[dict]:
        """Query jobs and return API/search dictionaries."""
        return [self.to_dict(job) for job in self.query_jobs(**filters)]

    def list_jobs(self, limit: int | None = None, include_expired: bool = False) -> list[JobPosting]:
        """List jobs for service consumers and analytics."""
        query = self.session.query(JobPosting)
        if not include_expired:
            query = query.filter(JobPosting.is_expired.is_(False))
        query = query.order_by(desc(JobPosting.posted_date), JobPosting.title)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def list_job_dicts(self, limit: int | None = None, include_expired: bool = False) -> list[dict]:
        """List jobs as normalized dictionaries."""
        return [self.to_dict(job) for job in self.list_jobs(limit=limit, include_expired=include_expired)]

    def mark_expired(self, reference_time: datetime | None = None) -> int:
        """Mark jobs expired when their expiry timestamp is in the past."""
        reference_time = reference_time or datetime.now(UTC)
        jobs = self.session.query(JobPosting).filter(
            JobPosting.expires_at.is_not(None),
            JobPosting.expires_at < reference_time,
            JobPosting.is_expired.is_(False),
        ).all()
        for job in jobs:
            job.is_expired = True
            job.updated_at = datetime.now(UTC)
        self.session.commit()
        return len(jobs)

    @staticmethod
    def _similarity_score(target: JobPosting, candidate: JobPosting) -> int:
        """Score related jobs using stable structured fields and skills."""
        if target.id == candidate.id:
            return 0
        score = 0
        if target.role_type and target.role_type == candidate.role_type:
            score += 5
        if target.occupation_group and target.occupation_group == candidate.occupation_group:
            score += 4
        if target.location and target.location == candidate.location:
            score += 3
        if target.remote_status and target.remote_status == candidate.remote_status:
            score += 2
        target_skills = {skill.lower() for skill in JobPostingRepository._deserialize_skills(target.required_skills)}
        candidate_skills = {skill.lower() for skill in JobPostingRepository._deserialize_skills(candidate.required_skills)}
        score += len(target_skills & candidate_skills)
        return score

    def query_similar_jobs(self, job_id: str, limit: int = 5) -> list[JobPosting]:
        """Find jobs similar to a selected posting."""
        target = self.get_job_by_id(job_id)
        if not target:
            return []
        candidates = self._base_active_query().filter(JobPosting.id != target.id).all()
        ranked = [
            (self._similarity_score(target, candidate), candidate)
            for candidate in candidates
        ]
        ranked = [item for item in ranked if item[0] > 0]
        ranked.sort(key=lambda item: (-item[0], item[1].title or ""))
        return [candidate for _, candidate in ranked[:limit]]

    def query_similar_job_dicts(self, job_id: str, limit: int = 5) -> list[dict]:
        """Find similar jobs and return API/search dictionaries."""
        return [self.to_dict(job) for job in self.query_similar_jobs(job_id, limit=limit)]

    def get_facets(self) -> dict:
        """Return filter facets from persisted active jobs."""
        jobs = self.list_job_dicts()
        salary_midpoints = [
            (float(job["salary_min"]) + float(job["salary_max"])) / 2
            for job in jobs
            if job.get("salary_min") is not None and job.get("salary_max") is not None
        ]
        return {
            "total_jobs": len(jobs),
            "locations": Counter(job.get("location") for job in jobs if job.get("location")),
            "role_types": Counter(job.get("role_type") for job in jobs if job.get("role_type")),
            "companies": Counter(job.get("company") for job in jobs if job.get("company")),
            "work_modes": Counter(job.get("remote_status") for job in jobs if job.get("remote_status")),
            "job_types": Counter(job.get("job_type") for job in jobs if job.get("job_type")),
            "salary_midpoints": salary_midpoints,
        }
    
    def create_job(
        self,
        title: str,
        company: str,
        location: str,
        salary_min: int = None,
        salary_max: int = None,
        salary_period: str = None,
        salary_is_estimated: bool = False,
        salary_confidence: float = None,
        job_type: str = None,
        employment_type: str = None,
        description: str = None,
        source: str = None,
        source_posting_id: str = None,
        url: str = None,
        application_url: str = None,
        company_career_url: str = None,
        country: str = "Germany",
        city: str = None,
        federal_state: str = None,
        remote_status: str = None,
        role_type: str = None,
        occupation_group: str = None,
        experience_level: str = None,
        source_legal_basis: str = None,
        ingestion_batch_id: str = None,
        posted_date: datetime = None,
        posted_at: datetime = None,
        expires_at: datetime = None,
        last_seen_at: datetime = None,
        is_expired: bool = False,
    ) -> JobPosting:
        """Create a job posting record.
        
        Args:
            title: Job title
            company: Company name
            location: Job location
            salary_min: Minimum salary
            salary_max: Maximum salary
            job_type: Job type (full-time, part-time, etc.)
            description: Job description
            source: Data source (linkedin, kaggle, etc.)
            url: Job URL
            posted_date: When job was posted
            
        Returns:
            Created JobPosting object
        """
        job = JobPosting(
            id=str(uuid.uuid4()),
            title=title,
            company=company,
            location=location,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_period=salary_period,
            salary_is_estimated=salary_is_estimated,
            salary_confidence=salary_confidence,
            job_type=job_type,
            employment_type=employment_type,
            description=description,
            source=source,
            source_posting_id=source_posting_id,
            url=url,
            application_url=application_url,
            company_career_url=company_career_url,
            country=country,
            city=city,
            federal_state=federal_state,
            remote_status=remote_status,
            role_type=role_type,
            occupation_group=occupation_group,
            experience_level=experience_level,
            source_legal_basis=source_legal_basis,
            ingestion_batch_id=ingestion_batch_id,
            posted_date=posted_date or datetime.now(UTC),
            posted_at=posted_at,
            expires_at=expires_at,
            last_seen_at=last_seen_at,
            is_expired=is_expired,
        )
        self.session.add(job)
        self.session.commit()
        return job
    
    def get_recent_jobs(self, days: int = 30, limit: int = 100) -> List[JobPosting]:
        """Get recent job postings.
        
        Args:
            days: Get jobs from last N days
            limit: Maximum number of jobs
            
        Returns:
            List of JobPosting objects
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        return self.session.query(JobPosting).filter(
            JobPosting.posted_date >= cutoff_date
        ).order_by(desc(JobPosting.posted_date)).limit(limit).all()
    
    def get_jobs_by_title(self, title: str, limit: int = 50) -> List[JobPosting]:
        """Get jobs by title.
        
        Args:
            title: Job title to search
            limit: Maximum number of jobs
            
        Returns:
            List of JobPosting objects
        """
        return self.session.query(JobPosting).filter(
            JobPosting.title.ilike(f"%{title}%")
        ).limit(limit).all()
    
    def count_jobs_by_location(self) -> List[tuple]:
        """Count jobs by location.
        
        Returns:
            List of (location, count) tuples
        """
        return self.session.query(
            JobPosting.location,
            func.count(JobPosting.id)
        ).group_by(JobPosting.location).all()
