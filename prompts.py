# Topic Extraction Prompts
TOPIC_EXTRACTION_SYSTEM = """
You are a strategic research planner. Break down research questions into {topic_range} major topics that would be important to investigate.

These should be topics that can be answered by web search results and articles. Do not be too general in your topics. 
"""

TOPIC_EXTRACTION_PROMPT = """
<Context>
You are a strategic research planner. Break down research questions into {topic_range} major topics that would be important to investigate.

These should be topics that can be answered by web search results and articles. Do not be too general in your topics. Make sure that the topics are varied from each other. 
</Context>

<Question>
{user_query}
</Question>
"""

# Subquestion Generation Prompts
SUBQUESTION_PROMPT = """
Given the topic "{topic}", write {subq_range} insightful and specific subquestions related to this broader research question:
"{user_query}"

Generate subquestions that will help thoroughly investigate this topic.
"""

# Fact Extraction Prompts
FACT_EXTRACTION_PROMPT = """
You are a fact extraction specialist. Given a subquestion and an article, extract only the factual information that could help in answering the question.

<Subquestion>
{subquestion}
</Subquestion>

<Article text>
{article_text}
</Article text>

<Task>
Extract only the key facts, statistics, names, dates, and specific information that directly answer the subquestion. 
- Focus on concrete, verifiable information
- Exclude opinions, speculation, or general statements
- Include source information: [{source_number}]
- Format as a clean list of facts
- Do NOT include the subquestion in your response
</Task>

<Output>
Return only the extracted facts:
</Output>
"""

# Topic Synthesis Prompts
TOPIC_SYNTHESIS_PROMPT = """
You are a research analyst writing a comprehensive section for a research report.

<Topic>
{topic}
</Topic>

<Facts>
Below are all the relevant facts extracted from research on this topic:

{combined_facts}
</Facts>

<Task>
Please write a comprehensive, well-structured section that synthesizes all these facts into a coherent narrative about {topic}. 
Do not include the title of the topic in your response, that will be inserted later. 

CRITICAL REQUIREMENTS:
- Use ONLY the source numbers that are already provided in the facts above
- For example, if you see "From Source 3:" in the facts, use [3] in your citations
- If you see "From Source 1:" in the facts, use [1] in your citations
- DO NOT create any new source numbers that are not in the facts
- DO NOT use numbers like [18], [22], [42], etc. unless they appear in the facts above
- The only valid source numbers are the ones that start with "From Source X:" in the facts

Other Requirements:
- Integrate all the key facts into a logical flow
- Maintain proper transitions between ideas
- Focus on the most important insights and connections
- Write in a professional, analytical tone
- Make it engaging and informative for readers
</Task>
"""

# Report Generation Prompts
INTRODUCTION_PROMPT = """
You are a research analyst writing the introduction to a structured report.

The user asked: "{user_query}"

Here are the synthesized sections by topic:

{topic_content}

Write an engaging, informative **introduction** that sets up the structure of the report, based on the topics and findings. The introduction should be no longer than one paragraph long.
"""

CONCLUSION_PROMPT = """
You are a research analyst writing the conclusion to a structured report.


<User query>
"{user_query}"
</User query>

<Key sections by topic>
{topic_content}
</Key sections by topic>

<Task>
Write a thoughtful **conclusion** that summarizes the major insights and takeaways across topics. Do not introduce new information. The conclusion should be no longer than one paragraphs long.
</Task>
"""

# Subquestion Synthesis Prompts (for the old synthesize_subq_results_node)
SUBQUESTION_SYNTHESIS_SYSTEM = """
You are a research assistant. Write clear, well-structured summaries that answer questions using provided sources. Do not hallucinate.
You have been provided with search results below. Only use this information.
If you cannot answer based on the sources, say so explicitly.

IMPORTANT: When you use information from the sources, cite them using [1], [2], [3], etc. format. If you are citing multiple sources, put them next to each other like [1][2]. 
Always cite the specific source number when making claims or using information from that source.
"""

SUBQUESTION_SYNTHESIS_PROMPT = """
<Subquestion>
"{subquestion}"
</Subquestion>

<Raw search results from trusted sources>
{combined_sources}
</Raw search results from trusted sources>

<Source references>
{source_refs}
</Source references>

<Task>
Please write a clear, well-structured summary that answers the subquestion using the provided sources. 
Cite sources using [1], [2], [3], etc. when you use information from them.
Do not hallucinate. If you cannot answer based on the sources, say so explicitly.
</Task>
"""

# Research Agent Prompts
FOLLOW_UP_QUESTIONS_PROMPT = """
You are a research analyst. Analyze this content and identify areas that need more research.

<Content>
{content}
</Content>

<Original Question>
{original_question}
</Original Question>

<Task>
Generate 2-3 specific follow-up research questions that would help expand understanding of this topic. Focus on:
1. Gaps in the current information
2. Areas that need more detail or examples
3. Related aspects that aren't covered
4. Recent developments or trends

Requirements:
- Questions should be specific and researchable
- Focus on the most important missing information
- Avoid questions that are already answered in the content
- Make questions that would lead to valuable new insights

Return only the questions, one per line:
"""

INTEGRATE_NEW_INFORMATION_PROMPT = """
You are a research analyst tasked with integrating new information into existing content.

<Current Content>
{current_content}
</Current Content>

<New Articles to Integrate>
{new_articles_text}
</New Articles to Integrate>

<Task>
Integrate the new information from the articles into the current content. Your goal is to:

1. Seamlessly weave in the new information where it's most relevant
2. Maintain the logical flow and structure of the content
3. Add proper citations for the new information using the source numbers provided
4. Avoid redundancy - don't repeat information that's already covered
5. Focus on the most important and relevant new insights

<CITATION REQUIREMENTS - ABSOLUTELY CRITICAL>
- **EVERY SINGLE PIECE OF INFORMATION from the new articles MUST be cited with the appropriate source number**
- **This includes: facts, statistics, concepts, explanations, background information, examples, descriptions, processes, methods, advantages, disadvantages, comparisons, historical context, technical details, and ANY other content from the articles**
- **NO EXCEPTIONS - even if something seems like common knowledge, if it comes from an article, it must be cited**
- **Place citations immediately after the relevant information**
- **Include citations throughout the text, not just at the end**
- **Every sentence that contains information from a new article must have a citation**
- **If you integrate information from an article, you MUST cite it - no exceptions**

<Examples of Proper Citation Usage>
- "Solar cells achieve 24.6% efficiency [1]."
- "The new technology reduces costs by 30% [2]."
- "According to recent studies, this approach shows promise [3]."
- "The basic principle involves converting sunlight into electricity [1]."
- "Researchers have developed several methods for improving performance [2]."
- "The technology works by capturing photons and generating electron-hole pairs [3]."
- "This approach offers several advantages over traditional methods [1]."
- "The company was founded in 2010 and has since grown significantly [2]."
- "The manufacturing process involves several key steps [3]."
- "This development represents a major breakthrough in the field [1]."

<Requirements>
- Maintain professional, academic tone
- Keep the content coherent and well-structured
- Prioritize the most valuable new insights

<Output>
Return the integrated content that combines the original and new information with proper in-text citations:
"""

INTEGRATE_ARTICLE_WITH_SOURCES_PROMPT = """
You are a research analyst tasked with intelligently integrating new information into existing content about a SPECIFIC TOPIC.

<SPECIFIC TOPIC TO FOCUS ON>
{topic}
</SPECIFIC TOPIC TO FOCUS ON>

<Current Content>
{current_content}
</Current Content>

<New Article to Integrate>
Title: {article_title}
URL: {article_url}
Content: {article_content}
Source Number: {source_number}
</New Article to Integrate>

<Task>
Integrate the new information from the article into the current content, but ONLY if it's directly relevant to "{topic}".

**CRITICAL REQUIREMENTS:**
- ONLY integrate information that is DIRECTLY related to "{topic}"
- IGNORE any information in the article that is not about "{topic}"
- Do NOT add information about other topics or broader subjects
- Focus ONLY on enhancing understanding of "{topic}" specifically
- If the article contains little or no information about "{topic}", return the current content unchanged

Your goal is to:

1. **Seamlessly weave** the new information where it's most relevant and logical
2. **Maintain the flow** and structure of the existing content
3. **Add proper citations** for the new information using [{source_number}]
4. **Avoid redundancy** - don't repeat information that's already covered
5. **Enhance understanding** - use the new information to provide more depth, examples, or context about "{topic}"
6. **Create a cohesive narrative** - make the content read like a unified research section about "{topic}"
7. **Stay on topic** - ensure all integrated information is directly about "{topic}"

<CITATION REQUIREMENTS - ABSOLUTELY CRITICAL>
- **EVERY SINGLE PIECE OF INFORMATION from the new article MUST be cited with [{source_number}]**
- **This includes: facts, statistics, concepts, explanations, background information, examples, descriptions, processes, methods, advantages, disadvantages, comparisons, historical context, technical details, and ANY other content from the article**
- **NO EXCEPTIONS - even if something seems like common knowledge, if it comes from the article, it must be cited**
- **Place citations immediately after the relevant information**
- **Include citations throughout the text, not just at the end**
- **Every sentence that contains information from the new article must have a citation**
- **If you integrate information from the article, you MUST cite it - no exceptions**

<Examples of Proper Citation Usage>
- "Solar cells achieve 24.6% efficiency [{source_number}]."
- "The new technology reduces costs by 30% [{source_number}]."
- "According to recent studies, this approach shows promise [{source_number}]."
- "The basic principle involves converting sunlight into electricity [{source_number}]."
- "Researchers have developed several methods for improving performance [{source_number}]."
- "The technology works by capturing photons and generating electron-hole pairs [{source_number}]."
- "This approach offers several advantages over traditional methods [{source_number}]."
- "The company was founded in 2010 and has since grown significantly [{source_number}]."
- "The manufacturing process involves several key steps [{source_number}]."
- "This development represents a major breakthrough in the field [{source_number}]."

<Requirements>
- Maintain professional, academic tone
- Keep the content coherent and well-structured
- Prioritize the most valuable new insights about "{topic}"
- Don't make the content unnecessarily long
- Focus on information that directly relates to "{topic}"
- Integrate rather than append - weave new information into existing paragraphs
- DO NOT include any "References:", "Citations:", or "Sources:" sections
- DO NOT include any academic formatting like "Abstract:", "Introduction:", "Conclusion:"
- DO NOT include any bold titles or section headers
- DO NOT create subsections - integrate everything into the main narrative flow
- Write in a natural, flowing style without academic structure
- **CRITICAL: If the article contains no relevant information about "{topic}", return the current content unchanged**

<Output>
Return the integrated content that seamlessly combines the original and new information in a natural, flowing narrative with proper in-text citations, focusing ONLY on "{topic}":
"""

FOLLOW_UP_QUESTIONS_FOR_TOPIC_PROMPT = """
You are a research analyst. Analyze this synthesized content about a SPECIFIC TOPIC and identify areas that need more research.

<Specific topic to focus on>
{topic}
</Specific topic to focus on>

<Content>
{content}
</Content>

<Task>
Generate 2-3 specific follow-up research questions that would help expand understanding of THIS SPECIFIC TOPIC ONLY. 

**CRITICAL REQUIREMENTS:**
- Questions must be DIRECTLY related to "{topic}" and nothing else
- Do NOT generate questions about other topics or broader subjects
- Focus ONLY on gaps, details, or aspects missing from the current content about "{topic}"
- Questions should help deepen understanding of "{topic}" specifically

Focus on:
1. Gaps in the current information about "{topic}"
2. Areas of "{topic}" that need more detail or examples
3. Related aspects of "{topic}" that aren't covered
4. Recent developments or trends specifically in "{topic}"
5. Specific aspects of "{topic}" mentioned but not fully explored

**EXAMPLES OF GOOD QUESTIONS (if topic is "Solar Energy"):**
- "What are the latest efficiency improvements in solar panel technology?"
- "How do different solar cell materials compare in cost and performance?"
- "What are the environmental impacts of solar panel manufacturing?"

**EXAMPLES OF BAD QUESTIONS (too broad or off-topic):**
- "What are the benefits of renewable energy?" (too broad)
- "How does wind energy work?" (different topic)
- "What is climate change?" (unrelated topic)

Requirements:
- Questions should be specific and researchable
- Focus on the most important missing information about "{topic}"
- Avoid questions that are already answered in the content
- Make questions that would lead to valuable new insights about "{topic}"
- Questions must be directly related to "{topic}" and nothing else
- Use natural, conversational language (not academic style)
- Focus on practical, real-world aspects of "{topic}"

Return only the questions, one per line:
"""

CLEAN_ACADEMIC_FORMATTING_PROMPT = """
You are a research analyst tasked with cleaning content of any academic formatting to create a natural, flowing narrative.

<Content>
{content}
</Content>

<Task>
Clean the content by removing any academic formatting and creating a natural, flowing narrative.

<Requirements>
- Remove any "Abstract:", "Introduction:", "Conclusion:", "References:", "Citations:", "Sources:" sections
- Remove any bold titles like "**Title**" or section headers
- Remove any numbered sections like "1. Introduction", "2. Methods", etc.
- Remove any academic structure and create a natural, flowing narrative
- Keep all the valuable information but present it in a natural way
- Ensure the content reads like a unified research section, not an academic paper
- **CRITICAL: Preserve ALL in-text citations like [1], [2], [3], etc. - DO NOT remove them**
- **CRITICAL: Keep citations in their original positions within the text**
- **CRITICAL: Do not change citation numbers or format**
- Remove any reference lists at the end, but keep all in-text citations
- Write in a professional but accessible tone

<Output>
Return the cleaned content as a natural, flowing narrative without academic formatting, but with all in-text citations preserved. If you need you are allowed to create sub-sections, but they must be topic specific:
""" 