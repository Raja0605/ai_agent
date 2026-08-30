from app.schemas.job import NormalizedJob
from mcp_agent.job_search import MCPJobSearch


def test_native_filters_keep_unknown_but_reject_explicitly_conflicting_detail():
    # The native MCP has already applied this range/date. Missing normalized
    # fields must not make the backend discard the source-approved row.
    unknown = NormalizedJob(source="mcp", source_job_id="unknown", title="Role", company="Company", description="")
    senior = NormalizedJob(source="mcp", source_job_id="senior", title="Role", company="Company", description="", experience_min=4)
    result = MCPJobSearch._filter_jobs([unknown, senior], {"experience_min": 0, "experience_max": 1}, native_experience=True)
    assert [job.source_job_id for job in result] == ["unknown"]
