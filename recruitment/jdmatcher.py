from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from typing import List, Dict, Any
import json
import os
from dataclasses import dataclass
from pydantic import BaseModel
import PyPDF2
import pdfplumber
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class CandidateProfile:
    """Data structure for candidate information"""
    name: str = ""
    resume_text: str = ""
    resume_pdf_path: str = ""
    email: str = ""
    phone: str = ""

    def __post_init__(self):
        """Extract text from PDF if path is provided and text is empty"""
        if self.resume_pdf_path and not self.resume_text:
            self.resume_text = PDFProcessor.extract_text_from_pdf(self.resume_pdf_path)
            # Extract name from filename if not provided
            if not self.name:
                self.name = Path(self.resume_pdf_path).stem.replace('_', ' ').replace('-', ' ').title()


class JobDescription:
    """Class to handle job description from PDF"""

    def __init__(self, pdf_path: str):
        self.text = PDFProcessor.extract_text_from_pdf(pdf_path)
        self.pdf_path = pdf_path

    def __str__(self):
        return self.text


class PDFProcessor:
    """Utility class for handling PDF file operations"""

    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """
        Extract text from PDF using multiple methods for better reliability
        """
        text = ""

        # Method 1: Try pdfplumber first (better for complex layouts)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                if text.strip():
                    return text.strip()
        except Exception as e:
            print(f"pdfplumber failed for {pdf_path}: {e}")

        # Method 2: Fallback to PyPDF2
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                if text.strip():
                    return text.strip()
        except Exception as e:
            print(f"PyPDF2 failed for {pdf_path}: {e}")

        return f"Error: Could not extract text from {pdf_path}"

    @staticmethod
    def validate_pdf_path(pdf_path: str) -> bool:
        """Validate if PDF path exists and is readable"""
        try:
            path = Path(pdf_path)
            return path.exists() and path.suffix.lower() == '.pdf'
        except:
            return False

    @staticmethod
    def batch_extract_from_folder(folder_path: str) -> List[CandidateProfile]:
        """
        Extract all PDF resumes from a folder and create CandidateProfile objects
        """
        candidates = []
        folder = Path(folder_path)

        if not folder.exists():
            print(f"Folder {folder_path} does not exist")
            return candidates

        # Find all PDF files in the folder
        pdf_files = list(folder.glob("*.pdf"))

        if not pdf_files:
            print(f"No PDF files found in {folder_path}")
            return candidates

        for pdf_file in pdf_files:
            try:
                candidate = CandidateProfile(resume_pdf_path=str(pdf_file))
                candidates.append(candidate)
            except Exception as e:
                print(f"Failed to process {pdf_file}: {e}")

        return candidates


class ScoringCriteria(BaseModel):
    """Scoring criteria for resume evaluation"""
    technical_skills: int = 0  # 0-10
    experience: int = 0  # 0-10
    education: int = 0  # 0-10
    cultural_fit: int = 0  # 0-10
    communication: int = 0  # 0-10

    @property
    def total_score(self) -> int:
        return self.technical_skills + self.experience + self.education + self.cultural_fit + self.communication


class ResumeAnalysisTool(BaseTool):
    """Custom tool for structured resume analysis"""
    name: str = "resume_analyzer"
    description: str = "Analyzes resume content against job requirements"

    def _run(self, resume_text: str, job_description: str) -> str:
        """Basic resume analysis logic"""
        analysis = {
            "resume_length": len(resume_text.split()),
            "contains_keywords": self._check_keywords(resume_text, job_description),
            "sections_found": self._identify_sections(resume_text)
        }
        return json.dumps(analysis, indent=2)

    def _check_keywords(self, resume: str, job_desc: str) -> List[str]:
        """Simple keyword matching"""
        job_keywords = job_desc.lower().split()
        resume_lower = resume.lower()
        found_keywords = [word for word in job_keywords if word in resume_lower and len(word) > 3]
        return found_keywords[:10]  # Top 10 matches

    def _identify_sections(self, resume: str) -> List[str]:
        """Identify resume sections"""
        sections = []
        common_sections = ['experience', 'education', 'skills', 'projects', 'certifications']
        for section in common_sections:
            if section.lower() in resume.lower():
                sections.append(section)
        return sections


class ResumeScreeningCrew:
    """Main class for the resume screening system"""

    def __init__(self, job_description_pdf: str):
        if not PDFProcessor.validate_pdf_path(job_description_pdf):
            raise ValueError(f"Invalid PDF path: {job_description_pdf}")

        self.job_description = JobDescription(job_description_pdf).text
        self.resume_tool = ResumeAnalysisTool()
        self.agents = self._create_agents()
        self.tasks = []

    def _create_agents(self) -> Dict[str, Agent]:
        """Create specialized agents for the screening process"""

        # Job Requirements Analyst
        job_analyst = Agent(
            role='Job Requirements Analyst',
            goal='Extract and analyze key requirements from job descriptions',
            backstory="""You are an experienced HR professional who specializes in 
            breaking down job descriptions into specific, measurable requirements. 
            You identify must-have skills, nice-to-have skills, experience levels, 
            and cultural fit indicators.""",
            verbose=True,
            allow_delegation=False
        )

        # Resume Evaluator
        resume_evaluator = Agent(
            role='Resume Evaluator',
            goal='Thoroughly evaluate resumes against job requirements',
            backstory="""You are a skilled recruiter with 10+ years of experience 
            in talent acquisition. You excel at reading between the lines in resumes, 
            identifying relevant experience, and assessing candidate potential.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.resume_tool]
        )

        # Skills Assessor
        skills_assessor = Agent(
            role='Technical Skills Assessor',
            goal='Evaluate technical competencies and assign accurate scores',
            backstory="""You are a technical hiring manager who understands the 
            nuances of different skill levels. You can distinguish between beginner, 
            intermediate, and expert levels of technical proficiency.""",
            verbose=True,
            allow_delegation=False
        )

        # Final Recommender
        recommender = Agent(
            role='Hiring Recommender',
            goal='Provide final recommendations based on comprehensive analysis',
            backstory="""You are a senior hiring manager who makes final decisions 
            on candidate selection. You weigh all factors including technical skills, 
            cultural fit, growth potential, and team dynamics.""",
            verbose=True,
            allow_delegation=False
        )

        return {
            'job_analyst': job_analyst,
            'resume_evaluator': resume_evaluator,
            'skills_assessor': skills_assessor,
            'recommender': recommender
        }

    def create_screening_tasks(self, candidates: List[CandidateProfile]) -> List[Task]:
        """Create tasks for the screening process"""
        tasks = []

        # Task 1: Analyze job requirements
        job_analysis_task = Task(
            description=f"""
            Analyze the following job description and extract key requirements:

            {self.job_description}

            Identify:
            1. Must-have technical skills
            2. Nice-to-have technical skills
            3. Required experience level
            4. Education requirements
            5. Soft skills and cultural fit indicators

            Provide a structured analysis that can be used for candidate evaluation.
            """,
            agent=self.agents['job_analyst'],
            expected_output="Detailed job requirements analysis with categorized skills and qualifications"
        )
        tasks.append(job_analysis_task)

        # Task 2: Evaluate each candidate
        for i, candidate in enumerate(candidates):
            evaluation_task = Task(
                description=f"""
                Evaluate the following candidate's resume against the job requirements:

                Candidate Name: {candidate.name}
                Resume Content: {candidate.resume_text}

                Based on the job analysis, evaluate this candidate on:
                1. Technical skills match
                2. Experience relevance and level
                3. Education background
                4. Communication skills (based on resume quality)
                5. Potential cultural fit indicators

                Provide specific examples from the resume to support your evaluation.
                """,
                agent=self.agents['resume_evaluator'],
                expected_output=f"Comprehensive evaluation of {candidate.name}'s qualifications with specific examples",
                context=[job_analysis_task]
            )
            tasks.append(evaluation_task)

        # Task 3: Score candidates
        scoring_task = Task(
            description="""
            Based on all candidate evaluations, assign numerical scores for each candidate in these categories:

            For EACH candidate, provide scores in this exact format:

            CANDIDATE NAME: [Name]
            - Technical Skills: [Score]/10 ([Percentage]%) - [Brief justification]
            - Experience Level: [Score]/10 ([Percentage]%) - [Brief justification] 
            - Education Background: [Score]/10 ([Percentage]%) - [Brief justification]
            - Communication Skills: [Score]/10 ([Percentage]%) - [Brief justification]
            - Cultural Fit Potential: [Score]/10 ([Percentage]%) - [Brief justification]
            - TOTAL SCORE: [Sum]/50 ([Overall Percentage]%)

            Calculate percentages as: (Score/10) × 100 for individual attributes
            Calculate overall percentage as: (Total Score/50) × 100

            Example format:
            - Technical Skills: 8/10 (80%) - Strong Python and Django experience
            - TOTAL SCORE: 38/50 (76%)

            After scoring all candidates, provide:
            1. Individual detailed scores with percentages for each candidate
            2. Final ranking from highest to lowest total percentage
            3. Summary table comparing all candidates' percentages

            Be specific in justifications and show all calculations clearly.
            """,
            agent=self.agents['skills_assessor'],
            expected_output="Detailed scoring breakdown with percentages for each candidate, individual attribute scores, justifications, and final ranking",
            context=tasks[1:]  # All evaluation tasks
        )
        tasks.append(scoring_task)

        # Task 4: Final recommendation
        recommendation_task = Task(
            description="""
            Based on the comprehensive analysis and detailed scoring with percentages, provide final hiring recommendations.

            IMPORTANT: Include the complete scoring breakdown with percentages in your final report.

            Your report must include:

            1. DETAILED SCORES SECTION:
            Copy the complete scoring breakdown from the Skills Assessor, showing:
            - Each candidate's name
            - All 5 attribute scores with percentages (Technical Skills, Experience, Education, Communication, Cultural Fit)
            - Total scores with percentages
            - Justifications for each score

            2. RANKING SECTION:
            - Final ranking from highest to lowest percentage
            - Clear percentage differences between candidates

            3. TOP RECOMMENDATIONS:
            - Top 3 recommended candidates with detailed reasoning
            - Key strengths and potential concerns for each
            - Interview focus areas for each candidate

            4. ANALYSIS SUMMARY:
            - Overall assessment of candidate pool quality
            - Hiring recommendations and next steps

            Format as a comprehensive professional hiring report that includes ALL scoring details with percentages.
            """,
            agent=self.agents['recommender'],
            expected_output="Complete professional hiring report including detailed scores with percentages, rankings, recommendations, and analysis",
            context=[job_analysis_task, scoring_task]
        )
        tasks.append(recommendation_task)

        return tasks

    def screen_candidates(self, candidates: List[CandidateProfile]) -> str:
        """Execute the complete screening process"""

        # Create tasks for this screening session
        tasks = self.create_screening_tasks(candidates)

        # Create and configure the crew
        crew = Crew(
            agents=list(self.agents.values()),
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )

        # Execute the screening process
        result = crew.kickoff()  # This is where all LLM calls happen

        return result


def main(job_pdf_path=None, resume_folder=None, output_file=None):
    """Main function to run PDF-based resume screening"""

    # Configuration with defaults
    if job_pdf_path is None:
        job_pdf_path = input("Enter job description PDF path (or press Enter for 'job_description.pdf'): ").strip()
        if not job_pdf_path:
            job_pdf_path = "job_description.pdf"

    if resume_folder is None:
        resume_folder = input("Enter resumes folder path (or press Enter for 'resumes/'): ").strip()
        if not resume_folder:
            resume_folder = "resumes/"

    if output_file is None:
        output_file = input("Enter output file name (or press Enter for 'screening_report.txt'): ").strip()
        if not output_file:
            output_file = "screening_report.txt"

    try:
        # Validate job description PDF
        if not PDFProcessor.validate_pdf_path(job_pdf_path):
            raise FileNotFoundError(f"Job description PDF not found: {job_pdf_path}")

        # Initialize the screening system
        screening_crew = ResumeScreeningCrew(job_description_pdf=job_pdf_path)

        # Load candidates from resume folder
        candidates = PDFProcessor.batch_extract_from_folder(resume_folder)

        if not candidates:
            raise ValueError(f"No valid resume PDFs found in {resume_folder}")

        # Run the screening process
        result = screening_crew.screen_candidates(candidates)

        # Display and save results
        print("FINAL SCREENING REPORT")
        print("=" * 60)
        print(result)

        # Save report to file - convert CrewOutput to string
        with open(output_file, "w") as f:
            f.write("RESUME SCREENING REPORT\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Job Description: {job_pdf_path}\n")
            f.write(f"Resume Folder: {resume_folder}\n")
            f.write(f"Candidates: {len(candidates)}\n\n")
            f.write(str(result))  # Convert CrewOutput to string

        print(f"\nReport saved to: {output_file}")
        return result

    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    # Simple usage - just run with defaults or specify paths

    # Option 1: Use defaults (job_description.pdf and resumes/ folder)
    result = main()

    # Option 2: Specify custom paths
    # result = main("my_job.pdf", "my_resumes/", "my_report.txt")

    if result:
        print("Screening completed successfully!")
    else:
        print("Screening failed. Check file paths and API key.")
