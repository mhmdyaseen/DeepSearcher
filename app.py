from src.agent.research import ResearcherAgent
from src.inference.gemini import ChatGemini
from os import environ
from dotenv import load_dotenv
from pydantic import BaseModel,Field

load_dotenv()

api_key=environ.get('api_key')
llm=ChatGemini(model='gemini-2.0-flash-exp',api_key=api_key,temperature=0)

input=input("Enter a query: ")
agent=ResearcherAgent(search_mode='deep_search',max_queries=1,max_results=1,llm=llm)
response=agent.invoke(input)
print(response['output'])

__all__ = ['agent']
