import json
import pytest
from mindbench.cli import main
from mindbench.cohort import synthetic_cohort
from mindbench.dashboard import benchmark_html
from mindbench.experiments import synthetic_experiment
from mindbench.schema import ValidationError
from mindbench.synthetic import generate_fixture


def test_synthetic_experiment_dashboard(tmp_path):
    output = tmp_path / "out"
    result = synthetic_experiment(output, n_subjects=12, trials=10, seed=12, reps=15)
    html = (output / "index.html").read_text()
    assert result == json.loads((output / "benchmark.json").read_text())
    assert "Skip to results" in html and "prefers-reduced-motion" in html
    assert "Download complete benchmark JSON" in html
    assert "No medical" in html or "no medical" in html.lower()
    assert "https://" not in html  # offline-only UI, no third-party scripts
    with pytest.raises(ValidationError, match="empty"):
        synthetic_experiment(output)


def test_cli_benchmark_and_align(tmp_path):
    out = tmp_path / "bench"
    assert main(["benchmark", "--output", str(out), "--subjects", "12", "--trials", "10", "--bootstrap", "15"]) == 0
    assert (out / "benchmark.json").is_file()
    root = generate_fixture(tmp_path / "fixture")
    target = tmp_path / "aligned.json"
    assert main(["align", "--root", str(root), "--output", str(target),
                 "--subject", "01", "--session", "01", "--task", "oddball", "--run", "01"]) == 0
    alignment = json.loads(target.read_text())
    assert alignment["qc"]["with_behavior"] == 3
    assert alignment["hardware_sync_verified"] is False
    assert alignment["trials"][0]["latency_s"] == pytest.approx(.2)
