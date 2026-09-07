from pathlib import Path

from backend.services.input_loader import load_file


def test_load_csv(tmp_path):

    file_path = tmp_path / "test.csv"

    file_path.write_text(
        "request_id,department,section_id\n"
        "TMS-001,ENGINEERING,SEC01\n",
        encoding="utf-8",
    )

    data = load_file(str(file_path))

    assert len(data) == 1
    assert data[0]["request_id"] == "TMS-001"
    assert data[0]["department"] == "ENGINEERING"
    assert data[0]["section_id"] == "SEC01"