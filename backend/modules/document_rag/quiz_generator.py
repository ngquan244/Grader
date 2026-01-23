"""
Quiz Generator Module
=====================
Generate quiz questions from documents using RAG + Ollama LLM.
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from .config import rag_config
from .retriever import DocumentRetriever

logger = logging.getLogger(__name__)


# ===== Quiz Data Models =====

class QuizQuestion(BaseModel):
    """Model for a single quiz question"""
    question: str = Field(description="Nội dung câu hỏi")
    options: List[str] = Field(description="Danh sách 4 đáp án A, B, C, D")
    correct_answer: str = Field(description="Đáp án đúng (A, B, C hoặc D)")
    explanation: str = Field(description="Giải thích ngắn gọn tại sao đáp án đúng")


class QuizOutput(BaseModel):
    """Model for quiz generation output"""
    quiz: List[QuizQuestion] = Field(default=[], description="Danh sách câu hỏi")
    message: str = Field(default="", description="Thông báo nếu có lỗi")


# ===== Prompt Template =====

QUIZ_GENERATION_PROMPT = """Bạn là một giáo viên chuyên nghiệp trong việc soạn đề thi trắc nghiệm chất lượng cao.

NHIỆM VỤ: Tạo {num_questions} câu hỏi trắc nghiệm dựa trên nội dung tài liệu được cung cấp.

NỘI DUNG TÀI LIỆU (CONTEXT):
{context}

CHỦ ĐỀ/YÊU CẦU: {topic}

ĐỘ KHÓ: {difficulty} (easy/medium/hard)

QUY TẮC BẮT BUỘC:
1. CHỈ sử dụng thông tin có trong Context để tạo câu hỏi
2. KHÔNG bịa đặt hoặc thêm kiến thức ngoài tài liệu
3. Mỗi câu hỏi PHẢI có đúng 4 đáp án: A, B, C, D
4. Các đáp án sai phải hợp lý, không quá dễ loại trừ
5. Câu hỏi phải rõ ràng, không mơ hồ
6. Tuân thủ độ khó yêu cầu:
   - easy: Câu hỏi đơn giản, kiểm tra ghi nhớ cơ bản
   - medium: Câu hỏi yêu cầu hiểu và áp dụng kiến thức
   - hard: Câu hỏi phân tích, so sánh, tổng hợp thông tin
7. Tránh câu hỏi trùng lặp ý nghĩa

HƯỚNG DẪN TẠO CÂU HỎI CHẤT LƯỢNG:
- Câu hỏi kiểm tra hiểu biết, không chỉ ghi nhớ
- Đáp án đúng phải chính xác theo tài liệu
- Giải thích ngắn gọn, trích dẫn từ context nếu có thể
- Nếu context không đủ để tạo {num_questions} câu, tạo tối đa số câu có thể

XỬ LÝ TRƯỜNG HỢP ĐẶC BIỆT:
- Nếu Context KHÔNG chứa thông tin về "{topic}": trả về quiz rỗng với message giải thích
- Nếu Context không đủ thông tin: tạo ít câu hơn, KHÔNG bịa

ĐỊNH DẠNG OUTPUT (JSON):
{{
  "quiz": [
    {{
      "question": "Nội dung câu hỏi?",
      "options": ["Đáp án A", "Đáp án B", "Đáp án C", "Đáp án D"],
      "correct_answer": "A",
      "explanation": "Giải thích ngắn gọn"
    }}
  ],
  "message": ""
}}

CHÚ Ý: Chỉ trả về JSON, không thêm text khác. Đảm bảo JSON hợp lệ."""


QUIZ_GENERATION_PROMPT_V2 = """You are an expert quiz creator. Create {num_questions} multiple-choice questions based ONLY on the provided document content.

DOCUMENT CONTENT:
{context}

TOPIC/REQUIREMENT: {topic}

DIFFICULTY LEVEL: {difficulty} (easy/medium/hard)

STRICT RULES:
1. Questions MUST be based ONLY on the provided content - DO NOT make up information
2. Each question has exactly 4 options: A, B, C, D
3. Wrong answers should be plausible but clearly incorrect based on the document
4. Follow the difficulty level:
   - easy: Simple recall questions testing basic facts
   - medium: Questions requiring understanding and application
   - hard: Complex questions requiring analysis and synthesis
5. Questions should test understanding, not just memorization
6. If content is insufficient, create fewer questions rather than inventing facts

OUTPUT FORMAT (JSON only, no markdown):
{{
  "quiz": [
    {{
      "question": "Question text here?",
      "options": ["Option A text", "Option B text", "Option C text", "Option D text"],
      "correct_answer": "A",
      "explanation": "Brief explanation why this is correct"
    }}
  ],
  "message": ""
}}

If the topic is not found in the document, return:
{{"quiz": [], "message": "Không tìm thấy nội dung về '{topic}' trong tài liệu"}}

Return ONLY valid JSON, no additional text."""


class QuizGenerator:
    """
    Generate quiz questions from documents using RAG.
    """
    
    def __init__(
        self,
        retriever: DocumentRetriever,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        base_url: Optional[str] = None
    ):
        """
        Initialize Quiz Generator.
        
        Args:
            retriever: DocumentRetriever instance
            model: Ollama model name
            temperature: Generation temperature (lower = more focused)
            base_url: Ollama API base URL
        """
        self.retriever = retriever
        self.model = model or rag_config.OLLAMA_MODEL
        self.temperature = temperature if temperature is not None else 0.3
        self.base_url = base_url or rag_config.OLLAMA_BASE_URL
        
        # Initialize LLM with lower temperature for more consistent output
        self.llm = ChatOllama(
            model=self.model,
            temperature=self.temperature,
            base_url=self.base_url,
            num_ctx=rag_config.OLLAMA_NUM_CTX,
            format="json",  # Request JSON output
        )
        
        # Prompt templates
        self.prompt_vi = ChatPromptTemplate.from_template(QUIZ_GENERATION_PROMPT)
        self.prompt_en = ChatPromptTemplate.from_template(QUIZ_GENERATION_PROMPT_V2)
        
        logger.info(f"QuizGenerator initialized with model: {self.model}")
    
    def generate_quiz(
        self,
        topic: str,
        num_questions: int = 5,
        difficulty: str = "medium",
        language: str = "vi",
        k: int = 10
    ) -> Dict[str, Any]:
        """
        Generate quiz questions based on a topic.
        
        Args:
            topic: Topic or description of what to quiz about
            num_questions: Number of questions to generate
            difficulty: Difficulty level - "easy", "medium", or "hard"
            language: "vi" for Vietnamese prompt, "en" for English
            k: Number of documents to retrieve for context
            
        Returns:
            Dictionary with quiz questions and metadata
        """
        logger.info(f"Generating quiz: topic='{topic}', num_questions={num_questions}, difficulty={difficulty}")
        
        # Step 1: Retrieve relevant documents
        documents = self.retriever.retrieve(topic, k=k)
        
        if not documents:
            logger.warning("No documents retrieved for topic")
            return {
                "success": False,
                "questions": [],
                "message": f"Không tìm thấy nội dung về '{topic}' trong tài liệu",
                "sources": []
            }
        
        # Step 2: Format context
        context = self.retriever.format_context(documents)
        
        if not context.strip():
            return {
                "success": False,
                "questions": [],
                "message": "Context rỗng, không thể tạo quiz",
                "sources": []
            }
        
        # Step 3: Select prompt based on language
        prompt = self.prompt_vi if language == "vi" else self.prompt_en
        
        # Step 4: Generate quiz
        chain = prompt | self.llm
        
        try:
            logger.info("Generating quiz with LLM...")
            
            response = chain.invoke({
                "context": context,
                "topic": topic,
                "num_questions": num_questions,
                "difficulty": difficulty
            })
            
            # Parse response
            content = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"Raw LLM response: {content[:500]}...")
            
            # Parse JSON
            quiz_data = self._parse_quiz_response(content)
            
            if not quiz_data:
                logger.error(f"Failed to parse quiz data from response")
                return {
                    "success": False,
                    "questions": [],
                    "message": "Không thể parse kết quả từ LLM",
                    "sources": self.retriever.extract_citations(documents),
                    "raw_response": content
                }
            
            logger.info(f"Parsed quiz_data keys: {quiz_data.keys()}")
            logger.info(f"Number of quiz items: {len(quiz_data.get('quiz', []))}")
            
            # Check for error message from LLM
            if quiz_data.get("message") and not quiz_data.get("quiz"):
                return {
                    "success": False,
                    "questions": [],
                    "message": quiz_data["message"],
                    "sources": self.retriever.extract_citations(documents)
                }
            
            # Format quiz questions
            formatted_quiz = self._format_quiz(quiz_data.get("quiz", []))
            
            logger.info(f"Generated {len(formatted_quiz)} questions")
            
            if len(formatted_quiz) > 0:
                logger.info(f"Sample question 1: {formatted_quiz[0]}")
            
            return {
                "success": True,
                "questions": formatted_quiz,
                "message": quiz_data.get("message", ""),
                "sources": self.retriever.extract_citations(documents),
                "num_questions_requested": num_questions,
                "num_questions_generated": len(formatted_quiz)
            }
            
        except Exception as e:
            logger.error(f"Error generating quiz: {e}")
            return {
                "success": False,
                "questions": [],
                "message": f"Lỗi khi tạo quiz: {str(e)}",
                "sources": self.retriever.extract_citations(documents),
                "error": str(e)
            }
    
    def _parse_quiz_response(self, content: str) -> Optional[Dict]:
        """Parse JSON response from LLM."""
        try:
            # Try direct JSON parse
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code block
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in content
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        logger.error(f"Could not parse JSON from response: {content[:200]}")
        return None
    
    def _format_quiz(self, quiz_list: List[Dict]) -> List[Dict]:
        """Format and validate quiz questions."""
        formatted = []
        
        for i, q in enumerate(quiz_list):
            try:
                # Validate required fields
                if not q.get("question"):
                    logger.warning(f"Question {i} missing 'question' field")
                    continue
                
                if not q.get("options"):
                    logger.warning(f"Question {i} missing 'options' field")
                    continue
                
                options = q.get("options", [])
                
                # Handle if options is already a dict
                if isinstance(options, dict):
                    # Already in {A: ..., B: ..., C: ..., D: ...} format
                    options_dict = options
                else:
                    # Convert list to dict
                    if not isinstance(options, list):
                        logger.warning(f"Question {i}: options is not list or dict: {type(options)}")
                        continue
                    
                    if len(options) != 4:
                        logger.warning(f"Question {i}: options has {len(options)} items, expected 4")
                        # Pad or trim to 4 options
                        while len(options) < 4:
                            options.append(f"Đáp án {chr(65 + len(options))}")
                        options = options[:4]
                    
                    options_dict = {
                        "A": options[0],
                        "B": options[1],
                        "C": options[2],
                        "D": options[3]
                    }
                
                # Get correct answer
                correct = q.get("correct_answer", "A").upper()
                if correct not in ["A", "B", "C", "D"]:
                    logger.warning(f"Question {i}: invalid correct_answer '{correct}', defaulting to 'A'")
                    correct = "A"
                
                formatted.append({
                    "question_number": i + 1,
                    "question": q["question"],
                    "options": options_dict,
                    "correct_answer": correct,
                    "explanation": q.get("explanation", "")
                })
                
                logger.debug(f"Formatted question {i+1}: {q['question'][:50]}...")
                
            except Exception as e:
                logger.warning(f"Error formatting question {i}: {e}")
                continue
        
        return formatted
    
    def generate_quiz_text(
        self,
        topic: str,
        num_questions: int = 5,
        k: int = 10
    ) -> str:
        """
        Generate quiz and return as formatted text.
        
        Args:
            topic: Topic to quiz about
            num_questions: Number of questions
            k: Documents to retrieve
            
        Returns:
            Formatted quiz text
        """
        result = self.generate_quiz(topic, num_questions, k)
        
        if not result["success"] or not result["quiz"]:
            return result.get("message", "Không thể tạo quiz")
        
        lines = [f"📝 QUIZ: {topic.upper()}", "=" * 50, ""]
        
        for q in result["quiz"]:
            lines.append(f"Câu {q['id']}: {q['question']}")
            for letter, option in q["options"].items():
                lines.append(f"   {letter}. {option}")
            lines.append(f"   ✅ Đáp án: {q['correct_answer']}")
            if q.get("explanation"):
                lines.append(f"   💡 Giải thích: {q['explanation']}")
            lines.append("")
        
        lines.append("=" * 50)
        lines.append(f"Tổng: {len(result['quiz'])} câu hỏi")
        
        return "\n".join(lines)
