import time
from datetime import datetime
import requests


def get_negative_controls(
    concept_ids,
    base_url="https://atlas-demo.ohdsi.org/WebAPI",
    source_key="CEM",
    name_prefix="NC",
    domain="Drug",
    outcome="condition",
    token=None,
    max_polls=40,
    poll_interval=15,
    timeout=180,
):
    name = f"{name_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    if token:
        session.headers["Authorization"] = token

    def req(method, path, **kw):
        r = session.request(method, f"{base_url}/{path.lstrip('/')}", timeout=timeout, **kw)
        r.raise_for_status()
        return r.json() if r.text.strip() else None

    print(f"# [CEM] concept set creating...")
    cs_id = req("POST", "/conceptset/", json={"name": name, "description": ""})["id"]
    print(f"# [CEM] concept set created (name={name}, conceptSetId={cs_id})")

    print(f"# [CEM] adding {len(concept_ids)} concept(s) to set...")
    req("PUT", f"/conceptset/{cs_id}/items", json=[
        {"conceptSetId": cs_id, "conceptId": int(c),
         "isExcluded": 0, "includeDescendants": 1, "includeMapped": 0}
        for c in concept_ids
    ])

    print(f"# [CEM] nc generating...")
    req("POST", f"/evidence/{source_key}/negativecontrols", json={
        "jobName": f"nc_{cs_id}",
        "conceptSetId": cs_id,
        "conceptSetName": name,
        "sourceKey": source_key,
        "conceptsOfInterest": [str(c) for c in concept_ids],
        "conceptDomainId": domain,
        "outcomeOfInterest": outcome,
        "csToInclude": 0, "csToExclude": 0,
        "csToIncludeSQL": "", "csToExcludeSQL": "",
    })

    rows = []
    for attempt in range(1, max_polls + 1):
        rows = req("GET", f"/evidence/{source_key}/negativecontrols/{cs_id}") or []
        if rows:
            print(f"# [CEM] results ready ({len(rows)} rows)")
            break
        print(f"# [CEM] polling... ({attempt}/{max_polls})")
        time.sleep(poll_interval)
    else:
        raise TimeoutError("# [CEM] no results were generated")

    save_path="cem_result.csv"

    rows = list(rows)
    if rows:
        fieldnames = list(rows[0].keys())
        with open(save_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    print(f"# [CEM] done — total {len(result)} / recommended NC {sum(result.values())}")
    print(f"# [CEM] saved full result -> {save_path} ({len(rows)} rows)")
    return result