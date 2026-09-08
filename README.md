# NCO-Agent

**Efficient Selection of Negative Control Outcomes Using a Human-in-the-Loop Multi-Agent System**

NCO-Agent is a human-in-the-loop multi-agent system (MAS) that combines evidence-based knowledge with large language model (LLM)-based semantic reasoning to select **institution-specific negative control outcomes (NCOs)** for observational studies built on the OMOP Common Data Model (CDM).

Negative control outcomes are essential for detecting and calibrating systematic error in observational research, but they are typically chosen ad hoc through labor-intensive manual review. Existing tools such as the Common Evidence Model (CEM) rely on simple co-occurrence counts and cannot accommodate cross-institutional heterogeneity in concept mapping and data availability. NCO-Agent addresses these limitations by pairing evidence-based screening with semantic reasoning and reserving human review for the cases that need it most.

---

## Architecture

<img width="3870" height="1378" alt="Group 1289" src="https://github.com/user-attachments/assets/b14f7aca-3451-41e2-b79c-5072d6b63e22" />

The system is orchestrated with [LangGraph](https://github.com/langchain-ai/langgraph) and consists of three sequential agents:

- **Curator** — Validates each input ingredient concept and collects its indications, mechanism of action, contraindications, and adverse events via the FDA [openFDA](https://open.fda.gov/) drug label API, then summarizes the information into a drug-information context using an LLM.
- **Suggester** — Builds a concept pool (each diagnosis concept expanded to its descendants with patient counts), retrieves concepts that meet a minimum patient-count threshold, and reviews candidates through two channels: an evidence-based evaluation from CEM results and an LLM-based semantic evaluation.
- **Diagnostician** — Routes only the concepts where the CEM and LLM evaluations **disagree** to human review (concordant cases are excluded), then assesses the final NCO set for count, patient coverage, and diversity. If coverage is insufficient, it lowers the patient-count threshold and returns to the Suggester. The loop terminates when the set is judged sufficient or all candidates have been reviewed.

By reserving review for discordant cases, the system concentrates human effort where false positives actually occur, making human-in-the-loop curation efficient and scalable for multi-center research.

---

## Requirements

- Python 3.10+
- Access to an OMOP CDM database
- An OpenAI-compatible LLM endpoint (the reference experiments used Qwen3.6-27B (FP8))

Install the dependencies:

```bash
pip install -r requirements.txt
```

---

## Usage

The easiest way to try the system is through the provided notebook, **`run.ipynb`**.

1. Open `run.ipynb`.
2. Set the `ingredient_concept_ids` variable to the OMOP RxNorm standard concept IDs of the ingredient-level drugs you want to generate NCOs for. For example, the reference experiments used:
   - Antidiabetics: metformin (`1503297`), sitagliptin (`1580747`)
   - Anticoagulants: warfarin (`1310149`), apixaban (`43013024`)
   - Antihypertensives: lisinopril (`1308216`), hydrochlorothiazide (`974166`)
3. Run all cells.

The notebook runs the multi-agent pipeline and writes the result to `final_state.json`, which contains the proposed institution-specific NCOs together with the intermediate agent state.

---

## Authors

- **Taeseok Yang** — Department of Biomedical Sciences, Ajou University Graduate School of Medicine, Suwon, Korea · [tsyang0123@ajou.ac.kr](mailto:tsyang0123@ajou.ac.kr)
- **Cheongsu Kim** (Corresponding Author) — Department of Biomedical Informatics, Ajou University School of Medicine, Suwon, Korea · [ted9219@ajou.ac.kr](mailto:ted9219@ajou.ac.kr)

Feel free to reach out with questions or feedback.
