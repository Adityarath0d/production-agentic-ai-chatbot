from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.agent.state import AgentState
from app.config import settings
from app.tools.calculator import calculator
from app.tools.weather import get_weather

llm = ChatGoogleGenerativeAI(
    model=settings.GEMINI_MODEL, api_key=settings.GEMINI_API_KEY
)

llm_with_tools = llm.bind_tools([calculator, get_weather])


async def call_model(state: AgentState) -> dict:
    response = await llm_with_tools.ainvoke(state["messages"])
    return {"messages": [response]}


def build_graph(checkpointer):

    # Instantiate Graph
    graph = StateGraph(AgentState)

    # tool node
    tool_node = ToolNode([calculator,get_weather])
    # add nodes
    graph.add_node("agent", call_model)
    graph.add_node("tool_node", tool_node)
    # add edges
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "tool_node",
            "__end__": END,
        },
    )
    graph.add_edge("tool_node", "agent")

    return graph.compile(checkpointer=checkpointer)



