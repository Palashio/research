import re
import json
from typing import Dict, List, Any, Tuple
from datetime import datetime
from openai import OpenAI
import argparse
from pathlib import Path
from pydantic import BaseModel

class EvaluationCriteria(BaseModel):
    score: int
    explanation: str

class SectionEvaluation(BaseModel):
    logical_flow: EvaluationCriteria
    integration_quality: EvaluationCriteria
    academic_tone: EvaluationCriteria
    clarity: EvaluationCriteria
    coherence: EvaluationCriteria
    overall_assessment: str

class ResearchReportEvaluator:
    """Evaluates the quality of generated research reports"""
    
    def __init__(self, model="gpt-4o"):
        self.client = OpenAI()
        self.model = model
        
    def evaluate_report(self, report_path: str) -> Dict[str, Any]:
        """
        Comprehensive evaluation of a research report
        
        Args:
            report_path: Path to the markdown report file
            
        Returns:
            Dictionary containing all evaluation results
        """
        
        # Load and parse the report
        with open(report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()
        
        # Parse report sections
        sections = self._parse_report_sections(report_content)
        
        # Run narrative coherence evaluation
        results = {
            'report_path': report_path,
            'evaluation_date': datetime.now().isoformat(),
            'narrative_coherence': self._evaluate_narrative_coherence(report_content),
            'overall_score': 0.0
        }
        
        # Calculate overall score
        results['overall_score'] = results['narrative_coherence']['overall_score']
        
        return results
    
    def _parse_report_sections(self, content: str) -> Dict[str, str]:
        """Parse the report into sections"""
        sections = {}
        
        # Extract main sections
        intro_match = re.search(r'## Introduction\n\n(.*?)(?=\n## |\n## Sources|\Z)', content, re.DOTALL)
        if intro_match:
            sections['introduction'] = intro_match.group(1).strip()
        
        # Extract topic sections
        topic_sections = re.findall(r'## ([^#\n]+)\n\n(.*?)(?=\n## |\n## Sources|\Z)', content, re.DOTALL)
        for topic, content in topic_sections:
            if topic.lower() not in ['introduction', 'conclusion', 'sources', 'table of contents']:
                sections[f'topic_{topic.strip()}'] = content.strip()
        
        # Extract conclusion
        conclusion_match = re.search(r'## Conclusion\n\n(.*?)(?=\n## Sources|\Z)', content, re.DOTALL)
        if conclusion_match:
            sections['conclusion'] = conclusion_match.group(1).strip()
        
        # Extract sources
        sources_match = re.search(r'## Sources\n\n(.*?)(?=\Z)', content, re.DOTALL)
        if sources_match:
            sections['sources'] = sources_match.group(1).strip()
        
        return sections
    
    def _evaluate_narrative_coherence(self, content: str) -> Dict[str, Any]:
        """Evaluate narrative coherence using LLM for each section separately"""
        
        # Parse sections first
        sections = self._parse_report_sections(content)
        
        # Evaluate each section separately
        section_scores = {}
        overall_scores = []
        
        for section_name, section_content in sections.items():
            if section_name == 'sources':  # Skip sources section
                continue
                
            prompt = f"""
You are an expert evaluator of research report sections. Analyze the following section for narrative coherence and quality.

<Section Name>
{section_name}
</Section Name>

<Section Content>
{section_content[:6000]}  # Limit content length for API
</Section Content>

Evaluate this section on the following criteria using a 1-5 scale (where 1=poor, 2=fair, 3=good, 4=very good, 5=excellent):

1. **Logical Flow (1-5)**: How well does the content flow from one paragraph to the next?
   - 1: Disjointed, no clear progression
   - 2: Some logical connections, but gaps exist
   - 3: Generally flows well with minor issues
   - 4: Strong logical progression with smooth transitions
   - 5: Excellent flow with seamless paragraph connections

2. **Integration Quality (1-5)**: How well is information from multiple sources integrated?
   - 1: Sources are simply listed without integration
   - 2: Basic integration with some source attribution
   - 3: Good integration with proper citations
   - 4: Strong integration with seamless source blending
   - 5: Excellent integration creating a unified narrative

3. **Academic Tone (1-5)**: How professional and scholarly is the writing style?
   - 1: Informal, inappropriate for academic context
   - 2: Somewhat informal with academic elements
   - 3: Generally appropriate academic tone
   - 4: Strong academic tone with professional language
   - 5: Excellent scholarly tone throughout

4. **Clarity (1-5)**: How clear and understandable is the content?
   - 1: Confusing, difficult to follow
   - 2: Somewhat clear with occasional confusion
   - 3: Generally clear with minor issues
   - 4: Very clear and well-explained
   - 5: Exceptionally clear and easy to understand

5. **Coherence (1-5)**: How well do the ideas connect and build upon each other?
   - 1: Ideas are disconnected and don't build on each other
   - 2: Some connections but ideas don't flow well
   - 3: Good connections with logical idea progression
   - 4: Strong connections with clear idea development
   - 5: Excellent coherence with ideas building naturally

Provide a brief explanation for each score and an overall coherence assessment.
"""
            
            try:
                response = self.client.responses.parse(
                    model=self.model,
                    input=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    text_format=SectionEvaluation
                )
                
                result = response.output_parsed
                
                # Calculate average score for this section (convert to 0-100 scale)
                scores = [
                    result.logical_flow.score,
                    result.integration_quality.score,
                    result.academic_tone.score,
                    result.clarity.score,
                    result.coherence.score
                ]
                avg_score = (sum(scores) / len(scores)) * 20  # Convert 1-5 to 0-100 scale
                
                section_scores[section_name] = {
                    'logical_flow': {
                        'score': result.logical_flow.score,
                        'explanation': result.logical_flow.explanation
                    },
                    'integration_quality': {
                        'score': result.integration_quality.score,
                        'explanation': result.integration_quality.explanation
                    },
                    'academic_tone': {
                        'score': result.academic_tone.score,
                        'explanation': result.academic_tone.explanation
                    },
                    'clarity': {
                        'score': result.clarity.score,
                        'explanation': result.clarity.explanation
                    },
                    'coherence': {
                        'score': result.coherence.score,
                        'explanation': result.coherence.explanation
                    },
                    'overall_assessment': result.overall_assessment,
                    'score': round(avg_score, 1)
                }
                
                overall_scores.append(avg_score)
                
            except Exception as e:
                section_scores[section_name] = {
                    'logical_flow': {'score': 3, 'explanation': 'Evaluation failed'},
                    'integration_quality': {'score': 3, 'explanation': 'Evaluation failed'},
                    'academic_tone': {'score': 3, 'explanation': 'Evaluation failed'},
                    'clarity': {'score': 3, 'explanation': 'Evaluation failed'},
                    'coherence': {'score': 3, 'explanation': 'Evaluation failed'},
                    'overall_assessment': 'Evaluation failed due to error',
                    'score': 60.0
                }
                overall_scores.append(60.0)
        
        # Calculate overall average score
        overall_avg_score = sum(overall_scores) / len(overall_scores) if overall_scores else 60.0
        
        return {
            'section_scores': section_scores,
            'overall_score': round(overall_avg_score, 1),
            'sections_evaluated': list(section_scores.keys())
        }
    
    def save_evaluation(self, results: Dict[str, Any], output_path: str = None):
        """Save evaluation results to JSON file"""
        
        if output_path is None:
            report_name = Path(results['report_path']).stem
            output_path = f"evaluation_{report_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Evaluation saved to: {output_path}")
        return output_path


def main():
    """Main function to run evaluations"""
    parser = argparse.ArgumentParser(description="Evaluate research report quality")
    parser.add_argument("report_path", help="Path to the research report markdown file")
    parser.add_argument("--output", "-o", help="Output path for evaluation results")
    parser.add_argument("--model", "-m", default="gpt-4o", help="OpenAI model to use for LLM evaluations")
    parser.add_argument("--no-save", action="store_true", help="Don't save evaluation results")
    
    args = parser.parse_args()
    
    # Initialize evaluator
    evaluator = ResearchReportEvaluator(model=args.model)
    
    # Run evaluation
    results = evaluator.evaluate_report(args.report_path)
    
    # Save results
    if not args.no_save:
        output_path = evaluator.save_evaluation(results, args.output)


if __name__ == "__main__":
    main() 