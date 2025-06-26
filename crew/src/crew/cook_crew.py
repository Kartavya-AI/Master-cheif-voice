from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv
from src.crew.tools.serper import SerperDevTool
import os

load_dotenv()

os.getenv("GEMINI_API_KEY")

# Initialize Gemini model
llm = LLM(model="gemini/gemini-2.0-flash")

search_tool = SerperDevTool()

@CrewBase
class CookCrew():
    """Cooking crew with specialized agents"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def recipe_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['cooking_expert'],
            llm=llm,
            tools=[search_tool],
            memory=True,
        )

    @task
    def cook_recipe(self) -> Task:
        return Task(
            config=self.tasks_config['cook_recipe'],
            agent=self.recipe_agent()
        )

    @crew
    def cooking_crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )