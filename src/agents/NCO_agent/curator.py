from typing import TypedDict, Dict, Any, List, Literal
from langgraph.graph import START, END, StateGraph
from core.prompt.curator import SUMMARIZE_PROMPT
from core.utils import parse_json_dict
from core.config.cdm import config as cdm_config
from core import openfda
import json
import tiktoken
_enc = tiktoken.get_encoding("cl100k_base")


CONCEPT_TABLE = cdm_config["concept_table"]


def count_tokens(obj):
    if not isinstance(obj, str):
        obj = json.dumps(obj, ensure_ascii=False)
    return len(_enc.encode(obj))


class AgentState(TypedDict):
    ingredient_concept_ids: List
    ingredient_concepts: Dict[int, Any]
    is_all_known_ingredient: bool


def build_nodes(llm, db):

    def check_valid_ingredient_concept_id(ingredient_concept_id):
        sql = f"""
        SELECT COUNT(*) AS cnt
        FROM {CONCEPT_TABLE} c
        WHERE c.concept_id = {int(ingredient_concept_id)}
            AND c.concept_class_id = 'Ingredient'
            AND c.standard_concept = 'S'
        """
        success, rows, error = db.query(sql)
        if not success:
            print(f"Error validating concept {ingredient_concept_id}: {error}")
            return False
        return bool(rows) and rows[0]["cnt"] > 0

    def get_ingredient_name(ingredient_concept_id):
        sql = f"""
        SELECT c.concept_name
        FROM {CONCEPT_TABLE} c
        WHERE c.concept_id = {int(ingredient_concept_id)}
        """
        success, rows, error = db.query(sql)
        if not success:
            print(f"Error fetching name for concept {ingredient_concept_id}: {error}")
            return ""
        return rows[0]["concept_name"] if rows else ""

    def collect_ingredient_name(state: AgentState):
        ingredient_concept_ids = state["ingredient_concept_ids"]
        print("# curating...")
        print("\n# collect_ingredient_name...")
        print(f"# Resolving names for {len(ingredient_concept_ids)} concept id(s)")

        is_all_known_ingredient = True
        ingredient_concepts = {}

        for ingredient_concept_id in ingredient_concept_ids:
            print(f"# [validate] concept_id={ingredient_concept_id}")
            is_valid = check_valid_ingredient_concept_id(ingredient_concept_id)

            if not is_valid:
                is_all_known_ingredient = False
                print(f"# [skip] Invalid or unknown ingredient concept id: {ingredient_concept_id}")
                break

            name = get_ingredient_name(ingredient_concept_id)
            ingredient_concepts[ingredient_concept_id] = {"ingredient_name": name}
            print(f"# [ok] {ingredient_concept_id} -> {name}")

        print(f"# [done] collected={len(ingredient_concepts)} is_all_known={is_all_known_ingredient}")

        return {
            "ingredient_concepts": ingredient_concepts,
            "is_all_known_ingredient": is_all_known_ingredient,
        }

    def collect_ingredient_info(state: AgentState):
        ingredient_concept_ids = state["ingredient_concept_ids"]
        ingredient_concepts = state["ingredient_concepts"]

        print("\n# collect_ingredient_info...")
        print(f"# Curating openFDA info for {len(ingredient_concept_ids)} ingredient(s)")

        is_all_known_ingredient = True

        for ingredient_concept_id in ingredient_concept_ids:
            ingredient_name = ingredient_concepts[ingredient_concept_id]["ingredient_name"]

            print(f"# [fetch] openFDA <- {ingredient_name}")
            results = openfda.collect([ingredient_name])
            result = results[0]

            found = result["found"]
            if not found:
                is_all_known_ingredient = False
                print(f"# [miss] Ingredient not found: {ingredient_name}")
                break

            drug_info = result["drug_info"]

            indications_raw = drug_info["indications"]
            mechanism_of_action_raw = drug_info["mechanism_of_action"]
            contraindications_raw = drug_info["contraindications"]
            adverse_effects_raw = drug_info["adverse_effects"]

            indications = indications_raw[0]["text"] if indications_raw else ""
            mechanism_of_action = mechanism_of_action_raw[0]["text"] if mechanism_of_action_raw else ""
            contraindications = contraindications_raw[0]["text"] if contraindications_raw else ""

            adverse_effects = ""
            filled_sections = []
            for section in ["boxed_warning", "adverse_reactions", "warnings_and_precautions", "warnings"]:
                section_data = adverse_effects_raw.get(section, [])
                if len(section_data) != 0:
                    adverse_effects += "\n# " + section + "\n"
                    adverse_effects += section_data[0]["text"]
                    filled_sections.append(section)

            ingredient_concepts[ingredient_concept_id] = {
                "ingredient_name": ingredient_name,
                "indications": indications,
                "mechanism_of_action": mechanism_of_action,
                "contraindications": contraindications,
                "adverse_effects": adverse_effects,
            }

            print(f"# [ok] {ingredient_name} | "
                  f"indications={'Y' if indications else 'N'} "
                  f"moa={'Y' if mechanism_of_action else 'N'} "
                  f"contra={'Y' if contraindications else 'N'} "
                  f"adverse_sections={filled_sections}")

        print(f"# [done] is_all_known={is_all_known_ingredient}")

        return {
            "ingredient_concepts": ingredient_concepts,
            "is_all_known_ingredient": is_all_known_ingredient,
        }

    def summarize(state: AgentState):
        ingredient_concept_ids = state["ingredient_concept_ids"]
        ingredient_concepts = state["ingredient_concepts"]

        print("\n# summarize...")
        print(f"# Summarizing {len(ingredient_concept_ids)} ingredient(s)")

        for ingredient_concept_id in ingredient_concept_ids:
            ingredient_info = ingredient_concepts[ingredient_concept_id]

            before = count_tokens(ingredient_info)

            print(f"# [llm] summarizing {ingredient_info['ingredient_name']} ...")
            response = llm.invoke(SUMMARIZE_PROMPT, {"drug_info": ingredient_info})
            summarized = parse_json_dict(response)

            after = count_tokens(summarized)
            reduction = (1 - after / before) * 100 if before else 0.0

            ingredient_concepts[ingredient_concept_id] = summarized

            print(f"# [tokens] before={before:,} -> after={after:,} "
                  f"({reduction:+.1f}% reduction)")

        print("# [done] summarize complete")

        return {
            "ingredient_concepts": ingredient_concepts,
        }

    return collect_ingredient_name, collect_ingredient_info, summarize


def route_if_known(state: AgentState):
    if not state.get("is_all_known_ingredient", False):
        print("# [route] unknown ingredient detected -> END")
        return "end"
    print("# [route] all known -> continue")
    return "continue"


def build_graph(collect_ingredient_name, collect_ingredient_info, summarize):
    builder = StateGraph(AgentState)

    builder.add_node("collect_name", collect_ingredient_name)
    builder.add_node("collect_info", collect_ingredient_info)
    builder.add_node("summarize", summarize)

    builder.add_edge(START, "collect_name")
    builder.add_conditional_edges(
        "collect_name",
        route_if_known,
        {
            "continue": "collect_info",
            "end": END,
        },
    )
    builder.add_conditional_edges(
        "collect_info",
        route_if_known,
        {
            "continue": "summarize",
            "end": END,
        },
    )
    builder.add_edge("summarize", END)
    return builder


def build_curator(llm, db):
    collect_ingredient_name, collect_ingredient_info, summarize = build_nodes(llm, db)
    graph = build_graph(collect_ingredient_name, collect_ingredient_info, summarize)
    return graph.compile()