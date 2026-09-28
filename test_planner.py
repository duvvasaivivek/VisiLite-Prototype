import asyncio, os
from dotenv import load_dotenv
load_dotenv('.env')
from app.agent.llm import get_planner
from app.schemas.context import SanitizedContext

planner = get_planner()
ctx = SanitizedContext(url='http://amazon.com', page_title='Amazon', task='Search', elements=[], available_user_tokens={})
planner.plan(ctx, '')
