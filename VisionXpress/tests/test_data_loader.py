from backend.services.data_loader import load_all_data


def test_load_all_data():

    data = load_all_data()

    assert "tms" in data
    assert "tdms" in data
    assert "smms" in data
    assert "coa" in data
    assert "existing_blocks" in data
    assert "section_master" in data

    assert len(data["tms"]) > 0
    assert len(data["tdms"]) > 0
    assert len(data["smms"]) > 0
    assert len(data["coa"]) > 0
    assert len(data["existing_blocks"]) > 0
    assert len(data["section_master"]) > 0