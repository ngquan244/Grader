"""
Quiz Generator Module
=====================
Generate quiz questions from documents using RAG + configurable LLM backends.
Supports Ollama (local) and Groq Cloud (API) with strict JSON output.
"""

import logging
import json
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from .config import rag_config
from .retriever import DocumentRetriever
from .llm_providers import BaseLLM, LLMFactory

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
    Supports multiple LLM providers with strict JSON output.
    """
    
    def __init__(
        self,
        retriever: DocumentRetriever,
        llm_provider: Optional[BaseLLM] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        base_url: Optional[str] = None
    ):
        """
        Initialize Quiz Generator.
        
        Args:
            retriever: DocumentRetriever instance
            llm_provider: Pre-configured LLM provider (if None, uses LLMFactory)
            model: Model name override (legacy, for backwards compatibility)
            temperature: Generation temperature (lower = more focused)
            base_url: API base URL (legacy)
        """
        self.retriever = retriever
        
        # Store legacy params for backwards compatibility
        self._model_override = model
        self._temperature_override = temperature if temperature is not None else 0.3
        self._base_url_override = base_url
        
        # Initialize LLM provider
        self._llm_provider: Optional[BaseLLM] = llm_provider
        
        # LLM instances (lazy initialized)
        self._llm = None  # Regular LLM
        self._llm_json = None  # JSON-mode LLM for quiz generation
        
        # Prompt templates
        self.prompt_vi = ChatPromptTemplate.from_template(QUIZ_GENERATION_PROMPT)
        self.prompt_en = ChatPromptTemplate.from_template(QUIZ_GENERATION_PROMPT_V2)
        
        # Initialize if provider not passed
        if self._llm_provider is None:
            self._init_llm()
        
        logger.info(f"QuizGenerator initialized with provider: {self._llm_provider.provider_name}")
    
    def _init_llm(self):
        """Initialize LLM using factory."""
        kwargs = {"temperature": self._temperature_override}
        if self._base_url_override:
            kwargs["base_url"] = self._base_url_override
        
        self._llm_provider = LLMFactory.create(
            model=self._model_override,
            **kwargs
        )
    
    @property
    def llm(self):
        """Get regular LLM instance (lazy initialization)."""
        if self._llm is None:
            self._llm = self._llm_provider.get_llm(json_mode=False)
        return self._llm
    
    @property
    def llm_json(self):
        """Get JSON-mode LLM instance for quiz generation (lazy initialization)."""
        if self._llm_json is None:
            self._llm_json = self._llm_provider.get_llm(json_mode=True)
        return self._llm_json
    
    @property
    def model(self) -> str:
        """Get current model name."""
        return self._llm_provider.model if self._llm_provider else self._model_override or rag_config.OLLAMA_MODEL
    
    def set_llm_provider(self, provider: BaseLLM):
        """
        Set a new LLM provider at runtime.
        
        Args:
            provider: New LLM provider instance
        """
        self._llm_provider = provider
        self._llm = None  # Reset cached instances
        self._llm_json = None
        logger.info(f"QuizGenerator LLM provider updated: {provider.provider_name}")
    
    def extract_topics_from_context(
        self,
        context: str,
        max_topics: int = 10
    ) -> Dict[str, Any]:
        """
        Extract topics from provided context using LLM.
        Used during document indexing to extract and cache topics.
        
        Args:
            context: Document content to analyze
            max_topics: Maximum number of topics to extract
            
        Returns:
            Dictionary with topics
        """
        logger.info("Extracting topics from provided context...")
        
        try:
            topic_prompt = ChatPromptTemplate.from_template("""Analyze the following document content and extract the main topics/concepts that could be used for quiz generation.

DOCUMENT CONTENT:
{context}

Extract {max_topics} main topics from this content. Topics should be:
- Specific enough to generate focused questions
- Clear and concise (1-5 words each)
- Represent key concepts, chapters, or sections in the document
- In the same language as the document content

OUTPUT FORMAT (JSON only):
{{
  "topics": [
    {{"name": "Topic Name", "description": "Brief description of what this topic covers"}}
  ]
}}

Return ONLY valid JSON, no additional text.""")
            
            # Use JSON-mode LLM for reliable JSON output
            chain = topic_prompt | self.llm_json
            
            response = chain.invoke({
                "context": context,
                "max_topics": max_topics
            })
            
            content = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"Topic extraction response: {content[:300]}...")
            
            data = self._parse_quiz_response(content)
            
            if data and data.get("topics"):
                return {
                    "success": True,
                    "topics": data["topics"]
                }
            
            return {
                "success": False,
                "topics": [],
                "message": "Could not extract topics"
            }
            
        except Exception as e:
            logger.error(f"Error extracting topics from context: {e}")
            return {
                "success": False,
                "topics": [],
                "message": str(e)
            }
    
    def extract_topics(self, max_topics: int = 10) -> Dict[str, Any]:
        """
        Extract suggested topics from indexed documents using LLM.
        
        Args:
            max_topics: Maximum number of topics to suggest
            
        Returns:
            Dictionary with topics and metadata
        """
        logger.info("Extracting topics from documents...")
        
        try:
            # Get sample documents for topic extraction
            documents = self.retriever.vector_store.get_all_document_content(max_docs=20)
            
            if not documents:
                return {
                    "success": False,
                    "topics": [],
                    "message": "Chưa có tài liệu nào được index"
                }
            
            # Create context from documents
            context = "\n\n---\n\n".join(documents[:15])  # Limit to avoid token overflow
            
            # Prompt for topic extraction - use JSON mode LLM
            topic_prompt = ChatPromptTemplate.from_template("""Analyze the following document content and extract the main topics/concepts that could be used for quiz generation.

DOCUMENT CONTENT:
{context}

Extract {max_topics} main topics from this content. Topics should be:
- Specific enough to generate focused questions
- Clear and concise (1-5 words each)
- Represent key concepts, chapters, or sections in the document

OUTPUT FORMAT (JSON only):
{{
  "topics": [
    {{"name": "Topic Name", "description": "Brief description of what this topic covers"}}
  ]
}}

Return ONLY valid JSON, no additional text.""")
            
            chain = topic_prompt | self.llm_json
            
            response = chain.invoke({
                "context": context[:8000],  # Limit context size
                "max_topics": max_topics
            })
            
            content = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"Topic extraction response: {content[:300]}...")
            
            # Parse response
            data = self._parse_quiz_response(content)
            
            if data and data.get("topics"):
                topics = data["topics"]
                logger.info(f"Extracted {len(topics)} topics")
                return {
                    "success": True,
                    "topics": topics,
                    "message": ""
                }
            
            return {
                "success": False,
                "topics": [],
                "message": "Không thể trích xuất chủ đề từ tài liệu"
            }
            
        except Exception as e:
            logger.error(f"Error extracting topics: {e}")
            return {
                "success": False,
                "topics": [],
                "message": f"Lỗi: {str(e)}"
            }

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
        
        # Step 4: Generate quiz using JSON-mode LLM
        chain = prompt | self.llm_json
        
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
    
    def export_to_qti(
        self,
        questions: List[Dict[str, Any]],
        title: str = "Generated Quiz",
        description: str = ""
    ) -> str:
        """
        Export quiz questions to QTI 2.1 XML format.
        
        Args:
            questions: List of formatted quiz questions
            title: Quiz title
            description: Quiz description
            
        Returns:
            QTI XML string
        """
        # Create root element
        root = ET.Element('questestinterop')
        root.set('xmlns', 'http://www.imsglobal.org/xsd/ims_qtiasiv1p2')
        root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        root.set('xsi:schemaLocation', 'http://www.imsglobal.org/xsd/ims_qtiasiv1p2 http://www.imsglobal.org/xsd/ims_qtiasiv1p2p1.xsd')
        
        # Assessment
        assessment = ET.SubElement(root, 'assessment')
        assessment.set('ident', f'quiz_{datetime.now().strftime("%Y%m%d%H%M%S")}')
        assessment.set('title', title)
        
        # Metadata
        qtimetadata = ET.SubElement(assessment, 'qtimetadata')
        qtimetadatafield = ET.SubElement(qtimetadata, 'qtimetadatafield')
        ET.SubElement(qtimetadatafield, 'fieldlabel').text = 'qmd_timelimit'
        ET.SubElement(qtimetadatafield, 'fieldentry').text = '0'
        
        # Section
        section = ET.SubElement(assessment, 'section')
        section.set('ident', 'root_section')
        section.set('title', title)
        
        if description:
            ET.SubElement(section, 'rubric').text = description
        
        # Add questions
        for q in questions:
            item = ET.SubElement(section, 'item')
            item.set('ident', f'question_{q["question_number"]}')
            item.set('title', f'Question {q["question_number"]}')
            
            # Item metadata
            itemmetadata = ET.SubElement(item, 'itemmetadata')
            qtimetadata_item = ET.SubElement(itemmetadata, 'qtimetadata')
            
            # Question type
            field1 = ET.SubElement(qtimetadata_item, 'qtimetadatafield')
            ET.SubElement(field1, 'fieldlabel').text = 'question_type'
            ET.SubElement(field1, 'fieldentry').text = 'multiple_choice_question'
            
            # Points
            field2 = ET.SubElement(qtimetadata_item, 'qtimetadatafield')
            ET.SubElement(field2, 'fieldlabel').text = 'points_possible'
            ET.SubElement(field2, 'fieldentry').text = '1.0'
            
            # Presentation
            presentation = ET.SubElement(item, 'presentation')
            material = ET.SubElement(presentation, 'material')
            mattext = ET.SubElement(material, 'mattext')
            mattext.set('texttype', 'text/html')
            mattext.text = q["question"]
            
            # Response
            response = ET.SubElement(presentation, 'response_lid')
            response.set('ident', 'response1')
            response.set('rcardinality', 'Single')
            
            render_choice = ET.SubElement(response, 'render_choice')
            
            # Options
            for key, value in q["options"].items():
                response_label = ET.SubElement(render_choice, 'response_label')
                response_label.set('ident', key)
                mat = ET.SubElement(response_label, 'material')
                mat_text = ET.SubElement(mat, 'mattext')
                mat_text.set('texttype', 'text/plain')
                mat_text.text = value
            
            # Correct answer
            resprocessing = ET.SubElement(item, 'resprocessing')
            outcomes = ET.SubElement(resprocessing, 'outcomes')
            decvar = ET.SubElement(outcomes, 'decvar')
            decvar.set('maxvalue', '100')
            decvar.set('minvalue', '0')
            decvar.set('varname', 'SCORE')
            decvar.set('vartype', 'Decimal')
            
            # Correct response condition
            respcondition = ET.SubElement(resprocessing, 'respcondition')
            respcondition.set('continue', 'No')
            conditionvar = ET.SubElement(respcondition, 'conditionvar')
            varequal = ET.SubElement(conditionvar, 'varequal')
            varequal.set('respident', 'response1')
            varequal.text = q["correct_answer"]
            
            setvar = ET.SubElement(respcondition, 'setvar')
            setvar.set('action', 'Set')
            setvar.set('varname', 'SCORE')
            setvar.text = '100'
            
            # Feedback if explanation exists
            if q.get("explanation"):
                itemfeedback = ET.SubElement(item, 'itemfeedback')
                itemfeedback.set('ident', 'correct_fb')
                flow_mat = ET.SubElement(itemfeedback, 'flow_mat')
                material_fb = ET.SubElement(flow_mat, 'material')
                mattext_fb = ET.SubElement(material_fb, 'mattext')
                mattext_fb.set('texttype', 'text/html')
                mattext_fb.text = q["explanation"]
        
        # Convert to string with pretty print
        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent='  ')
        
        return "\n".join(lines)
