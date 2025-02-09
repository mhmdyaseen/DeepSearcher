from src.agent.research.utils import read_markdown_file, scrape, extract_python_code
from langgraph.graph import StateGraph,END,START
from src.message import SystemMessage,HumanMessage
from src.agent.research.state import AgentState
from src.inference import BaseInference
from duckduckgo_search import DDGS
from src.agent import BaseAgent
from datetime import datetime
from ast import literal_eval
from typing import Literal
import nest_asyncio
import asyncio


class ResearcherAgent(BaseAgent):
    def __init__(self,search_mode:Literal['deep_search','quick_search']='quick_search',max_queries:int=5,max_results:int=5,lang:str='en-US',llm:BaseInference=None,verbose=False):
        self.llm=llm
        self.verbose=verbose
        self.lang=lang
        self.search_mode=search_mode
        self.max_queries=max_queries
        self.max_results=max_results
        self.date=datetime.now()
        self.ddgs=DDGS()
        self.graph=self.create_graph()
    
    async def query(self,state:AgentState):
        system_prompt=read_markdown_file('./src/agent/research/prompt/query.md')
        user_prompt=f"## User Query:\n{state.get('input')}"
        parameters={'max_queries':self.max_queries,'date':self.date,'lang':self.lang}
        messages=[SystemMessage(system_prompt.format(**parameters)),HumanMessage(user_prompt)]
        llm_response=await self.llm.async_invoke(messages)
        code=extract_python_code(llm_response.content)
        queries=literal_eval(code)
        return {**state,'queries':queries}
        
    async def quick_search(self,state:AgentState):
        # Fetch results for the query
        async def fetch_results(query):
            responses = self.ddgs.text(query, max_results=self.max_results)
            await asyncio.sleep(1)
            return list(responses)
        results = await asyncio.gather(*(fetch_results(query) for query in state.get('queries')))
        results = [result for sublist in results for result in sublist]
        return {**state, 'results': results}
    
    async def deep_search(self, state: AgentState):
        async def fetch_results_and_scrape(query):
            # Fetch results for the query
            responses = self.ddgs.text(query, max_results=self.max_results)
            results = {response.get('href'):{'title': response.get('title'),'href': response.get('href')} for response in responses}.values()

            # Scrape the content for each URL
            tasks = []
            for result in results:
                url = result.get('href')
                tasks.append(asyncio.to_thread(scrape, url))
            
            scraped_results = await asyncio.gather(*tasks)
            for result,scraped_result in zip(results,scraped_results):
                title = result.get('title','')
                url=result.get('href','')
                result['body'] = scraped_result if scraped_result else ''
                await asyncio.sleep(1)
            return list(results)

        all_results = await asyncio.gather(*(fetch_results_and_scrape(query) for query in state.get('queries')))
        # Flatten the list of results
        results = [result for sublist in all_results for result in sublist]
        return {**state, 'results': results}
    
    async def response(self,state:AgentState):
        results='\n'.join([f"Title: {result['title']}\nContent: {result['body']}\nSource: {result['href']}\n" for result in state.get('results')])
        system_prompt=read_markdown_file('./src/agent/research/prompt/response.md')
        user_prompt=f"## Web Search Results:\n{results}\n\n## User Query:\n{state.get('input')}"
        messages=[SystemMessage(system_prompt),HumanMessage(user_prompt)]
        llm_response=await self.llm.async_invoke(messages)
        output=llm_response.content
        return {**state,'output':output}
        
    def search_strategy(self,state:AgentState):
        return self.search_mode

    def create_graph(self):
        graph=StateGraph(AgentState)
        graph.add_node('query',self.query)
        graph.add_node('quick_search',self.quick_search)
        graph.add_node('deep_search',self.deep_search)
        graph.add_node('response',self.response)

        graph.add_edge(START,'query')
        graph.add_conditional_edges('query',self.search_strategy)
        graph.add_edge('quick_search','response')
        graph.add_edge('deep_search','response')
        graph.add_edge('response',END)

        return graph.compile(debug=False)

    async def async_invoke(self, input:str):
        state={
            'input':input,
            'max_queries':self.max_queries,
            'results':[],
            'output':''
        }
        graph_response=await self.graph.ainvoke(state)
        return graph_response
    
    def invoke(self, input: str):
        try:
            # If there's no running event loop, use asyncio.run
            return asyncio.run(self.async_invoke(input))
        except RuntimeError:
            nest_asyncio.apply()  # Allow nested event loops in notebooks
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.async_invoke(input))

    def stream(self, input):
        pass



# from src.agent.research.utils import read_markdown_file, scrape, extract_python_code
# from langgraph.graph import StateGraph, END, START
# from src.message import SystemMessage, HumanMessage
# from src.agent.research.state import AgentState
# from src.inference import BaseInference
# from duckduckgo_search import DDGS
# from src.agent import BaseAgent
# from datetime import datetime
# from ast import literal_eval
# from typing import Literal
# import asyncio

# class ResearcherAgent(BaseAgent):
#     def __init__(self, search_mode: Literal['deep_search', 'quick_search'] = 'quick_search',
#                  max_queries: int = 5, max_results: int = 5, lang: str = 'en-US', llm: BaseInference = None):
#         self.llm = llm
#         self.lang = lang
#         self.search_mode = search_mode
#         self.max_queries = max_queries
#         self.max_results = max_results
#         self.date = datetime.now()
#         self.ddgs = DDGS()
#         self.graph = self.create_graph()

#     async def query(self, state: AgentState):
#         """Generate queries based on the user input."""
#         system_prompt = read_markdown_file('./src/agent/research/prompt/query.md')
#         parameters = {'max_queries': self.max_queries, 'date': self.date, 'lang': self.lang}
#         messages = [
#             SystemMessage(system_prompt.format(**parameters)),
#             HumanMessage(f"## User Query:\n{state.get('input')}")
#         ]
#         llm_response = await self.llm.async_invoke(messages)
#         queries = literal_eval(extract_python_code(llm_response.content))
#         return {**state, 'queries': queries}

#     async def quick_search(self, state: AgentState):
#         """Perform a quick search for each query."""
#         async def fetch_results(query):
#             responses = self.ddgs.text(query, max_results=self.max_results)
#             await asyncio.sleep(1)  # Rate limiting
#             return list(responses)

#         results = await asyncio.gather(*(fetch_results(query) for query in state.get('queries')))
#         results = [result for sublist in results for result in sublist]
#         return {**state, 'results': results}

#     async def deep_search(self, state: AgentState):
#         """Perform a deep search (including scraping) for each query."""
#         async def fetch_results_and_scrape(query):
#             responses = self.ddgs.text(query, max_results=self.max_results)
#             results = [{'title': r.get('title'), 'href': r.get('href')} for r in responses]

#             tasks = [asyncio.to_thread(scrape, result['href']) for result in results]
#             scraped_results = await asyncio.gather(*tasks)

#             for result, scraped_result in zip(results, scraped_results):
#                 result['body'] = scraped_result if scraped_result else ''
#                 await asyncio.sleep(1)  # Rate limiting

#             return results

#         all_results = await asyncio.gather(*(fetch_results_and_scrape(query) for query in state.get('queries')))
#         results = [result for sublist in all_results for result in sublist]
#         return {**state, 'results': results}

#     async def response(self, state: AgentState):
#         """Generate a final response using the LLM."""
#         results = '\n'.join(
#             f"Title: {r['title']}\nContent: {r['body']}\nSource: {r['href']}\n"
#             for r in state.get('results')
#         )
#         system_prompt = read_markdown_file('./src/agent/research/prompt/response.md')
#         messages = [
#             SystemMessage(system_prompt),
#             HumanMessage(f"## Web Search Results:\n{results}\n\n## User Query:\n{state.get('input')}")
#         ]
#         llm_response = await self.llm.async_invoke(messages)
#         return {**state, 'output': llm_response.content}

#     def search_strategy(self, state: AgentState):
#         """Determine the search strategy based on the mode."""
#         return self.search_mode

#     def create_graph(self):
#         """Create the workflow graph."""
#         graph = StateGraph(AgentState)
#         graph.add_node('query', self.query)
#         graph.add_node('quick_search', self.quick_search)
#         graph.add_node('deep_search', self.deep_search)
#         graph.add_node('response', self.response)
#         graph.add_edge(START, 'query')
#         graph.add_conditional_edges('query', self.search_strategy)
#         graph.add_edge('quick_search', 'response')
#         graph.add_edge('deep_search', 'response')
#         graph.add_edge('response', END)
#         return graph.compile(debug=False)

#     async def async_invoke(self, input: str):
#         """Asynchronously invoke the agent."""
#         state = {
#             'input': input,
#             'max_queries': self.max_queries,
#             'results': [],
#             'output': ''
#         }
#         return await self.graph.ainvoke(state)

#     def invoke(self, input: str):
#         """Synchronously invoke the agent."""
#         try:
#             return asyncio.run(self.async_invoke(input))
#         except RuntimeError:
#             loop = asyncio.get_event_loop()
#             return loop.run_until_complete(self.async_invoke(input))

#     def stream(self, input):
#         """Placeholder for streaming functionality."""
#         raise NotImplementedError("Streaming is not implemented.")    