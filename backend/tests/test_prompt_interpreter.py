from app.services.prompt_interpreter import interpret_prompt


def test_title_and_city_are_read_without_inventing_skills():
    result = interpret_prompt("Find DevOps Engineer jobs in Chennai.")
    assert result.keywords == ["DevOps Engineer"]
    assert result.locations == ["Chennai"]
    assert result.remote is None
    assert "Terraform" not in result.skills


def test_remote_india_and_named_skills():
    result = interpret_prompt("Find remote DevOps jobs in India with Kubernetes and Docker.")
    assert result.keywords == ["DevOps"]
    assert result.remote is True
    assert result.country == "india"
    assert {"Kubernetes", "Docker"} <= set(result.skills)


def test_experience_and_skill_list_without_invented_title():
    result = interpret_prompt(
        "Find jobs requiring AWS, Docker, Kubernetes and Terraform with 3+ years experience."
    )
    assert result.experience_min == 3
    assert {"AWS", "Docker", "Kubernetes", "Terraform"} <= set(result.skills)


def test_posted_within_three_days():
    result = interpret_prompt("Find DevOps jobs posted within the last 3 days.")
    assert result.hours_old == 72
    assert result.posted_after is not None
    assert "DevOps" in result.keywords[0]


def test_hybrid_is_noted_without_forcing_remote():
    result = interpret_prompt("Find Python backend jobs in Chennai or Bangalore suitable for my resume.")
    assert "Chennai" in result.locations
    assert "Bengaluru" in result.locations
    assert result.remote is None
    assert "Python" in result.skills
