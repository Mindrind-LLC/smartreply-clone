import logging

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from core.config import settings
from models.webhook_models import IntentAnalysisResponse

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    def __init__(self):
        self.llm = self._initialize_llm()
        self.parser = PydanticOutputParser(pydantic_object=IntentAnalysisResponse)
        
    def _initialize_llm(self):
        """Initialize the LLM based on provider configuration"""
        if settings.LLM_PROVIDER.lower() == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
            return ChatOpenAI(
                model=settings.LLM_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=0.1
            )
        elif settings.LLM_PROVIDER.lower() == "google":
            if not settings.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY is required when using Google provider")
            return ChatGoogleGenerativeAI(
                model=settings.LLM_MODEL,
                temperature=0.1
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Create the prompt template with few-shot examples"""
        
        # Format few-shot examples
        examples_text = "\n".join([
            f"Comment: '{example['comment']}'\nIntent: {example['intent']}\nDM Message: '{example['dm_message']}'\n"
            for example in settings.DM_EXAMPLES
        ])
        
        prompt_template = ChatPromptTemplate.from_template("""
You are an AI assistant that analyzes Facebook page comments to determine user intent and generate appropriate DM responses.

Your task:
1. Analyze the comment to determine if the user is interested in services
2. Generate a personalized DM message based on the comment

Few-shot examples:
{examples}

Comment to analyze: "{comment}"
User name: {user_name}

{format_instructions}

Please analyze this comment and provide:
1. Intent (choose one):
   - "positive" - shows appreciation, satisfaction, or praise
   - "negative" - shows dissatisfaction, complaints, or criticism
   - "interested_in_services" - shows interest in services, asking questions, needs help
   - "other" - neutral, informational, or not categorized
2. A personalized DM message (leave empty for "negative" or "other" intents)
3. Confidence score (0.0 to 1.0)

Guidelines:
- For "interested_in_services": user is asking about services, pricing, help, or support
- For "positive": user expresses satisfaction, appreciation, or praise
- For "negative": user shows dissatisfaction, complaints, or criticism
- For "other": neutral comments, general discussion, or information sharing
- Generate DM message ONLY for "positive" or "interested_in_services" intents
- Leave DM message empty for "negative" or "other" intents
- Keep messages professional, friendly, and concise
- Use appropriate emojis sparingly
""")
        
        return prompt_template
    
    async def analyze_intent(self, comment_message: str, user_name: str) -> IntentAnalysisResponse:
        """
        Analyze comment intent and generate DM message
        
        Args:
            comment_message: The comment text to analyze
            user_name: Name of the user who commented
            
        Returns:
            IntentAnalysisResponse with intent and DM message
        """
        try:
            prompt_template = self._create_prompt_template()
            
            # Format the prompt
            formatted_prompt = prompt_template.format_messages(
                examples="\n".join([
                    f"Comment: '{example['comment']}'\nIntent: {example['intent']}\nDM Message: '{example['dm_message']}'\n"
                    for example in settings.DM_EXAMPLES
                ]),
                comment=comment_message,
                user_name=user_name,
                format_instructions=self.parser.get_format_instructions()
            )
            
            # Get response from LLM
            response = await self.llm.ainvoke(formatted_prompt)
            
            # Parse the response
            parsed_response = self.parser.parse(response.content)
            
            logger.info(f"Intent analysis completed for comment: '{comment_message[:50]}...' - Intent: {parsed_response.intent}")
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"Error analyzing intent for comment '{comment_message}': {str(e)}")
            # Return default response in case of error
            return IntentAnalysisResponse(
                intent="other",
                dm_message=f"Hi {user_name}! 👋 Thanks for your comment! Feel free to reach out if you need any assistance.",
                confidence=0.0
            )
    
    def analyze_intent_sync(self, comment_message: str, user_name: str) -> IntentAnalysisResponse:
        """
        Synchronous version of analyze_intent for compatibility
        """
        try:
            prompt_template = self._create_prompt_template()
            
            # Format the prompt
            formatted_prompt = prompt_template.format_messages(
                examples="\n".join([
                    f"Comment: '{example['comment']}'\nIntent: {example['intent']}\nDM Message: '{example['dm_message']}'\n"
                    for example in settings.DM_EXAMPLES
                ]),
                comment=comment_message,
                user_name=user_name,
                format_instructions=self.parser.get_format_instructions()
            )
            
            # Get response from LLM
            response = self.llm.invoke(formatted_prompt)
            
            # Parse the response
            parsed_response = self.parser.parse(response.content)
            
            logger.info(f"Intent analysis completed for comment: '{comment_message[:50]}...' - Intent: {parsed_response.intent}")
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"Error analyzing intent for comment '{comment_message}': {str(e)}")
            # Return default response in case of error
            return IntentAnalysisResponse(
                intent="other",
                dm_message=f"Hi {user_name}! 👋 Thanks for your comment! Feel free to reach out if you need any assistance.",
                confidence=0.0
            )


if __name__ == "__main__":
    analyzer = IntentAnalyzer()
    response = analyzer.analyze_intent_sync("I need help with my assignment", "John Doe")
    print(response)
    print(response.intent)
    print(response.dm_message)
    print(response.confidence)