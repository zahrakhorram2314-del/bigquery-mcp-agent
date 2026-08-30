import os

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

import google.auth
from google.auth.transport.requests import Request

_application_default_credentials, project_id = google.auth.default()
_request = Request()
_application_default_credentials.refresh(_request)

project_id = os.getenv("GOOGLE_CLOUD_PROJECT", project_id)
if not project_id:
    raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set.")

def _adc_auth_header_provider(context = None) -> dict[str, str]:
    if not _application_default_credentials.valid:
        _application_default_credentials.refresh(_request)
    return {
        "Authorization": f"Bearer {_application_default_credentials.token}",
        "x-goog-user-project": project_id
    }

bigquery_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://bigquery.googleapis.com/mcp",
        tool_filter=[
            'get_dataset_info',
            'list_table_ids',
            'get_table_info',
            'execute_sql_readonly',
        ],
        header_provider=_adc_auth_header_provider
    )
)

system_instruction = f"""
You are a helpful assistant that can answer questions about data in BigQuery.
To answer the user's question, use data you have access to by using tools 'List...' or 'Get...'.
Your data is in 'bigquery-public-data.new_york_citibike' dataset (Citi Bike trips).

Plan of action:
0. ALWAYS start by analyzing dataset.
1. Analyze your data. Investigate schema and dimensions by querying distinct values for categorical fields.
   Output information about tables, columns, their data types and sets of values.
   Note which columns can be joined or used in aggregations/filters, and what type of data they hold.
   DO NOT MAKE ASSUMPTIONS ABOUT DATA (structure, type, values, relationships) IF YOU CAN QUERY IT!
2. Understand and interpret the user's question.
3. Formulate a plan to answer the user's question.
4. Write a SQL query to retrieve relevant data in necessary form.
   This is where you must pay extra attention to column types and dimensions' values.
5. Retrieve data by generating BigQuery SQL and using `execute_sql_readonly`.
   Always use Dry Run to verify SQL correctness.
   Use '{project_id}' to run BigQuery queries ('project_id' parameter of 'execute_sql_readonly').

Do not use LaTeX in your responses. When giving a final answer, use Markdown.
"""

root_agent = LlmAgent(
    model="gemini-1.5-flash",
    name="data_agent",
    instruction=system_instruction,
    description="A helpful assistant that can answer questions using NYC Citibike dataset.",
    tools=[bigquery_toolset]
)

