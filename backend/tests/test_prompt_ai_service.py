import pytest

from app.models.user import Resume
from app.schemas.job import NormalizedJob
from app.schemas.prompt_ai import SourceStatus
from app.services.prompt_ai_service import PromptAIService


class FakeResult:
    def scalars(self):
        return self

    def all(self):
        return []


class FakeDB:
    async def execute(self, _stmt):
        return FakeResult()


class FakeSources:
    async def search(self, keywords, location=None, filters=None, sources=None):
        job = NormalizedJob(
            source="remotive",
            source_job_id="1",
            title="DevOps Engineer",
            company="Acme",
            location="Chennai",
            remote=True,
            description="Kubernetes Docker AWS",
            skills=["Kubernetes", "Docker", "AWS"],
            job_url="https://example.com/1",
            apply_url="https://example.com/1",
        )
        return [job], {"remotive": {"status": "success", "result_count": 1}}


class FailingJobSpy:
    async def discover(self):
        return {"sites": ["naukri", "indeed"]}

    async def search(self, _request):
        raise RuntimeError("down")


@pytest.mark.asyncio
async def test_failed_jobspy_does_not_discard_direct_results(session_factory):
    resume = Resume(
        id="resume-1",
        user_id="user-123",
        file_name="DevOps Resume.pdf",
        raw_text="Kubernetes Docker AWS Terraform",
        extracted_skills=["Kubernetes", "Docker", "AWS", "Terraform"],
        summary="DevOps",
        experience_years=5,
        target_role="DevOps Engineer",
    )
    service = PromptAIService(source_manager=FakeSources(), jobspy=FailingJobSpy())
    result = await service.search(
        "Find DevOps Engineer jobs in Chennai with Kubernetes and Docker.",
        resume,
        FakeDB(),
    )
    assert result.total >= 1
    assert result.results[0].match.score >= 0
    assert "Kubernetes" in result.results[0].match.matched_skills
    assert result.source_status["naukri"].status == "failed"
    assert result.source_status["indeed"].status == "failed"
    assert result.source_status["remotive"].status == "success"
    assert any("Understanding your job requirements" in step for step in result.progress)
    assert any("Removing duplicates" in step for step in result.progress)


def test_source_status_model_keeps_failure_message():
    status = SourceStatus(status="failed", count=0, message="Naukri temporarily unavailable.")
    assert "Naukri" in status.message
