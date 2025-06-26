"""
Argument Parser Module

This module handles all command-line argument parsing for the research pipeline,
providing a clean separation of concerns and better maintainability.
"""

import argparse
from typing import Dict, Any


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser for the research pipeline.
    
    Returns:
        Configured ArgumentParser instance with all pipeline options
    """
    parser = argparse.ArgumentParser(
        description="Automated Research Pipeline using LangGraph and Exa Search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --query "What are the latest developments in renewable energy?"
  python main.py --query "How has AI impacted healthcare?" --topic-model gpt-4o-mini
  python main.py --query "Economic implications of climate change" --summary-model gpt-4o
  python main.py --query "Latest tech trends" --legend
  python main.py --query "Space exploration advances" --detail high --legend
  python main.py --query "Climate change impacts" --search-provider tavily --detail medium
  python main.py --query "Deep dive into quantum computing" --breadth 3 --detail high
  python main.py --query "Comprehensive AI research" --breadth 5 --search-provider exa --legend
  python main.py --query "Renewable energy breakthroughs" --max-expansions 5 --legend
  python main.py --query "Future of electric vehicles" --max-expansions 4 --detail high --legend
  python main.py --query "Quantum computing advances" --max-workers 8 --max-expansions 3 --legend
  python main.py --query "AI in healthcare" --max-workers 6 --breadth 3 --max-expansions 4 --legend
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--query", 
        required=True,
        help="Research question to investigate"
    )
    
    # Model configuration
    parser.add_argument(
        "--topic-model", 
        default="gpt-4o",
        help="OpenAI model for topic generation and subquestion creation (default: gpt-4o)"
    )
    
    parser.add_argument(
        "--summary-model", 
        default="gpt-4o",
        help="OpenAI model for synthesis and report generation (default: gpt-4o)"
    )
    
    # Research configuration
    parser.add_argument(
        "--detail", 
        choices=["low", "medium", "high"],
        default="medium",
        help="Detail level for subquestion generation: low (1-2), medium (2-3), high (4-5) (default: medium)"
    )
    
    parser.add_argument(
        "--breadth", 
        type=int,
        default=1,
        help="Research breadth: number of follow-up iterations (1-10, default: 1)"
    )
    
    parser.add_argument(
        "--max-expansions", 
        type=int,
        default=3,
        help="Maximum recursive expansion rounds per article (1-5, default: 3)"
    )
    
    parser.add_argument(
        "--max-workers", 
        type=int,
        default=4,
        help="Number of parallel workers for article expansion (1-10, default: 4)"
    )
    
    # Search configuration
    parser.add_argument(
        "--search-provider", 
        choices=["exa", "tavily"],
        default="exa",
        help="Search provider to use: exa or tavily (default: exa)"
    )
    
    # Output configuration
    parser.add_argument(
        "--legend", 
        action="store_true",
        help="Add a table of contents (legend) to the report"
    )
    
    parser.add_argument(
        "--verbose", 
        "-v", 
        action="store_true",
        help="Enable verbose output with detailed progress information"
    )
    
    return parser


def parse_arguments() -> Dict[str, Any]:
    """
    Parse command-line arguments and return them as a dictionary.
    
    Returns:
        Dictionary containing all parsed arguments and their values
    """
    parser = create_argument_parser()
    args = parser.parse_args()
    
    return {
        "query": args.query,
        "topic_model": args.topic_model,
        "summary_model": args.summary_model,
        "detail": args.detail,
        "breadth": args.breadth,
        "max_expansions": args.max_expansions,
        "max_workers": args.max_workers,
        "search_provider": args.search_provider,
        "legend": args.legend,
        "verbose": args.verbose
    }
