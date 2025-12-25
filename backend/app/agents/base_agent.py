"""
Base Agent Implementation

This module defines the common base class for all Technical Working Group agents,
including integration with tools and LLMs.
"""

from typing import List, Dict, Any, Optional
import os
import logging
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from backend.app.tools.knowledge_tools import KNOWLEDGE_TOOLS
from backend.app.tools.database_tools import DATABASE_TOOLS

logger = logging.getLogger(__name__)

class TWGAgent:
    """
    Base class for thematic TWG agents.
    """
    
    def __init__(
        self,
        name: str,
        pillar: str,
        twg_id: Optional[str] = None,
        model_name: str = "gpt-4-turbo-preview"
    ):
        self.name = name
        self.pillar = pillar
        self.twg_id = twg_id
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Combine tools
        self.tools = self._initialize_tools()
        
        # Create prompt
        self.prompt = self._create_prompt()
        
        # Initialize agent
        self.agent = create_openai_tools_agent(self.llm, self.tools, self.prompt)
        self.executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)
        
        logger.info(f"Initialized agent: {name} for pillar: {pillar}")

    def _initialize_tools(self):
        """
        Merge knowledge base tools and database tools.
        """
        # Convert custom tool definitions to LangChain tools if necessary
        # For now, we assume tools are already in a compatible format or we use wrappers
        from langchain.tools import Tool
        
        lc_tools = []
        
        # Knowledge Base Tools
        from backend.app.tools.knowledge_tools import search_knowledge_base, get_relevant_context
        lc_tools.append(Tool(
            name="search_knowledge",
            func=search_knowledge_base,
            description="Search the ECOWAS Summit knowledge base for relevant documents and policy info."
        ))
        
        # Database Tools
        from backend.app.tools.database_tools import get_twg_info, list_twg_meetings, create_meeting_invite
        
        # Note: Since database tools are async, we might need to handle them differently in AgentExecutor
        # For now, we will use synchronous wrappers or ensure the executor handles async.
        
        return lc_tools

    def _create_prompt(self) -> ChatPromptTemplate:
        """
        Define the system prompt for the agent.
        """
        system_message = f"""
You are {self.name}, the AI support agent for the {self.pillar} Technical Working Group (TWG) of the ECOWAS Summit 2026.
Your goal is to streamline the TWG's work, ensuring alignment with Summit pillars and deliverables like the Abuja Declaration.

Context:
- Current Pillar: {self.pillar}
- TWG ID: {self.twg_id}

Responsibilities:
1. Assist in scheduling meetings and drafting invitations.
2. Formulate policy drafts based on knowledge base search.
3. Track and update action items from meeting discussions.
4. Curate investment projects for the Deal Room pipeline.

Always maintain a professional, diplomatic tone. Cite your sources when retrieving information from the knowledge base.
"""
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

    async def chat(self, user_input: str, chat_history: List[BaseMessage] = None) -> str:
        """
        Send a message to the agent and get a response.
        """
        if chat_history is None:
            chat_history = []
            
        try:
            response = await self.executor.ainvoke({
                "input": user_input,
                "chat_history": chat_history
            })
            return response["output"]
        except Exception as e:
            logger.error(f"Error in agent chat: {e}")
            return f"I encountered an error while processing your request: {str(e)}"
