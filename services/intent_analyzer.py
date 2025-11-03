import logging

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from core.config import settings
from core.prompts import get_comment_dm_prompt, get_messaging_prompt, get_lisa_persona
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
        prompt_template = ChatPromptTemplate.from_template(get_comment_dm_prompt())
        return prompt_template

    def _create_messaging_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_template(get_messaging_prompt())
    
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
            
            # Format the prompt with first name for greeting
            first_name = (user_name.split(" ")[0] if user_name else "")
            formatted_prompt = prompt_template.format_messages(
                examples="\n".join([
                    f"Comment: '{example['comment']}'\nIntent: {example['intent']}\nDM Message: '{example['dm_message']}'\n"
                    for example in settings.DM_EXAMPLES
                ]),
                comment=comment_message,
                user_name=user_name,
                first_name=first_name,
                format_instructions=self.parser.get_format_instructions(),
                company_bio=settings.COMPANY_BIO,
                lisa_persona=get_lisa_persona()
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

    def generate_messaging_reply_sync(self, latest_user_text: str, user_name: str, context_messages: list[dict]) -> str:
        """Generate a Messenger reply using Lisa's persona and chat context."""
        try:
            prompt_template = self._create_messaging_prompt()
            lines = []
            for m in context_messages[:25]:
                role = m.get("role", "user")
                text = m.get("text") or ""
                lines.append(f"{role}: {text}")
            context_block = "\n".join(lines)

            first_name = (user_name.split(" ")[0] if user_name else "")
            has_agent_reply = any((m.get("role") or "").lower() == "agent" for m in context_messages)
            should_greet = "yes" if not has_agent_reply else "no"
            formatted = prompt_template.format_messages(
                latest_user_text=latest_user_text,
                first_name=first_name,
                context_messages=context_block,
                company_bio=settings.COMPANY_BIO,
                lisa_persona=get_lisa_persona(),
                should_greet=should_greet,
            )
            resp = self.llm.invoke(formatted)
            return resp.content.strip()
        except Exception as e:
            logger.error(f"Error generating messaging reply: {str(e)}")
            first_name = (user_name.split(" ")[0] if user_name else "there")
            has_agent_reply = any((m.get("role") or "").lower() == "agent" for m in context_messages)
            if has_agent_reply:
                return "Could you share the best phone number so our specialist can text you a quick plan?"
            return f"Hey {first_name}, could you share the best phone number so our specialist can text you a quick plan?"
    
    def analyze_intent_sync(self, comment_message: str, user_name: str) -> IntentAnalysisResponse:
        """
        Synchronous version of analyze_intent for compatibility
        """
        try:
            prompt_template = self._create_prompt_template()
            
            # Format the prompt with first name for greeting
            first_name = (user_name.split(" ")[0] if user_name else "")
            formatted_prompt = prompt_template.format_messages(
                examples="\n".join([
                    f"Comment: '{example['comment']}'\nIntent: {example['intent']}\nDM Message: '{example['dm_message']}'\n"
                    for example in settings.DM_EXAMPLES
                ]),
                comment=comment_message,
                user_name=user_name,
                first_name=first_name,
                format_instructions=self.parser.get_format_instructions(),
                company_bio=settings.COMPANY_BIO
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
