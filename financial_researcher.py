import os
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from langchain_openai import ChatOpenAI

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("python-dotenv not installed. Make sure to set environment variables manually.")


def main():
    print("🏦 Financial Research AI Assistant")
    print("=" * 50)

    # Check if API keys are set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found. Please set your OpenAI API key.")
        return

    if not os.getenv("SERPER_API_KEY"):
        print("❌ SERPER_API_KEY not found. Please set your Serper API key.")
        return

    # Get company name from user
    company_name = input("\n💼 Enter the company name to analyze: ").strip()
    if not company_name:
        print("Please enter a valid company name.")
        return

    print(f"\n🔍 Starting research and analysis for: {company_name}")
    print("This may take a few minutes...\n")

    # Initialize tools and LLM
    search_tool = SerperDevTool()
    llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.1)

    # Create the Researcher Agent
    researcher = Agent(
        role="Financial Researcher",
        goal="Find comprehensive financial information and recent news about the company",
        backstory="""You are an expert financial researcher who specializes in gathering 
        accurate and up-to-date information about public companies. You know how to find 
        the most important financial data, recent news, and market information.""",
        tools=[search_tool],
        llm=llm,
        verbose=True
    )

    # Create the Analyst Agent
    analyst = Agent(
        role="Financial Analyst",
        goal="Analyze the research data and provide clear investment insights",
        backstory="""You are a senior financial analyst with expertise in evaluating 
        companies and providing investment recommendations. You excel at interpreting 
        financial data and explaining complex analysis in simple terms.""",
        llm=llm,
        verbose=True
    )

    # Create the Research Task
    research_task = Task(
        description=f"""Research {company_name} and gather the following information:

        1. Company basics: What does the company do? What industry are they in?
        2. Financial health: Recent revenue, profits, and financial performance
        3. Stock information: Current stock price, market cap, recent performance
        4. Recent news: Any important recent developments or announcements
        5. Competition: Who are their main competitors?

        Focus on finding accurate, recent information from reliable sources.""",

        expected_output="""A clear research report with:
        - Company overview and business description
        - Key financial metrics and recent performance
        - Current stock price and market data
        - Summary of recent news and developments
        - List of main competitors""",

        agent=researcher
    )

    # Create the Analysis Task (uses research as input)
    analysis_task = Task(
        description=f"""Using the research data provided, analyze {company_name} and provide:

        1. Investment Summary: Is this a good investment opportunity?
        2. Strengths: What are the company's main advantages?
        3. Risks: What are the potential problems or concerns?
        4. Financial Analysis: How is the company performing financially?
        5. Recommendation: Should someone buy, hold, or avoid this stock?

        Explain everything in simple terms that a beginner investor could understand.""",

        expected_output="""A comprehensive analysis report including:
        - Clear investment recommendation (Buy/Hold/Sell)
        - Top 3 strengths of the company
        - Top 3 risks or concerns
        - Simple explanation of financial health
        - Overall investment thesis in plain English""",

        agent=analyst,
        context=[research_task]  # This task gets the research results as input
    )

    # Create the Crew (team of agents)
    crew = Crew(
        agents=[researcher, analyst],
        tasks=[research_task, analysis_task],
        process=Process.sequential,  # Research first, then analysis
        verbose=True
    )

    try:
        # Run the analysis
        result = crew.kickoff()

        # Display results
        print("\n" + "=" * 60)
        print("📊 FINANCIAL ANALYSIS COMPLETE")
        print("=" * 60)
        print(result)

        # Save results to file (optional)
        save_results(company_name, result)

    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        print("Please check your API keys and internet connection.")


def save_results(company_name: str, result):
    """Save the analysis results to a text file"""
    try:
        # Create filename
        filename = f"{company_name.replace(' ', '_')}_analysis.txt"

        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Financial Analysis Report for {company_name}\n")
            f.write("=" * 50 + "\n\n")
            f.write(str(result))

        print(f"\n💾 Results saved to: {filename}")

    except Exception as e:
        print(f"Note: Could not save to file - {str(e)}")


if __name__ == "__main__":
    # Instructions for first-time users
    print(__doc__)

    # Check Python version
    import sys

    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher required")
        exit(1)

    print("\n🚀 Ready to start!")
    main()

