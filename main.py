from openai import OpenAI
from pydantic import BaseModel
from typing import List, Dict
from langgraph.graph import StateGraph
from langchain_exa import ExaSearchResults
import argparse
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from prompts import (
    TOPIC_EXTRACTION_SYSTEM, TOPIC_EXTRACTION_PROMPT,
    SUBQUESTION_SYSTEM, SUBQUESTION_PROMPT
)
from report_generator import generate_report
from search_provider import SearchProvider
from research_agent import ResearchAgent

load_dotenv()

# Initializations
client = OpenAI()


class ResearchTopics(BaseModel):
    topics: List[str]

class Subquestions(BaseModel):
    subquestions: List[str]

def create_initial_state(user_query):
    """Create initial state with user query"""
    return {
        "user_query": user_query,
        "topics": [],
        "subquestions": [],
        "subq_map": {},
        "messages": [
            {
                "role": "user",
                "content": user_query
            }
        ]
    }

def search_node(state):
    search_provider_name = state.get("search_provider", "exa")
    search_provider = SearchProvider(search_provider_name)
    search_results = {}
    current_iteration = state.get("current_iteration", 1)
    max_depth = state.get("depth", 1)

    print(f"\n🔍 Searching with {search_provider_name.upper()} (Iteration {current_iteration}/{max_depth})...")

    # Get questions for this iteration
    questions = state.get("current_questions", state["subquestions"])
    
    for question in questions:
        try:
            results = search_provider.search(question, num_results=5)
            search_results[question] = results

            # Store raw result log in messages
            state["messages"].append({
                "role": "tool",
                "content": results
            })

        except Exception as e:
            print(f"Search error on '{question}' with {search_provider_name}: {e}")
            search_results[question] = []
            state["messages"].append({
                "role": "tool",
                "content": f"[{search_provider_name.upper()}Search] Error on '{question}': {e}"
            })
    
    print(f"Found results for {len(search_results)} questions")
    state["search_results"] = search_results
    state["current_iteration"] = current_iteration
    state["messages"].append({
        "role": "assistant",
        "content": f"Stored raw {search_provider_name.upper()} results for iteration {current_iteration}/{max_depth}"
    })

    return state


def topic_extractor_node(state):
    user_query = state["user_query"]
    model = state.get("topic_model", "gpt-4o")
    detail = state.get("detail", "medium")
    
    # Map detail levels to topic ranges
    detail_ranges = {
        "low": "1-2",
        "medium": "2-3", 
        "high": "3-4"
    }
    topic_range = detail_ranges.get(detail, "2-3")

    response = client.responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": TOPIC_EXTRACTION_SYSTEM.format(topic_range=topic_range)
            },
            {
                "role": "user",
                "content": TOPIC_EXTRACTION_PROMPT.format(
                    user_query=user_query,
                    topic_range=topic_range
                )
            },
        ],
        text_format=ResearchTopics,
    )
    topics = response.output_parsed.topics
    print(topics)
    state["topics"] = topics
    state["messages"].append({
        "role": "assistant",
        "content": f"Extracted topics: {topics}"
    })
    return state

def subquestion_generator_node(state):
    model = state.get("topic_model", "gpt-4o")
    detail = state.get("detail", "medium")
    subq_map = {}
    all_subqs = []

    # Map detail levels to subquestion ranges
    detail_ranges = {
        "low": "1-2",
        "medium": "2-3", 
        "high": "4-5"
    }
    subq_range = detail_ranges.get(detail, "2-3")

    print(f"\n🔍 Generating subquestions with detail level: {detail} ({subq_range} per topic)")

    for topic in state["topics"]:
        response = client.responses.parse(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": SUBQUESTION_SYSTEM
                },
                {
                    "role": "user",
                    "content": SUBQUESTION_PROMPT.format(
                        topic=topic, 
                        user_query=state['user_query'],
                        subq_range=subq_range
                    )
                }
            ],
            text_format=Subquestions
        )

        subqs = response.output_parsed.subquestions
        subq_map[topic] = subqs
        all_subqs.extend(subqs)
    print(subq_map)
    state["subq_map"] = subq_map
    state["subquestions"] = all_subqs
    state["messages"].append({
        "role": "assistant",
        "content": f"Generated subquestions: {subq_map}"
    })
    return state

def follow_up_generator_node(state):
    """Generate follow-up questions based on search results"""
    model = state.get("topic_model", "gpt-4o")
    current_iteration = state.get("current_iteration", 1)
    max_depth = state.get("depth", 1)
    main_query = state["user_query"]
    
    print(f"\n🤔 Generating follow-up questions (Iteration {current_iteration}/{max_depth})...")
    
    # If this is the first iteration, use original subquestions
    if current_iteration == 1:
        state["current_questions"] = state["subquestions"]
        state["all_questions"] = state["subquestions"].copy()
        return state
    
    # Generate follow-up questions from search results
    follow_up_questions = []
    asked_questions = state.get("all_questions", [])
    
    for question, search_response in state.get("search_results", {}).items():
        if not search_response or not search_response.results:
            continue
            
        # Combine article content for this question
        article_content = ""
        for result in search_response.results:
            if result.text:
                article_content += f"\n\nArticle: {result.title}\n{result.text[:1000]}"
        
        if not article_content.strip():
            continue
        
        # Generate follow-up questions
        follow_up_prompt = f"""
Based on this article content, what are 2 meaningful follow-up research questions that could deepen understanding of the original topic: '{main_query}'?

Article Content:
{article_content}

Original Question: {question}

Generate 2 follow-up questions that:
1. Build upon the information in this article
2. Explore deeper aspects of the topic
3. Are specific and researchable
4. Haven't been asked before

Return only the follow-up questions, one per line, with no numbering or bullets:
"""
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": follow_up_prompt}]
            )
            
            generated_questions = response.choices[0].message.content.strip().split('\n')
            
            # Filter and add novel questions
            for q in generated_questions:
                print('generated question:', q)
                q = q.strip()

                # Validate the question
                if (
                    q 
                    and len(q) > 20 
                    and q.lower() not in [aq.lower() for aq in asked_questions]  # check novelty
                ):
                    follow_up_questions.append(q)
                    asked_questions.append(q)

                        
        except Exception as e:
            print(f"Error generating follow-up questions: {e}")
    
    max_follow_ups = min(len(follow_up_questions), 3)  # Max 3 follow-up questions per iteration
    selected_follow_ups = follow_up_questions[:max_follow_ups]
    
    print(f"Generated {len(selected_follow_ups)} follow-up questions")
    for i, q in enumerate(selected_follow_ups, 1):
        print(f"  {i}. {q}")
    
    # Update state
    state["current_questions"] = selected_follow_ups
    state["all_questions"] = asked_questions
    state["messages"].append({
        "role": "assistant",
        "content": f"Generated {len(selected_follow_ups)} follow-up questions for iteration {current_iteration}"
    })
    
    return state

def iteration_controller_node(state):
    """Control the research iteration flow"""
    current_iteration = state.get("current_iteration", 1)
    max_depth = state.get("depth", 1)
    
    print(f"\n🔄 Research Iteration {current_iteration}/{max_depth}")
    
    # Check if we should continue to next iteration
    if current_iteration < max_depth:
        # Prepare for next iteration
        state["current_iteration"] = current_iteration + 1
        state["next_node"] = "follow_up_generator"
        print(f"Continuing to iteration {current_iteration + 1}")
    else:
        # Research complete, move to synthesis
        state["next_node"] = "article_synthesis_with_expansion"
        print(f"Research complete after {max_depth} iterations")
    
    return state

def route_after_iteration(state):
    """Route to the next node based on iteration controller decision"""
    return state.get("next_node", "article_synthesis_with_expansion")

def article_synthesis_with_expansion_node(state):
    """Synthesize articles with intelligent integration and recursive research expansion"""
    model = state.get("summary_model", "gpt-4o")
    search_provider = state.get("search_provider", "exa")
    max_expansions = state.get("max_expansions", 3)
    max_workers = state.get("max_workers", 4)
    
    print(f"\n🔬 Synthesizing articles with intelligent integration and expansion...")
    
    # Initialize research agent with parallel processing
    research_agent = ResearchAgent(model=model, search_provider=search_provider, max_workers=max_workers)
    expanded_sections = {}
    
    # Create global source mapping to ensure consistent citation numbering
    global_source_mapping = {}
    global_source_counter = 1
    
    # First pass: collect all unique URLs and assign global source numbers
    all_unique_urls = set()
    for topic in state["topics"]:
        topic_subqs = state["subq_map"].get(topic, [])
        for subq in topic_subqs:
            search_response = state["search_results"].get(subq)
            if search_response and search_response.results:
                for result in search_response.results:
                    if result.url not in all_unique_urls:
                        all_unique_urls.add(result.url)
                        global_source_mapping[result.url] = global_source_counter
                        global_source_counter += 1
    
    print(f"   📊 Created global source mapping with {len(global_source_mapping)} unique sources")
    
    for topic in state["topics"]:
        print(f"   🔄 Processing topic: {topic}")
        topic_subqs = state["subq_map"].get(topic, [])
        
        # Get all search results for this topic's subquestions
        topic_articles = []
        for subq in topic_subqs:
            search_response = state["search_results"].get(subq)
            if search_response and search_response.results:
                for result in search_response.results:
                    topic_articles.append({
                        "subquestion": subq,
                        "title": result.title,
                        "url": result.url,
                        "text": result.text,
                        "source_id": global_source_mapping.get(result.url, global_source_counter)
                    })
        
        if not topic_articles:
            expanded_sections[topic] = f"No articles found for {topic}."
            continue
        
        print(f"   📚 Found {len(topic_articles)} articles for {topic}")
        
        # Use intelligent synthesis to create cohesive topic section with global source mapping
        synthesis_result = research_agent.synthesize_topic_with_articles(
            topic=topic, 
            articles=topic_articles, 
            max_expansions=max_expansions,
            global_source_mapping=global_source_mapping
        )
        
        # Store the synthesized content
        expanded_sections[topic] = synthesis_result['synthesized_content']
        
        # Store all sources for later use in the report
        if "all_new_sources" not in state:
            state["all_new_sources"] = []
        state["all_new_sources"].extend(synthesis_result['all_sources'])
        
        print(f"   ✅ Completed intelligent synthesis for {topic} ({synthesis_result['expansion_rounds']} expansion rounds)")
    
    # Update state
    state["expanded_sections"] = expanded_sections
    state["global_source_mapping"] = global_source_mapping
    print(f"✅ Completed intelligent synthesis for {len(expanded_sections)} topics")
    
    return state

State = dict
graph = StateGraph(State)

# Add nodes
graph.add_node("extract_topics", topic_extractor_node)
graph.add_node("generate_subqs", subquestion_generator_node)
graph.add_node("search_node", search_node)
graph.add_node("generate_report", generate_report)
graph.add_node("follow_up_generator", follow_up_generator_node)
graph.add_node("iteration_controller", iteration_controller_node)
graph.add_node("article_synthesis_with_expansion", article_synthesis_with_expansion_node)

# Connect nodes
graph.set_entry_point("extract_topics")
graph.add_edge("extract_topics", "generate_subqs")
graph.add_edge("generate_subqs", "follow_up_generator")
graph.add_edge("follow_up_generator", "search_node")
graph.add_edge("search_node", "iteration_controller")
graph.add_conditional_edges(
    "iteration_controller",
    route_after_iteration,
    {
        "follow_up_generator": "follow_up_generator",
        "article_synthesis_with_expansion": "article_synthesis_with_expansion"
    }
)
graph.add_edge("article_synthesis_with_expansion", "generate_report")
graph.set_finish_point("generate_report")

# Compile graph
app = graph.compile()

def main():
    """Main function to run the research pipeline"""
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
  python main.py --query "Deep dive into quantum computing" --depth 3 --detail high
  python main.py --query "Comprehensive AI research" --depth 5 --search-provider exa --legend
  python main.py --query "Renewable energy breakthroughs" --max-expansions 5 --legend
  python main.py --query "Future of electric vehicles" --max-expansions 4 --detail high --legend
  python main.py --query "Quantum computing advances" --max-workers 8 --max-expansions 3 --legend
  python main.py --query "AI in healthcare" --max-workers 6 --depth 3 --max-expansions 4 --legend
        """
    )
    
    parser.add_argument(
        "--query", 
        required=True,
        help="Research question to investigate"
    )
    
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
    
    parser.add_argument(
        "--detail", 
        choices=["low", "medium", "high"],
        default="medium",
        help="Detail level for subquestion generation: low (1-2), medium (2-3), high (4-5) (default: medium)"
    )
    
    parser.add_argument(
        "--depth", 
        type=int,
        default=1,
        help="Research depth: number of follow-up iterations (1-10, default: 1)"
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
    
    parser.add_argument(
        "--search-provider", 
        choices=["exa", "tavily"],
        default="exa",
        help="Search provider to use: exa or tavily (default: exa)"
    )
    
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
    
    args = parser.parse_args()
    
    # Create initial state with user query and models
    initial_state = create_initial_state(args.query)
    initial_state["topic_model"] = args.topic_model
    initial_state["summary_model"] = args.summary_model
    initial_state["detail"] = args.detail
    initial_state["depth"] = args.depth
    initial_state["max_expansions"] = args.max_expansions
    initial_state["max_workers"] = args.max_workers
    initial_state["search_provider"] = args.search_provider
    initial_state["legend"] = args.legend
    
    try:
        # Run the research pipeline
        result = app.invoke(initial_state)
        
        # Report is already saved in the generate_report node
        filename = result.get("report_filename", "research_report.md")
        print(f"\n✅ Research report saved to: {filename}")
        
    except Exception as e:
        print(f"\n❌ Error during research pipeline execution: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())