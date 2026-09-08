import warnings
warnings.filterwarnings("ignore")
import sys
from pathlib import Path
sys.path.append(str(Path.cwd() / "src"))
from dotenv import load_dotenv
load_dotenv() 
from agents.NCO_agent.agent import build_NCO_agent
from agents.NCO_agent import agent as NCO_agent
from core.database import Database
from core.config.database import config as database_config

def build_initial_state(ingredient_concept_ids):
    state: NCO_agent.AgentState = {
        "ingredient_concept_ids": ingredient_concept_ids,
        "min_patients": 100000,
        "step": 10000,
    }
    return state


def main(ingredient_concept_ids):
    db = Database(database_config)
    NCO_agent = build_NCO_agent(db)
    state = build_initial_state(ingredient_concept_ids)
    final_state = NCO_agent.invoke(state)
    db.close()
    
    return final_state