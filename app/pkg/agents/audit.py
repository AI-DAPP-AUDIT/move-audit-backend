from app.pkg.agents.prompt import get_prompt
from autogen_ext.models.openai import OpenAIChatCompletionClient
from openai import AsyncClient
from autogen_agentchat.ui import Console
from app.pkg.walus.publisher import Publish
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_ext.agents.openai import OpenAIAssistantAgent
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools
from autogen_ext.agents.file_surfer import FileSurfer
from markdown import markdown
from weasyprint import HTML
import re
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)
class AuditStatus(Enum):
    PENDING = "pending"
    Reading = "reading"
    Auditing = "auditing"
    Auditted = "auditted"
    Reporting = "reporting"
    Reported = "reported"


def extract_markdown_content(text: str) -> str:
    pattern = r"```markdown\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text

class Client:
    def __init__(self, model: str, api_key: str, directory: str, order_id: str):
        self.model = model
        self.api_key = api_key
        self.directory = directory
        self.status = AuditStatus.PENDING
        self.audit_path = self.directory + "/report.pdf"
        self.blob_id = ""
        self.order_id = order_id
        self.model_client = OpenAIChatCompletionClient(
            model=model,
            api_key=api_key,
        )

        self.openapi_client = AsyncClient(
            api_key=api_key,
        )
    
    def getStatus(self):
        return self.status.value
    
    def getBlobId(self):
        return self.blob_id

    def getDirectory(self):
        return self.directory
    
    def getOrderId(self):
        return self.order_id

    async def close(self):
        await self.model_client.close()
        await self.openapi_client.close()
        logger.debug("Successfully closed client", self.directory, self.blob_id, self.status)


    async def begin(self):
        print("contract file directory==========\n", self.directory)
        self.status = AuditStatus.Reading
        server_params = StdioServerParams(
            command="mcp-filesystem-server", args=[self.directory]
        )

        tools = await mcp_server_tools(server_params)

        fs_agent = FileSurfer("FileSurfer", model_client=self.model_client, base_path=self.directory)

        output_agnet = AssistantAgent(
            name="OutputAgent",
            model_client=self.model_client,
            system_message="You are an agent that organizes and formats audit reports in Move language based on audit results.",
            description="A agent that organizes and formats audit reports in Move language based on audit results.",
        )

        auditor_agent = OpenAIAssistantAgent(
            name="AuditAgent",
            description="A helpful assistant that audits the move contract and outputs the audit results.",
            client=self.openapi_client,
            model="gpt-4o",
            instructions="You are an assistant that audits the move contract and outputs the audit results.",
            tools=tools,
        )

        m1 = MagenticOneGroupChat([fs_agent, auditor_agent, output_agnet], model_client=self.model_client)

        task = get_prompt()

        try:
            self.status = AuditStatus.Auditing
            result = await Console(m1.run_stream(task=task))
            lenght = len(result.messages)-1
            resultStr = ""
            for i in range(lenght, 0, -1):
                if result.messages[i].source == "OutputAgent":
                    resultStr = result.messages[i].content
                    break
            print("resultStr ===============: ", resultStr)
            self.status = AuditStatus.Auditted         
            markdown_content = extract_markdown_content(resultStr)
            html_text = markdown(markdown_content)
            HTML(string=html_text).write_pdf(target = self.audit_path)
            self.status = AuditStatus.Reporting
            publisher = Publish()
            response = publisher.upload(markdown_content)
            uploadRes = json.loads(response.text)
            self.blob_id = uploadRes["newlyCreated"]["blobObject"]["id"]
            print("blob_id: ",response.text, self.blob_id)

            self.status = AuditStatus.Reported
            return self.blob_id
        except Exception as e:
            print(f"audit error: {str(e)}")
            return ""