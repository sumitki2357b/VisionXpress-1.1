from collections import Counter

from backend.services.data_loader import load_all_data
from backend.services.data_normalizer import (
    normalize_maintenance_tasks,
)


def test_resource_diagnostics():

    data = load_all_data()

    tasks = normalize_maintenance_tasks(
        data["tms"],
        data["tdms"],
        data["smms"],
    )

    print("\n")
    print("=" * 70)
    print("VISIONXPRESS RESOURCE DIAGNOSTICS")
    print("=" * 70)

    resources = Counter()

    for task in tasks:

        value = task.get("required_resources")

        if value is None:
            continue

        value = str(value).strip()

        if not value:
            continue

        resources[value] += 1

    print("\n")
    print("REQUIRED RESOURCES")
    print("-" * 70)

    for resource, count in resources.most_common():

        print(
            f"{resource:40} count={count}"
        )

    print("\n")
    print(f"Unique resource combinations: {len(resources)}")

    assert len(tasks) > 0