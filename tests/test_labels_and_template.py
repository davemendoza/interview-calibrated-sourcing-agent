from datetime import date

from icsa import identity, scorer
from icsa.config import check_role, load_role
from icsa.models import Evidence

from conftest import ROOT


def test_labels_and_domain_name_come_from_the_role_file(role):
    role["labels"].update({"domain_name": "robotics", "pending": "Needs research", "tier2": "Worth a call"})
    role["requirements"] = [{"id": "d", "label": "Robotics work", "kind": "domain", "terms": ["ros2", "motion planning"]}]
    neutral = Evidence("Ana Cruz", "commit", "40 commits to example/photo-app", "https://github.com/example/photo-app",
                       "github:acruz", f"{date.today().year}-01-01", "PixelCo", None, "acruz", [], None, "photo", 40)
    robot = Evidence("Lee Chen", "paper", "Author: motion planning at scale", "https://doi.org/10.1/r",
                     "openalex:A9", f"{date.today().year}-02-01", "RoboLab")
    out = {c.name: c for c in scorer.score_all(identity.resolve([neutral, robot]), role)}
    assert out["Ana Cruz"].tier == "Needs research"
    assert out["Ana Cruz"].tier_reasons == ["No robotics evidence found yet; not scored"]
    assert out["Lee Chen"].recommendation == "Worth a call"
    assert "Robotics evidence" in out["Lee Chen"].tier_reasons[0]


def test_fintech_example_is_complete(role):
    assert check_role(role) == []


def test_template_flags_every_unfilled_customize_field():
    problems = check_role(load_role(ROOT / "config/roles/TEMPLATE_role.toml", calibration=None))
    text = " ".join(problems)
    assert "domain_name is empty" in text
    assert "role.title is empty" in text
    assert "no domain requirement terms" in text
