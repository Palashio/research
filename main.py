from openai import OpenAI
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph
from langchain_exa import ExaSearchResults
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from prompts import (
    TOPIC_EXTRACTION_SYSTEM, TOPIC_EXTRACTION_PROMPT,
    SUBQUESTION_PROMPT,
    FOLLOW_UP_GENERATION_PROMPT
)
from report_generator import generate_report
from search_provider import SearchProvider
from research_agent import ResearchAgent
from arg_parser import parse_arguments

load_dotenv()

# Initialize OpenAI client
client = OpenAI()


class ResearchTopics(BaseModel):
    """Pydantic model for structured topic extraction."""
    topics: List[str]


class Subquestions(BaseModel):
    """Pydantic model for structured subquestion generation."""
    subquestions: List[str]


def create_initial_state(user_query: str) -> Dict[str, Any]:
    """
    Create initial state with user query and default values.
    
    Args:
        user_query: The research question to investigate
        
    Returns:
        Dictionary containing the initial state with user query, empty topics,
        subquestions, and initial message history
    """
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

def search_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search for information using the specified search provider.
    
    This node performs web searches for each question in the current iteration,
    storing results in the state for later processing.
    
    Args:
        state: Current pipeline state containing questions and configuration
        
    Returns:
        Updated state with search results for each question
    """
    search_provider_name = state.get("search_provider", "exa")
    search_provider = SearchProvider(search_provider_name)
    search_results = {}
    current_iteration = state.get("current_iteration", 1)
    max_breadth = state.get("breadth", 1)

    print(f"\n🔍 Searching with {search_provider_name.upper()} (Iteration {current_iteration}/{max_breadth})...")

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
        "content": f"Stored raw {search_provider_name.upper()} results for iteration {current_iteration}/{max_breadth}"
    })

    return state


def topic_extractor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract main topics from the user query.
    
    This node uses AI to break down the research question into 2-4 main topics
    that can be investigated independently.
    
    Args:
        state: Current pipeline state containing the user query
        
    Returns:
        Updated state with extracted topics
    """
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
    state["topics"] = topics
    state["messages"].append({
        "role": "assistant",
        "content": f"Extracted topics: {topics}"
    })
    return state

def subquestion_generator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate specific subquestions for each topic.
    
    This node creates detailed, researchable questions for each extracted topic,
    mapping them back to the original user query.
    
    Args:
        state: Current pipeline state containing topics
        
    Returns:
        Updated state with subquestions and topic mapping
    """
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

    state["subq_map"] = subq_map
    state["subquestions"] = all_subqs
    state["messages"].append({
        "role": "assistant",
        "content": f"Generated subquestions: {subq_map}"
    })
    
    return state

def follow_up_generator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate follow-up questions based on search results.
    
    This node analyzes search results from previous iterations to generate
    new, more specific research questions that build upon found information.
    
    Args:
        state: Current pipeline state containing search results
        
    Returns:
        Updated state with follow-up questions for next iteration
    """
    model = state.get("topic_model", "gpt-4o")
    current_iteration = state.get("current_iteration", 1)
    max_breadth = state.get("breadth", 1)
    main_query = state["user_query"]
    
    print(f"\n🤔 Generating follow-up questions (Iteration {current_iteration}/{max_breadth})...")
    
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
        follow_up_prompt = FOLLOW_UP_GENERATION_PROMPT.format(
            main_query=main_query,
            article_content=article_content,
            question=question
        )
        
        try:
            response = client.responses.create(
                model=model,
                input=follow_up_prompt
            )
            
            generated_questions = response.output_text.strip().split('\n')
            
            # Filter and add novel questions
            for q in generated_questions:
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
    
    # Update state
    state["current_questions"] = selected_follow_ups
    state["all_questions"] = asked_questions
    state["messages"].append({
        "role": "assistant",
        "content": f"Generated {len(selected_follow_ups)} follow-up questions for iteration {current_iteration}"
    })
    
    return state

def iteration_controller_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Control the research iteration flow.
    
    This node determines whether to continue with more iterations or move
    to the synthesis phase based on the configured breadth parameter.
    
    Args:
        state: Current pipeline state with iteration information
        
    Returns:
        Updated state with next node routing information
    """
    current_iteration = state.get("current_iteration", 1)
    max_breadth = state.get("breadth", 1)
    
    print(f"\n🔄 Research Iteration {current_iteration}/{max_breadth}")
    
    # Check if we should continue to next iteration
    if current_iteration < max_breadth:
        # Prepare for next iteration
        state["current_iteration"] = current_iteration + 1
        state["next_node"] = "follow_up_generator"
        print(f"Continuing to iteration {current_iteration + 1}")
    else:
        # Research complete, move to synthesis
        state["next_node"] = "article_synthesis_with_expansion"
        print(f"Research complete after {max_breadth} iterations")
    
    return state

def route_after_iteration(state: Dict[str, Any]) -> str:
    """
    Route to the next node based on iteration controller decision.
    
    Args:
        state: Current pipeline state with routing information
        
    Returns:
        Name of the next node to execute
    """
    return state.get("next_node", "article_synthesis_with_expansion")

def article_synthesis_with_expansion_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synthesize articles with intelligent integration and recursive research expansion.
    
    This node uses the ResearchAgent to intelligently combine all search results
    into cohesive topic sections, then performs additional recursive expansion
    to deepen understanding of each topic.
    
    Args:
        state: Current pipeline state with all search results
        
    Returns:
        Updated state with synthesized and expanded content
    """
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
    
    # Prepare topic processing tasks for parallel execution
    def process_topic(topic: str) -> tuple[str, Dict[str, Any]]:
        """Process a single topic and return (topic, synthesis_result)"""
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
            return topic, {
                'synthesized_content': f"No articles found for {topic}.",
                'all_sources': [],
                'expansion_rounds': 0.
            }
        
        print(f"   📚 Found {len(topic_articles)} articles for {topic}")
        
        # Use intelligent synthesis to create cohesive topic section with global source mapping
        synthesis_result = research_agent.synthesize_topic_with_articles(
            topic=topic, 
            articles=topic_articles, 
            max_expansions=max_expansions,
            global_source_mapping=global_source_mapping
        )
        
        print(f"   ✅ Completed intelligent synthesis for {topic} ({synthesis_result['expansion_rounds']} expansion rounds)")
        return topic, synthesis_result
    
    # Process topics in parallel
    all_new_sources = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all topic processing tasks
        future_to_topic = {
            executor.submit(process_topic, topic): topic 
            for topic in state["topics"]
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_topic):
            topic = future_to_topic[future]
            try:
                topic_name, synthesis_result = future.result()
                expanded_sections[topic_name] = synthesis_result['synthesized_content']
                all_new_sources.extend(synthesis_result['all_sources'])
            except Exception as e:
                print(f"   ❌ Error processing topic '{topic}': {e}")
                expanded_sections[topic] = f"Error processing {topic}: {str(e)}"
    
    # Update state
    state["expanded_sections"] = expanded_sections
    state["global_source_mapping"] = global_source_mapping
    state["all_new_sources"] = all_new_sources
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

def main() -> int:
    """
    Main function to run the research pipeline.
    
    This function sets up the argument parser, creates the initial state,
    and executes the LangGraph pipeline to generate a comprehensive research report.
    
    Returns:
        0 on success, 1 on error
    """
    try:
        # Parse and validate arguments
        args = parse_arguments()
        
        # Create initial state with user query and models
        initial_state = create_initial_state(args["query"])
        initial_state["topic_model"] = args["topic_model"]
        initial_state["summary_model"] = args["summary_model"]
        initial_state["detail"] = args["detail"]
        initial_state["breadth"] = args["breadth"]
        initial_state["max_expansions"] = args["max_expansions"]
        initial_state["max_workers"] = args["max_workers"]
        initial_state["search_provider"] = args["search_provider"]
        initial_state["legend"] = args["legend"]
        
        # Run the research pipeline
        result = app.invoke(initial_state)
        
        # Report is already saved in the generate_report node
        filename = result.get("report_filename", "research_report.md")
        print(f"\n✅ Research report saved to: {filename}")
        
    except Exception as e:
        print(f"\n❌ Error during research pipeline execution: {e}")
        if args.get("verbose"):
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())