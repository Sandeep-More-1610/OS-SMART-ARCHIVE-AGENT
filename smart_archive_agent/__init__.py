"""Smart Archive Agent (Agent #12) for the Agentic Shell.

Integration points for the base shell (see INTEGRATION.md):
    get_manifest()                              -> who this agent is, what it needs, how to call it
    get_tools(style, prefixed=False)            -> tool definitions for LLM function calling
    execute_tool(name, args, passphrase=None)   -> run one tool call chosen by the LLM
    handle_request(text, confirm=None, passphrase=None) -> plan and run a plain-English request
"""
from smart_archive_agent.manifest import AGENT_ID, AGENT_NAME, AGENT_DESCRIPTION, VERSION, get_manifest
from smart_archive_agent.agent import handle_request
from smart_archive_agent.tools.registry import get_tools, execute_tool, TOOL_PREFIX

__version__ = VERSION
__all__ = ["AGENT_ID", "AGENT_NAME", "AGENT_DESCRIPTION", "TOOL_PREFIX", "get_manifest",
           "get_tools", "execute_tool", "handle_request", "__version__"]
