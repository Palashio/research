from openai import OpenAI
from typing import List, Dict, Any
import json
from search_provider import SearchProvider
from concurrent.futures import ThreadPoolExecutor, as_completed
from prompts import (
    FOLLOW_UP_QUESTIONS_PROMPT,
    INTEGRATE_NEW_INFORMATION_PROMPT,
    INTEGRATE_ARTICLE_WITH_SOURCES_PROMPT,
    FOLLOW_UP_QUESTIONS_FOR_TOPIC_PROMPT,
    CLEAN_ACADEMIC_FORMATTING_PROMPT
)

class ResearchAgent:
    """An LLM agent equipped with search tools for recursive research expansion"""
    
    def __init__(self, model="gpt-4o", search_provider="exa", max_workers=4):
        self.client = OpenAI()
        self.model = model
        self.search_provider = SearchProvider(search_provider)
        self.max_workers = max_workers
        self.conversation_history = []
        
    def search_and_expand_article(self, article: Dict[str, Any], max_expansions: int = 3) -> Dict[str, Any]:
        """
        Recursively search and expand an article with additional research
        
        Args:
            article: Dictionary containing article info (title, url, text, subquestion)
            max_expansions: Maximum number of recursive expansions
            
        Returns:
            Dictionary with expanded content and new sources
        """
        print(f"    🔍 Starting recursive expansion for: {article['title'][:50]}...")
        
        # Initialize expansion state
        expanded_content = article['text']
        new_sources = []
        expansion_count = 0
        
        # Start the recursive expansion process
        while expansion_count < max_expansions:
            # Generate follow-up questions based on current content
            follow_up_questions = self.generate_follow_up_questions(expanded_content, article['subquestion'])
            
            if not follow_up_questions:
                print(f"      ⏹️  No more follow-up questions generated, stopping expansion")
                break
            
            # Search for additional information in parallel
            new_articles = self.search_parallel(follow_up_questions)
            
            print(f"        📊 Found {len(new_articles)} total new articles for expansion")
            
            if not new_articles:
                print(f"        ⏹️  No new articles found, stopping expansion")
                break
            
            # Integrate new information into the content
            expanded_content = self.integrate_new_information(expanded_content, new_articles)
            new_sources.extend(new_articles)
            
            expansion_count += 1
            print(f"      ✅ Completed expansion round {expansion_count}/{max_expansions}")
        
        return {
            'original_article': article,
            'expanded_content': expanded_content,
            'new_sources': new_sources,
            'expansion_rounds': expansion_count
        }
    
    def search_parallel(self, questions: List[str]) -> List[Dict]:
        """Search for multiple questions in parallel"""
        new_articles = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all search tasks
            future_to_question = {
                executor.submit(self.search_single_question, question): question 
                for question in questions
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_question):
                question = future_to_question[future]
                try:
                    articles = future.result()
                    new_articles.extend(articles)
                    print(f"        🔍 Found {len(articles)} articles for question: {question[:50]}...")
                except Exception as e:
                    print(f"        ⚠️  Search error for question '{question}': {e}")
        
        return new_articles
    
    def search_single_question(self, question: str) -> List[Dict]:
        """Search for a single question and return articles"""
        try:
            search_results = self.search_provider.search(question, num_results=2)
            if search_results and search_results.results:
                articles = []
                for result in search_results.results:
                    articles.append({
                        'title': result.title,
                        'url': result.url,
                        'text': result.text,
                        'question': question
                    })
                return articles
            return []
        except Exception as e:
            print(f"        ⚠️  Search error for question '{question}': {e}")
            return []
    
    def generate_follow_up_questions(self, content: str, original_question: str) -> List[str]:
        """Generate follow-up research questions based on content analysis"""
        
        prompt = FOLLOW_UP_QUESTIONS_PROMPT.format(
            content=content[:3000],
            original_question=original_question
        )
        
        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt
            )
            
            questions = response.output_text.strip().split('\n')
            # Clean up questions
            cleaned_questions = []
            for q in questions:
                q = q.strip()
                if q and len(q) > 20 and not q.startswith(('1.', '2.', '3.', '-')):
                    cleaned_questions.append(q)
            
            return cleaned_questions[:3]  # Limit to 3 questions
            
        except Exception as e:
            print(f"      ⚠️  Error generating follow-up questions: {e}")
            return []
    
    def integrate_new_information(self, current_content: str, new_articles: List[Dict]) -> str:
        """Integrate new articles into the existing content"""
        
        # Prepare new article information with source numbers
        new_articles_text = ""
        for i, article in enumerate(new_articles, 1):
            new_articles_text += f"""
<New Article {i}>
Title: {article['title']}
URL: {article['url']}
Content: {article['text'][:1000]}
Related Question: {article['question']}
Source Number: {i}
</New Article {i}>
"""
        
        prompt = INTEGRATE_NEW_INFORMATION_PROMPT.format(
            current_content=current_content,
            new_articles_text=new_articles_text
        )
        
        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt
            )
            
            integrated_content = response.output_text.strip()
            
            # Clean any academic formatting that might have been introduced
            integrated_content = self.clean_academic_formatting(integrated_content)
            
            print(f"          ✅ Integration completed successfully")
            return integrated_content
            
        except Exception as e:
            print(f"      ⚠️  Error integrating new information: {e}")
            return current_content
    
    def synthesize_topic_with_articles(self, topic: str, articles: List[Dict], max_expansions: int = 3, global_source_mapping: Dict[str, int] = None) -> Dict[str, Any]:
        """
        Intelligently synthesize multiple articles into a cohesive topic section
        
        Args:
            topic: The main topic being researched
            articles: List of articles to synthesize
            max_expansions: Maximum number of recursive expansions
            global_source_mapping: Global source mapping from URL to source number
            
        Returns:
            Dictionary with synthesized content and all sources
        """
        print(f"    🔬 Starting intelligent synthesis for topic: {topic}")
        
        # Initialize with the first article as the base
        if not articles:
            return {
                'topic': topic,
                'synthesized_content': f"No articles found for {topic}.",
                'all_sources': [],
                'expansion_rounds': 0
            }
        
        # Start with the first article as the foundation
        current_content = articles[0]['text']
        
        # Clean the initial content of any academic formatting
        current_content = self.clean_academic_formatting(current_content)
        
        # Initialize source tracking
        all_sources = [articles[0]]
        
        # Use global source mapping if provided, otherwise create local one
        if global_source_mapping is None:
            source_mapping = {articles[0]['url']: 1}
        else:
            source_mapping = global_source_mapping
        
        expansion_count = 0
        
        # Integrate remaining articles into the content
        for i, article in enumerate(articles[1:], 1):
            print(f"      🔄 Integrating article {i+1}/{len(articles)}: {article['title'][:50]}...")
            
            # Add new source to mapping if not using global mapping
            if global_source_mapping is None:
                source_mapping[article['url']] = i + 1
            
            # Integrate this article into the current content
            current_content = self.integrate_article_into_content_with_sources(current_content, article, topic, source_mapping)
            all_sources.append(article)
        
        # Now do recursive expansion on the synthesized content
        print(f"      🚀 Starting recursive expansion on synthesized content...")
        
        while expansion_count < max_expansions:
            # Generate follow-up questions based on the synthesized content
            follow_up_questions = self.generate_follow_up_questions_for_topic(current_content, topic)
            
            if not follow_up_questions:
                break
            
            # Search for additional information in parallel
            new_articles = self.search_parallel(follow_up_questions)
            
            if not new_articles:
                break
            
            # Integrate new information into the synthesized content
            for new_article in new_articles:
                print(f"        🔄 Integrating expansion article: {new_article['title'][:50]}...")
                
                # Add new source to mapping (handle both global and local cases)
                if global_source_mapping is not None:
                    # For global mapping, we need to add new URLs to the global mapping
                    if new_article['url'] not in source_mapping:
                        # This is a new URL found during expansion
                        new_source_number = max(source_mapping.values()) + 1 if source_mapping else 1
                        source_mapping[new_article['url']] = new_source_number
                        global_source_mapping[new_article['url']] = new_source_number
                else:
                    # Local mapping case - always assign a new source number
                    source_mapping[new_article['url']] = len(source_mapping) + 1
                
                current_content = self.integrate_article_into_content_with_sources(current_content, new_article, topic, source_mapping)
                all_sources.append(new_article)
                print(f"        ✅ Completed integration of expansion article")
            
            expansion_count += 1
            print(f"        ✅ Completed expansion round {expansion_count}/{max_expansions}")
        
        return {
            'topic': topic,
            'synthesized_content': current_content,
            'all_sources': all_sources,
            'expansion_rounds': expansion_count
        }
    
    def integrate_article_into_content_with_sources(self, current_content: str, new_article: Dict, topic: str, source_mapping: Dict[str, int]) -> str:
        """Intelligently integrate a new article into existing content with source citations"""

        # Get the source number for this article
        source_number = source_mapping.get(new_article['url'], len(source_mapping))
        
        prompt = INTEGRATE_ARTICLE_WITH_SOURCES_PROMPT.format(
            topic=topic,
            current_content=current_content,
            article_title=new_article['title'],
            article_url=new_article['url'],
            article_content=new_article['text'][:1500],
            source_number=source_number
        )
        
        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt
            )
            
            integrated_content = response.output_text.strip()
            
            # Clean any academic formatting that might have been introduced
            integrated_content = self.clean_academic_formatting(integrated_content)
            
            print(f"          ✅ Integration completed successfully")
            return integrated_content
            
        except Exception as e:
            print(f"          ❌ Error integrating article: {e}")
            return current_content
    
    def generate_follow_up_questions_for_topic(self, content: str, topic: str) -> List[str]:
        """Generate follow-up research questions based on synthesized content analysis"""
        
        prompt = FOLLOW_UP_QUESTIONS_FOR_TOPIC_PROMPT.format(
            topic=topic,
            content=content
        )
        
        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt
            )
            
            questions = response.output_text.strip().split('\n')
            # Clean up questions
            cleaned_questions = []
            for q in questions:
                q = q.strip()
                if q and len(q) > 20 and not q.startswith(('1.', '2.', '3.', '-')):
                    # Additional topic relevance check
                    topic_keywords = topic.lower().split()
                    question_lower = q.lower()
                    # Check if the question contains topic-related keywords
                    if any(keyword in question_lower for keyword in topic_keywords):
                        cleaned_questions.append(q)
            
            return cleaned_questions[:3]  # Limit to 3 questions
            
        except Exception as e:
            print(f"      ⚠️  Error generating follow-up questions: {e}")
            return []
    
    def clean_academic_formatting(self, content: str) -> str:
        """Clean the content of any academic formatting"""
        
        prompt = CLEAN_ACADEMIC_FORMATTING_PROMPT.format(content=content)
        
        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt
            )
            
            cleaned_content = response.output_text.strip()
            return cleaned_content
            
        except Exception as e:
            print(f"          ❌ Error cleaning content: {e}")
            return content 