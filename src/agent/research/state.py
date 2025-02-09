from typing import TypedDict

class AgentState(TypedDict):
    input:str
    queries:list[str]
    results:list[dict]
    output:str