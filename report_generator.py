from openai import OpenAI
import datetime
from prompts import INTRODUCTION_PROMPT, CONCLUSION_PROMPT

def generate_report(state):
    # Initialize OpenAI client
    client = OpenAI()
    
    model = state.get("summary_model", "gpt-4o")
    legend_enabled = state.get("legend", True)
    print("\n📝 Generating research report...")
    
    # Use expanded sections for the report (new architecture)
    topic_content = ""
    if "expanded_sections" in state:
        # Use the new expanded sections from research agent
        for topic in state["topics"]:
            section = state["expanded_sections"].get(topic, f"No information available for {topic}.")
            topic_content += f"\nTopic: {topic}\nSection: {section}\n"
    else:
        # Fallback to old topic sections if expanded sections not available
        for topic in state["topics"]:
            section = state["topic_sections"].get(topic, f"No information available for {topic}.")
            topic_content += f"\nTopic: {topic}\nSection: {section}\n"
    
    # Intro generation using topic sections
    intro_prompt = INTRODUCTION_PROMPT.format(
        user_query=state['user_query'], 
        topic_content=topic_content
    )
    intro = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": intro_prompt}]
    ).choices[0].message.content.strip()

    # Conclusion generation using topic sections
    conclusion_prompt = CONCLUSION_PROMPT.format(
        user_query=state['user_query'], 
        topic_content=topic_content
    )
    conclusion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": conclusion_prompt}]
    ).choices[0].message.content.strip()

    # Body formatting using expanded sections
    body = ""
    if "expanded_sections" in state:
        # Use the new expanded sections
        for topic in state["topics"]:
            section = state["expanded_sections"].get(topic, f"No information available for {topic}.")
            body += f"\n## {topic}\n\n{section}\n"
    else:
        # Fallback to old topic sections
        for topic in state["topics"]:
            section = state["topic_sections"].get(topic, f"No information available for {topic}.")
            body += f"\n## {topic}\n\n{section}\n"

    # Create legend (table of contents) if enabled
    legend_section = ""
    if legend_enabled:
        legend_section = "\n## Table of Contents\n\n"
        legend_section += "1. [Introduction](#introduction)\n"
        for i, topic in enumerate(state["topics"], 2):
            # Create anchor-friendly topic name (lowercase, replace spaces with hyphens)
            anchor = topic.lower().replace(" ", "-").replace(",", "").replace(":", "")
            legend_section += f"{i}. [{topic}](#{anchor})\n"
        legend_section += f"{len(state['topics']) + 2}. [Conclusion](#conclusion)\n"
        legend_section += f"{len(state['topics']) + 3}. [Sources](#sources)\n\n"

    # Collect all sources from research agent expansion
    sources_section = ""
    all_sources = {}
    
    # Use global source mapping if available
    if state.get("global_source_mapping"):
        global_mapping = state["global_source_mapping"]
        
        # Add sources from research agent expansion with global numbering
        if state.get("all_new_sources"):
            for new_source in state["all_new_sources"]:
                source_id = global_mapping.get(new_source['url'])
                if source_id and new_source['url'] not in [s['url'] for s in all_sources.values()]:
                    all_sources[source_id] = {
                        'id': source_id,
                        'url': new_source['url'],
                        'title': new_source['title']
                    }
    else:
        # Fallback to old method
        if state.get("all_new_sources"):
            for i, new_source in enumerate(state["all_new_sources"], 1):
                if new_source['url'] not in [s['url'] for s in all_sources.values()]:
                    all_sources[i] = {
                        'id': i,
                        'url': new_source['url'],
                        'title': new_source['title']
                    }

    # Sort by ID and create sources section
    if all_sources:
        sources_section = "\n## Sources\n\n"
        for source_id in sorted(all_sources.keys()):
            source = all_sources[source_id]
            sources_section += f"[{source['id']}] {source['title']} - {source['url']}\n\n"

    # Final report assembly
    report = f"# Research Report\n\n{legend_section}## Introduction\n\n{intro}\n\n{body}\n\n## Conclusion\n\n{conclusion}{sources_section}"
    
    # Save report to markdown file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"research_report_{timestamp}.md"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ Report generated and saved to: {filename}")

    # Update state
    state["report"] = report
    state["report_filename"] = filename
    state["messages"].append({
        "role": "assistant",
        "content": f"[Report Generation] Complete report saved to {filename}"
    })
    
    return state 