
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# Initialize tools
search_tool = SerperDevTool()


class StockPickerCrew:
    """Main class to orchestrate the stock picking process"""

    def __init__(self):
        self.setup_agents()
        self.setup_tasks()

    def setup_agents(self):
        """Create all the agents for the stock picking process"""

        # 1. Trending Companies Agent - Finds what's hot in the market
        self.trending_agent = Agent(
            role='Trending Companies Analyst',
            goal='Identify the most trending and talked-about companies in the current market',
            backstory="""You are a market trend specialist who keeps a pulse on what companies 
            are making waves in the financial world. You excel at identifying companies that are 
            gaining momentum due to news, earnings, product launches, or market sentiment. 
            You focus on companies with recent significant developments.""",
            tools=[search_tool],
            verbose=True,
            allow_delegation=False
        )

        # 2. Financial Researcher Agent - Deep dives into company financials
        self.financial_researcher = Agent(
            role='Financial Research Analyst',
            goal='Conduct comprehensive financial analysis of trending companies',
            backstory="""You are a seasoned financial analyst with expertise in evaluating 
            company fundamentals, financial health, and growth prospects. You analyze revenue, 
            profit margins, debt levels, cash flow, and key financial ratios. You provide 
            objective assessments of a company's financial strength and investment potential.""",
            tools=[search_tool],
            verbose=True,
            allow_delegation=False
        )

        # 3. Stock Picker Agent - Makes the final investment recommendation
        self.stock_picker = Agent(
            role='Investment Decision Specialist',
            goal='Select the best investment opportunity from researched companies',
            backstory="""You are an experienced portfolio manager who specializes in making 
            final investment decisions. You synthesize market trends, financial data, and 
            risk assessments to recommend the single best investment opportunity. You consider 
            both potential returns and risk factors in your recommendations.""",
            verbose=True,
            allow_delegation=False
        )

        # 4. Manager Agent - No longer needed for sequential process
        # Removed manager agent to simplify execution and avoid delegation errors

    def setup_tasks(self):
        """Create all tasks for the stock picking process"""

        # Task 1: Find Trending Companies
        self.find_trending_task = Task(
            description="""Find and identify 5-7 companies that are currently trending in the 
            stock market as of August 2025. Focus on companies that have:
            - Recent positive news or developments in 2025
            - Strong market momentum in current market conditions
            - Significant trading volume increases
            - Positive analyst coverage or upgrades
            - New product launches or business expansions

            Search for the most recent and current information available.
            Provide a brief explanation for why each company is trending.
            Include the company name, ticker symbol, and current stock price if available.""",
            expected_output="""A list of 5-7 trending companies with:
            - Company name and ticker symbol
            - Current stock price (August 2025)
            - Brief explanation of why they're trending
            - Recent news or catalysts driving the trend""",
            agent=self.trending_agent
        )

        # Task 2: Research Trending Companies (uses context from Task 1)
        self.research_task = Task(
            description="""Conduct detailed financial research on the trending companies 
            identified in the previous task. Search for the most current financial data available 
            in 2025. For each company, analyze:

            Financial Metrics:
            - Latest revenue growth and trends (2024-2025 data preferred)
            - Current profit margins and profitability
            - Recent debt-to-equity ratio
            - Latest cash flow and cash reserves
            - Current price-to-earnings ratio and other valuation metrics

            Business Analysis:
            - Current market position and competitive advantages
            - Growth prospects and future outlook for 2025-2026
            - Risk factors and potential challenges
            - Management quality and recent strategic decisions

            Focus on the most recent and current information available.
            Provide a comprehensive analysis for each company with a risk rating (Low/Medium/High).""",
            expected_output="""Detailed financial analysis for each trending company including:
            - Key financial metrics and ratios (most recent available)
            - Revenue and profit trends (2024-2025)
            - Business strengths and competitive position
            - Growth prospects and opportunities
            - Risk assessment and potential challenges
            - Overall investment attractiveness score (1-10)""",
            agent=self.financial_researcher,
            context=[self.find_trending_task]  # Uses output from trending task
        )

        # Task 3: Pick Best Company (uses context from Task 2)
        self.pick_best_task = Task(
            description="""Based on the comprehensive research conducted, select the single 
            best company for investment. Consider:

            Selection Criteria:
            - Strong financial fundamentals
            - Attractive valuation relative to growth prospects
            - Manageable risk profile
            - Clear competitive advantages
            - Positive industry outlook
            - Strong management team

            Provide a detailed recommendation including:
            - The chosen company and rationale
            - Specific reasons why it's the best choice
            - Expected return potential
            - Risk factors to monitor
            - Suggested investment strategy (buy and hold, growth play, etc.)""",
            expected_output="""A comprehensive investment recommendation including:
            - Selected company name and ticker
            - Detailed investment thesis
            - Key reasons for selection over other candidates
            - Expected return potential and timeline
            - Risk factors and mitigation strategies
            - Recommended position size and investment approach
            - Price targets and exit strategy""",
            agent=self.stock_picker,
            context=[self.research_task]  # Uses output from research task
        )

    def run_analysis(self):
        """Execute the complete stock picking analysis - runs only once"""

        # Create the crew with all agents and tasks
        # Note: Manager agent is NOT included in agents list when using hierarchical process
        crew = Crew(
            agents=[self.trending_agent, self.financial_researcher, self.stock_picker],
            tasks=[self.find_trending_task, self.research_task, self.pick_best_task],
            process=Process.sequential,  # Changed to sequential to avoid delegation issues
            verbose=True,
            max_execution_time=1800,  # 30 minutes timeout
        )

        print(f"🚀 Starting Stock Picker Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        try:
            # Execute the crew - this runs only once
            result = crew.kickoff()

            print("\n" + "=" * 80)
            print("📊 FINAL INVESTMENT RECOMMENDATION")
            print("=" * 80)
            print(result)

            return result

        except Exception as e:
            print(f"❌ Error during execution: {str(e)}")
            print("The analysis encountered an issue. Please check your API keys and try again.")
            return None


def main():
    """Main function to run the stock picker - executes only once"""

    # Check if API keys are set (uncomment when you have your keys)
    # if not os.getenv("OPENAI_API_KEY"):
    #     print("❌ Please set your OPENAI_API_KEY environment variable")
    #     return
    #
    # if not os.getenv("SERPER_API_KEY"):
    #     print("❌ Please set your SERPER_API_KEY environment variable")
    #     return

    print("🏦 Welcome to the CrewAI Stock Picker!")
    print("This system will analyze trending companies and recommend the best investment.")
    print("📅 Searching for the most current market data available (August 2025)")
    print("\n⚠️  Note: This is for educational purposes only. Not financial advice!")

    # Initialize and run the stock picker
    stock_picker = StockPickerCrew()

    try:
        print("🔄 Starting analysis... This will run once and provide complete results.")
        result = stock_picker.run_analysis()

        if result:
            # Save results to file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"stock_analysis_{timestamp}.txt"

            with open(filename, 'w') as f:
                f.write(f"Stock Picker Analysis Results - {datetime.now()}\n")
                f.write("=" * 80 + "\n\n")
                f.write(str(result))

            print(f"\n💾 Results saved to: {filename}")
            print("✅ Analysis completed successfully!")
        else:
            print("❌ Analysis failed. Please check the error messages above.")

    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        print("Please check your API keys and internet connection.")


if __name__ == "__main__":
    main()
