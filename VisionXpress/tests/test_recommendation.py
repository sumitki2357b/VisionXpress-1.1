from backend.optimization.recommendation import build_recommendation


def test_build_recommendation():

    assignments = [
        {
            "task_id": "TMS-001",
            "department": "ENGINEERING",
            "section_id": "SEC01",
            "block_start": "05:00",
            "block_end": "07:00",
            "block_duration_minutes": 120,
            "coordination": True,
        },
        {
            "task_id": "SMMS-001",
            "department": "SIGNAL",
            "section_id": "SEC01",
            "block_start": "05:00",
            "block_end": "07:00",
            "block_duration_minutes": 120,
            "coordination": True,
        },
    ]

    result = build_recommendation(assignments)

    assert result["status"] == "RECOMMENDED"

    assert result["recommended_block"]["section_id"] == "SEC01"
    assert result["recommended_block"]["start_time"] == "05:00"
    assert result["recommended_block"]["end_time"] == "07:00"

    assert result["coordination"]["enabled"] is True
    assert result["coordination"]["task_count"] == 2

    assert "ENGINEERING" in result["coordination"]["departments"]
    assert "SIGNAL" in result["coordination"]["departments"]

    assert result["bdms_action"]["status"] == "PENDING_BDMS_APPROVAL"
    assert "ACCEPT" in result["bdms_action"]["options"]
    assert "DECLINE" in result["bdms_action"]["options"]
    assert "REQUEST_BETTERMENT" in result["bdms_action"]["options"]
    assert "MODIFY" in result["bdms_action"]["options"]