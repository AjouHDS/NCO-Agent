from typing import TypedDict, Dict, Any, List, Literal
from langgraph.graph import START, END, StateGraph
from agents.NCO_agent.curator import build_curator
from agents.NCO_agent.suggestor import build_suggestor
from agents.NCO_agent.constructor import build_constructor
from agents.NCO_agent.diagnostician import build_diagnostician
from agents.NCO_agent import constructor
from core.model_factory import create_llm
from core.config.agent import CONFIG as AGENT_CONFIG


class AgentState(TypedDict, total= False):
    outcomes: Dict[int, Any]
    ingredient_concept_ids: List
    ingredient_concepts: Dict[int, Any]
    diagnostics: int
    is_all_known_ingredient: bool
    cem_result: Dict[int, Any]
    min_patients: int
    step: int
    
  
def build_nodes(db):
    curator_llm = create_llm(AGENT_CONFIG["curator"])
    curator = build_curator(curator_llm, db)
    
    suggestor_llm = create_llm(AGENT_CONFIG["suggestor"])
    suggestor = build_suggestor(suggestor_llm, db)
    
    diagnostician_llm = create_llm(AGENT_CONFIG["diagnostician"])
    diagnostician = build_diagnostician(diagnostician_llm, db)
        
    return curator, suggestor, diagnostician

    
def route_curator(state: AgentState) -> Literal["suggestor", "__end__"]:
    if state.get("is_all_known_ingredient"):
        return "suggestor"
    return END


def route_diagnostician(state: AgentState) -> Literal["suggestor", "__end__"]:
    if state.get("diagnostics"):
        return END
    return "suggestor"

    
def build_graph(curator, suggestor, diagnostician):
    builder = StateGraph(AgentState)
    builder.add_node("curator", curator)
    builder.add_node("suggestor", suggestor)
    builder.add_node("diagnostician", diagnostician)

    builder.add_edge(START, "curator")
    builder.add_conditional_edges(         
        "curator",
        route_curator,
        {"suggestor": "suggestor", END: END}, 
    )
    builder.add_edge("suggestor", "diagnostician")
    builder.add_conditional_edges(
        "diagnostician",
        route_diagnostician,
        {"suggestor": "suggestor", END: END},
    )
    return builder

    
def build_NCO_agent(db):
    nodes = build_nodes(db)
    graph = build_graph(*nodes)
    return graph.compile()