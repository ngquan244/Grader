import React, { useState, useEffect, useRef } from 'react';
import {
  FileText,
  Upload,
  Search,
  Database,
  Trash2,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  FileIcon,
  Server,
  Info,
  BookOpen,
  HelpCircle,
  Check,
  X,
  Edit2,
  Download,
  Save,
  Cloud,
  Cpu,
  Zap,
} from 'lucide-react';
import {
  uploadAndIndexDocument,
  queryRAG,
  getRAGStats,
  resetRAGIndex,
  checkOllamaStatus,
  listUploadedFiles,
  generateQuiz,
  exportQuizToQTI,
  getDocumentTopics,
  listIndexedDocuments,
  getLLMProviderInfo,
  setLLMProvider,
  checkLLMStatus,
  type RAGSource,
  type RAGIndexStats,
  type RAGUploadedFile,
  type OllamaStatus,
  type QuizQuestion,
  type TopicSuggestion,
  type LLMProviderInfo,
} from '../api/documentRag';

// Indexed document info
interface IndexedDocument {
  filename: string;
  original_filename: string;
  topic_count: number;
  indexed_at: string;
}

interface QueryResult {
  answer: string;
  sources: RAGSource[];
  context?: string;
}

// Tab type
type ActiveTab = 'query' | 'quiz';

const DocumentRAGPanel: React.FC = () => {
  // State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [question, setQuestion] = useState('');
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [showContext, setShowContext] = useState(false);
  const [showSources, setShowSources] = useState(true);
  
  // Tab state
  const [activeTab, setActiveTab] = useState<ActiveTab>('quiz');
  
  // Quiz states
  const [quizTopic, setQuizTopic] = useState('');
  const [numQuestions, setNumQuestions] = useState(5);
  const [quizDifficulty, setQuizDifficulty] = useState<'easy' | 'medium' | 'hard'>('medium');
  const [quizLanguage, setQuizLanguage] = useState<'vi' | 'en'>('vi');
  const [generatedQuiz, setGeneratedQuiz] = useState<QuizQuestion[]>([]);
  const [isGeneratingQuiz, setIsGeneratingQuiz] = useState(false);
  const [quizError, setQuizError] = useState<string | null>(null);
  const [editingQuestionIndex, setEditingQuestionIndex] = useState<number | null>(null);
  const [editingQuestion, setEditingQuestion] = useState<QuizQuestion | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  
  // Topic suggestions states - PER DOCUMENT
  const [indexedDocuments, setIndexedDocuments] = useState<IndexedDocument[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<string>('');
  const [suggestedTopics, setSuggestedTopics] = useState<TopicSuggestion[]>([]);
  const [isLoadingTopics, setIsLoadingTopics] = useState(false);
  const [showTopicSuggestions, setShowTopicSuggestions] = useState(false);
  const [topicsCache, setTopicsCache] = useState<Record<string, TopicSuggestion[]>>({});
  
  // Loading states
  const [isUploading, setIsUploading] = useState(false);
  const [isQuerying, setIsQuerying] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  
  // Status states
  const [indexStats, setIndexStats] = useState<RAGIndexStats | null>(null);
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<RAGUploadedFile[]>([]);
  
  // Messages
  const [uploadMessage, setUploadMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  
  // LLM Provider states
  const [llmProviderInfo, setLlmProviderInfo] = useState<LLMProviderInfo | null>(null);
  const [isSwitchingProvider, setIsSwitchingProvider] = useState(false);
  const [providerMessage, setProviderMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load initial data
  useEffect(() => {
    loadIndexStats();
    loadOllamaStatus();
    loadUploadedFiles();
    loadIndexedDocuments();
    loadLLMProviderInfo();
  }, []);

  // Load LLM Provider info
  const loadLLMProviderInfo = async () => {
    try {
      const info = await getLLMProviderInfo();
      setLlmProviderInfo(info);
    } catch (error) {
      console.error('Error loading LLM provider info:', error);
    }
  };

  // Handle LLM provider switch
  const handleSwitchProvider = async (provider: 'ollama' | 'groq') => {
    if (isSwitchingProvider) return;
    
    setIsSwitchingProvider(true);
    setProviderMessage(null);
    
    try {
      const response = await setLLMProvider({ provider });
      
      if (response.success) {
        setProviderMessage({
          type: 'success',
          text: `Đã chuyển sang ${provider === 'groq' ? 'Groq Cloud' : 'Ollama'} thành công!`
        });
        // Reload provider info and status
        await loadLLMProviderInfo();
        await loadOllamaStatus();
      } else {
        setProviderMessage({
          type: 'error',
          text: response.error || `Không thể chuyển sang ${provider}`
        });
      }
    } catch (error) {
      console.error('Error switching provider:', error);
      setProviderMessage({
        type: 'error',
        text: `Lỗi khi chuyển provider: ${error}`
      });
    } finally {
      setIsSwitchingProvider(false);
      // Clear message after 5 seconds
      setTimeout(() => setProviderMessage(null), 5000);
    }
  };

  // Load indexed documents with topics
  const loadIndexedDocuments = async () => {
    try {
      const response = await listIndexedDocuments();
      if (response.success && response.documents) {
        setIndexedDocuments(response.documents);
        // Auto-select first document if none selected
        if (response.documents.length > 0 && !selectedDocument) {
          setSelectedDocument(response.documents[0].filename);
        }
      }
    } catch (error) {
      console.error('Error loading indexed documents:', error);
    }
  };

  const loadIndexStats = async () => {
    try {
      const response = await getRAGStats();
      if (response.success) {
        setIndexStats(response.stats);
      }
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const loadOllamaStatus = async () => {
    try {
      const status = await checkOllamaStatus();
      setOllamaStatus(status);
    } catch (error) {
      console.error('Error checking Ollama:', error);
      setOllamaStatus({
        connected: false,
        message: 'Không thể kết nối đến Ollama',
        error: String(error),
      });
    }
  };

  const loadUploadedFiles = async () => {
    try {
      const response = await listUploadedFiles();
      if (response.success) {
        setUploadedFiles(response.files);
      }
    } catch (error) {
      console.error('Error loading files:', error);
    }
  };

  // Load suggested topics for selected document (from cache, instant!)
  const loadSuggestedTopics = async () => {
    if (!selectedDocument) {
      return;
    }
    
    // Check cache first - instant!
    if (topicsCache[selectedDocument]) {
      setSuggestedTopics(topicsCache[selectedDocument]);
      setShowTopicSuggestions(true);
      return;
    }
    
    // Load from API (topics are pre-extracted during indexing, so this is fast)
    setIsLoadingTopics(true);
    try {
      const response = await getDocumentTopics(selectedDocument);
      if (response.success && response.topics) {
        const topics: TopicSuggestion[] = response.topics.map((name, idx) => ({
          name,
          relevance_score: 1 - (idx * 0.05), // Fake score based on order
          description: `Chủ đề từ ${response.filename}`
        }));
        
        // Cache it
        setTopicsCache(prev => ({ ...prev, [selectedDocument]: topics }));
        setSuggestedTopics(topics);
        setShowTopicSuggestions(true);
      }
    } catch (error) {
      console.error('Error getting topics:', error);
    } finally {
      setIsLoadingTopics(false);
    }
  };

  // Select a suggested topic
  const handleSelectTopic = (topic: TopicSuggestion) => {
    setQuizTopic(topic.name);
    setShowTopicSuggestions(false);
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setUploadMessage({ type: 'error', text: 'Chỉ hỗ trợ file PDF' });
        return;
      }
      setSelectedFile(file);
      setUploadMessage(null);
    }
  };

  const handleUploadAndIndex = async () => {
    if (!selectedFile) {
      setUploadMessage({ type: 'error', text: 'Vui lòng chọn file PDF' });
      return;
    }

    setIsUploading(true);
    setUploadMessage(null);

    try {
      const response = await uploadAndIndexDocument(selectedFile);
      
      if (response.success) {
        if (response.already_indexed) {
          setUploadMessage({ type: 'info', text: `Tài liệu đã được index trước đó: ${response.filename}` });
        } else {
          setUploadMessage({
            type: 'success',
            text: `Đã index thành công: ${response.filename} (${response.pages_loaded} trang, ${response.chunks_added} chunks)`,
          });
        }
        setSelectedFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
        // Reload stats and indexed documents
        await loadIndexStats();
        await loadUploadedFiles();
        await loadIndexedDocuments();
      } else {
        setUploadMessage({ type: 'error', text: response.error || 'Lỗi khi index tài liệu' });
      }
    } catch (error) {
      console.error('Error uploading:', error);
      setUploadMessage({ type: 'error', text: 'Lỗi khi upload và index tài liệu' });
    } finally {
      setIsUploading(false);
    }
  };

  const handleQuery = async () => {
    if (!question.trim()) {
      setQueryError('Vui lòng nhập câu hỏi');
      return;
    }

    setIsQuerying(true);
    setQueryError(null);
    setQueryResult(null);

    try {
      const response = await queryRAG({
        question: question.trim(),
        return_context: showContext,
      });

      if (response.success) {
        setQueryResult({
          answer: response.answer,
          sources: response.sources,
          context: response.context,
        });
      } else {
        setQueryError(response.error || 'Lỗi khi truy vấn');
      }
    } catch (error) {
      console.error('Query error:', error);
      setQueryError('Lỗi khi xử lý câu hỏi. Hãy kiểm tra Ollama đang chạy.');
    } finally {
      setIsQuerying(false);
    }
  };

  const handleResetIndex = async () => {
    if (!window.confirm('Bạn có chắc muốn xóa toàn bộ index? Hành động này không thể hoàn tác.')) {
      return;
    }

    setIsResetting(true);

    try {
      const response = await resetRAGIndex();
      if (response.success) {
        setUploadMessage({ type: 'success', text: 'Đã reset index thành công' });
        setQueryResult(null);
        setGeneratedQuiz([]);
        await loadIndexStats();
      } else {
        setUploadMessage({ type: 'error', text: response.error || 'Lỗi khi reset index' });
      }
    } catch (error) {
      console.error('Reset error:', error);
      setUploadMessage({ type: 'error', text: 'Lỗi khi reset index' });
    } finally {
      setIsResetting(false);
    }
  };

  // Quiz generation handler
  const handleGenerateQuiz = async () => {
    if (!quizTopic.trim()) {
      setQuizError('Vui lòng nhập chủ đề quiz');
      return;
    }

    setIsGeneratingQuiz(true);
    setQuizError(null);
    setGeneratedQuiz([]);
    setEditingQuestionIndex(null);
    setEditingQuestion(null);

    try {
      const response = await generateQuiz({
        topic: quizTopic.trim(),
        num_questions: numQuestions,
        difficulty: quizDifficulty,
        language: quizLanguage,
      });

      if (response.success && response.questions.length > 0) {
        setGeneratedQuiz(response.questions);
      } else {
        setQuizError(response.error || 'Không thể tạo quiz. Hãy thử lại với chủ đề khác.');
      }
    } catch (error) {
      console.error('Quiz generation error:', error);
      setQuizError('Lỗi khi tạo quiz. Hãy kiểm tra Ollama đang chạy và có tài liệu đã được index.');
    } finally {
      setIsGeneratingQuiz(false);
    }
  };

  // Start editing a specific question
  const handleStartEdit = (index: number) => {
    setEditingQuestionIndex(index);
    setEditingQuestion(JSON.parse(JSON.stringify(generatedQuiz[index])));
  };

  // Update the currently editing question
  const handleEditQuestion = (field: string, value: any) => {
    if (!editingQuestion) return;
    
    const updated = { ...editingQuestion };
    if (field === 'option') {
      const [optionKey, optionValue] = value as [string, string];
      updated.options = {
        ...updated.options,
        [optionKey]: optionValue
      };
    } else {
      (updated as any)[field] = value;
    }
    setEditingQuestion(updated);
  };

  // Save a single question
  const handleSaveQuestion = () => {
    if (editingQuestionIndex === null || !editingQuestion) return;
    
    const updated = [...generatedQuiz];
    updated[editingQuestionIndex] = editingQuestion;
    setGeneratedQuiz(updated);
    setEditingQuestionIndex(null);
    setEditingQuestion(null);
  };

  // Cancel editing a single question
  const handleCancelEdit = () => {
    setEditingQuestionIndex(null);
    setEditingQuestion(null);
  };

  const handleExportQTI = async () => {
    if (generatedQuiz.length === 0) {
      setQuizError('Không có quiz để export');
      return;
    }

    setIsExporting(true);
    try {
      const blob = await exportQuizToQTI(generatedQuiz, quizTopic || 'Generated Quiz');
      
      // Download file
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `quiz_${quizTopic.replace(/\s+/g, '_')}.xml`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export error:', error);
      setQuizError('Lỗi khi export quiz');
    } finally {
      setIsExporting(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="document-rag-panel">
      <div className="panel-header">
        <FileText size={24} />
        <h2>RAG Tài liệu</h2>
      </div>

      <div className="rag-content">
        {/* Status Section */}
        <div className="status-section">
          <div className="status-cards">
            {/* LLM Provider Selector - Dropdown Style */}
            <div className="status-card llm-provider-card">
              <Zap size={20} className="provider-icon" />
              <div className="status-info">
                <span className="status-label">LLM Provider</span>
                <div className="provider-dropdown-wrapper">
                  <select
                    className="provider-dropdown"
                    value={llmProviderInfo?.current_provider || 'ollama'}
                    onChange={(e) => handleSwitchProvider(e.target.value as 'ollama' | 'groq')}
                    disabled={isSwitchingProvider}
                  >
                    <option value="ollama">
                      🖥️ Ollama (Local)
                    </option>
                    <option 
                      value="groq" 
                      disabled={!llmProviderInfo?.groq_configured}
                    >
                      ☁️ Groq Cloud {!llmProviderInfo?.groq_configured ? '(Chưa cấu hình)' : ''}
                    </option>
                  </select>
                  {isSwitchingProvider && (
                    <Loader2 size={14} className="spin provider-dropdown-loading" />
                  )}
                </div>
              </div>
            </div>

            {/* Current Model Status */}
            <div className={`status-card model-status-card ${ollamaStatus?.connected ? 'connected' : 'disconnected'}`}>
              <Server size={20} />
              <div className="status-info">
                <span className="status-label">Model Status</span>
                <span className="status-value">
                  {ollamaStatus?.connected ? (
                    <>
                      <CheckCircle size={14} className="status-icon success" />
                      <span className="model-name">{llmProviderInfo?.current_model || ollamaStatus.model || 'Connected'}</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle size={14} className="status-icon error" />
                      <span className="status-text">Chưa kết nối</span>
                    </>
                  )}
                </span>
              </div>
            </div>

            {/* Index Stats */}
            <div className="status-card">
              <Database size={20} />
              <div className="status-info">
                <span className="status-label">Documents</span>
                <span className="status-value">
                  {indexStats?.total_documents ?? 0} chunks
                </span>
              </div>
            </div>

            {/* Indexed Files */}
            <div className="status-card">
              <FileIcon size={20} />
              <div className="status-info">
                <span className="status-label">Files Indexed</span>
                <span className="status-value">
                  {indexStats?.indexed_file_hashes ?? 0}
                </span>
              </div>
            </div>
          </div>

          <button
            className="btn-icon refresh-btn"
            onClick={() => {
              loadIndexStats();
              loadOllamaStatus();
              loadUploadedFiles();
              loadLLMProviderInfo();
            }}
            title="Refresh status"
          >
            <RefreshCw size={16} />
          </button>
        </div>

        {/* Provider Switch Message */}
        {providerMessage && (
          <div className={`message provider-message ${providerMessage.type}`}>
            {providerMessage.type === 'success' && <CheckCircle size={16} />}
            {providerMessage.type === 'error' && <AlertCircle size={16} />}
            {providerMessage.text}
          </div>
        )}

        {/* Upload Section */}
        <div className="upload-section">
          <h3>
            <Upload size={18} />
            Upload & Index PDF
          </h3>
          
          <div className="upload-area">
            <input
              type="file"
              ref={fileInputRef}
              accept=".pdf"
              onChange={handleFileSelect}
              className="file-input"
              id="pdf-upload"
            />
            <label htmlFor="pdf-upload" className="file-label">
              <Upload size={24} />
              <span>{selectedFile ? selectedFile.name : 'Chọn file PDF'}</span>
              {selectedFile && (
                <span className="file-size">{formatFileSize(selectedFile.size)}</span>
              )}
            </label>
          </div>

          <div className="upload-actions">
            <button
              className="btn btn-primary"
              onClick={handleUploadAndIndex}
              disabled={!selectedFile || isUploading}
            >
              {isUploading ? (
                <>
                  <Loader2 size={16} className="spin" />
                  Đang xử lý...
                </>
              ) : (
                <>
                  <Database size={16} />
                  Build Index
                </>
              )}
            </button>

            <button
              className="btn btn-danger"
              onClick={handleResetIndex}
              disabled={isResetting || (indexStats?.total_documents ?? 0) === 0}
              title="Xóa toàn bộ index"
            >
              {isResetting ? (
                <Loader2 size={16} className="spin" />
              ) : (
                <Trash2 size={16} />
              )}
              Reset Index
            </button>
          </div>

          {uploadMessage && (
            <div className={`message ${uploadMessage.type}`}>
              {uploadMessage.type === 'success' && <CheckCircle size={16} />}
              {uploadMessage.type === 'error' && <AlertCircle size={16} />}
              {uploadMessage.type === 'info' && <Info size={16} />}
              {uploadMessage.text}
            </div>
          )}
        </div>

        {/* Tab Navigation */}
        <div className="tab-navigation">
          <button
            className={`tab-btn ${activeTab === 'quiz' ? 'active' : ''}`}
            onClick={() => setActiveTab('quiz')}
          >
            <BookOpen size={18} />
            Tạo Quiz
          </button>
          <button
            className={`tab-btn ${activeTab === 'query' ? 'active' : ''}`}
            onClick={() => setActiveTab('query')}
          >
            <Search size={18} />
            Hỏi đáp
          </button>
        </div>

        {/* Quiz Generation Section */}
        {activeTab === 'quiz' && (
          <div className="quiz-section">
            <h3>
              <BookOpen size={18} />
              Tạo Quiz từ tài liệu
            </h3>

            <div className="quiz-form">
              {/* Document selector for topic suggestions */}
              {indexedDocuments.length > 0 && (
                <div className="form-group document-selector">
                  <label>
                    <FileText size={14} />
                    Chọn tài liệu để gợi ý chủ đề
                  </label>
                  <select
                    value={selectedDocument}
                    onChange={(e) => {
                      setSelectedDocument(e.target.value);
                      setShowTopicSuggestions(false);
                      setSuggestedTopics([]);
                    }}
                    disabled={isGeneratingQuiz}
                    className="document-select"
                  >
                    {indexedDocuments.map((doc) => (
                      <option key={doc.filename} value={doc.filename}>
                        {doc.original_filename} ({doc.topic_count} chủ đề)
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="form-group topic-input-group">
                <label>Chủ đề Quiz</label>
                <div className="topic-input-wrapper">
                  <input
                    type="text"
                    value={quizTopic}
                    onChange={(e) => setQuizTopic(e.target.value)}
                    placeholder="Nhập chủ đề bạn muốn tạo quiz..."
                    disabled={isGeneratingQuiz}
                  />
                  <button
                    type="button"
                    className="btn btn-suggest-topics"
                    onClick={loadSuggestedTopics}
                    disabled={isLoadingTopics || isGeneratingQuiz || !selectedDocument}
                    title={selectedDocument ? `Gợi ý chủ đề từ ${selectedDocument}` : "Chọn tài liệu trước"}
                  >
                    {isLoadingTopics ? (
                      <Loader2 size={16} className="spin" />
                    ) : (
                      <HelpCircle size={16} />
                    )}
                    Gợi ý
                  </button>
                </div>
                
                {/* Topic suggestions dropdown */}
                {showTopicSuggestions && suggestedTopics.length > 0 && (
                  <div className="topic-suggestions">
                    <div className="suggestions-header">
                      <span>Chủ đề từ: <strong>{indexedDocuments.find(d => d.filename === selectedDocument)?.original_filename || selectedDocument}</strong></span>
                      <button 
                        className="btn-close-suggestions"
                        onClick={() => setShowTopicSuggestions(false)}
                      >
                        <X size={14} />
                      </button>
                    </div>
                    <ul className="suggestions-list">
                      {suggestedTopics.map((topic, index) => (
                        <li 
                          key={index} 
                          onClick={() => handleSelectTopic(topic)}
                          className="suggestion-item"
                        >
                          <span className="topic-name">{topic.name}</span>
                          {topic.description && (
                            <span className="topic-description">{topic.description}</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Số câu hỏi</label>
                  <select
                    value={numQuestions}
                    onChange={(e) => setNumQuestions(Number(e.target.value))}
                    disabled={isGeneratingQuiz}
                  >
                    {[3, 5, 7, 10, 15, 20].map(n => (
                      <option key={n} value={n}>{n} câu</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Độ khó</label>
                  <select
                    value={quizDifficulty}
                    onChange={(e) => setQuizDifficulty(e.target.value as 'easy' | 'medium' | 'hard')}
                    disabled={isGeneratingQuiz}
                  >
                    <option value="easy">Dễ</option>
                    <option value="medium">Trung bình</option>
                    <option value="hard">Khó</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Ngôn ngữ</label>
                  <select
                    value={quizLanguage}
                    onChange={(e) => setQuizLanguage(e.target.value as 'vi' | 'en')}
                    disabled={isGeneratingQuiz}
                  >
                    <option value="vi">Tiếng Việt</option>
                    <option value="en">English</option>
                  </select>
                </div>
              </div>

              <button
                className="btn btn-primary btn-generate"
                onClick={handleGenerateQuiz}
                disabled={!quizTopic.trim() || isGeneratingQuiz || (indexStats?.total_documents ?? 0) === 0}
              >
                {isGeneratingQuiz ? (
                  <>
                    <Loader2 size={16} className="spin" />
                    Đang tạo quiz...
                  </>
                ) : (
                  <>
                    <BookOpen size={16} />
                    Tạo Quiz
                  </>
                )}
              </button>

              {(indexStats?.total_documents ?? 0) === 0 && (
                <div className="message info">
                  <Info size={16} />
                  Vui lòng upload và index tài liệu PDF trước khi tạo quiz.
                </div>
              )}

              {quizError && (
                <div className="message error">
                  <AlertCircle size={16} />
                  {quizError}
                </div>
              )}
            </div>

            {/* Generated Quiz Display */}
            {generatedQuiz.length > 0 && (
              <div className="quiz-display">
                <div className="quiz-header">
                  <h4>
                    <HelpCircle size={18} />
                    Quiz: {quizTopic}
                  </h4>
                  <div className="quiz-header-actions">
                    <button
                      className="btn btn-primary"
                      onClick={handleExportQTI}
                      disabled={isExporting || editingQuestionIndex !== null}
                    >
                      {isExporting ? (
                        <><Loader2 size={16} className="spin" /> Đang export...</>
                      ) : (
                        <><Download size={16} /> Export QTI</>
                      )}
                    </button>
                  </div>
                </div>

                <div className="quiz-questions">
                  {generatedQuiz.map((q, idx) => (
                    <div key={idx} className={`quiz-question ${editingQuestionIndex === idx ? 'editing' : ''}`}>
                      <div className="question-header">
                        <span className="question-number">Câu {q.question_number}</span>
                        {editingQuestionIndex !== idx && (
                          <button
                            className="btn-edit-question"
                            onClick={() => handleStartEdit(idx)}
                            title="Chỉnh sửa câu hỏi"
                          >
                            <Edit2 size={14} strokeWidth={2} />
                            <span>Chỉnh sửa</span>
                          </button>
                        )}
                      </div>
                      
                      {editingQuestionIndex === idx && editingQuestion ? (
                        <>
                          <textarea
                            className="edit-question-text"
                            value={editingQuestion.question}
                            onChange={(e) => handleEditQuestion('question', e.target.value)}
                            rows={2}
                          />
                          
                          <div className="question-options edit-mode">
                            {Object.entries(editingQuestion.options).map(([key, value]) => (
                              <div key={key} className="edit-option">
                                <span className="option-key">{key}</span>
                                <input
                                  type="text"
                                  className="edit-option-input"
                                  value={value}
                                  onChange={(e) => handleEditQuestion('option', [key, e.target.value])}
                                />
                                <label className="correct-label">
                                  <input
                                    type="radio"
                                    name={`correct-${idx}`}
                                    checked={editingQuestion.correct_answer === key}
                                    onChange={() => handleEditQuestion('correct_answer', key)}
                                  />
                                  <span>Đúng</span>
                                </label>
                              </div>
                            ))}
                          </div>

                          <div className="edit-explanation">
                            <label>Giải thích:</label>
                            <textarea
                              value={editingQuestion.explanation || ''}
                              onChange={(e) => handleEditQuestion('explanation', e.target.value)}
                              rows={2}
                              placeholder="Nhập giải thích (tùy chọn)..."
                            />
                          </div>
                          
                          <div className="question-edit-actions">
                            <button
                              className="btn btn-sm btn-secondary"
                              onClick={handleCancelEdit}
                            >
                              <X size={14} />
                              Hủy
                            </button>
                            <button
                              className="btn btn-sm btn-success"
                              onClick={handleSaveQuestion}
                            >
                              <Save size={14} />
                              Lưu
                            </button>
                          </div>
                        </>
                      ) : (
                        <>
                          <div className="question-text">{q.question}</div>
                          
                          <div className="question-options">
                            {Object.entries(q.options).map(([key, value]) => (
                              <div
                                key={key}
                                className={`option-label ${key === q.correct_answer ? 'correct-answer' : ''}`}
                              >
                                <span className="option-key">{key}</span>
                                <span className="option-value">{value}</span>
                                {key === q.correct_answer && (
                                  <Check size={14} className="correct-icon" style={{ color: '#10b981', marginLeft: 'auto' }} />
                                )}
                              </div>
                            ))}
                          </div>

                          {q.explanation && (
                            <div className="question-explanation">
                              <strong>Giải thích:</strong> {q.explanation}
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  ))}
                </div>

                <div className="quiz-actions">
                  <button
                    className="btn btn-primary"
                    onClick={() => {
                      setGeneratedQuiz([]);
                      setQuizError(null);
                      setEditingQuestionIndex(null);
                      setEditingQuestion(null);
                    }}
                  >
                    <RefreshCw size={16} />
                    Tạo Quiz mới
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Query Section */}
        {activeTab === 'query' && (
        <>
        <div className="query-section">
          <h3>
            <Search size={18} />
            Hỏi đáp tài liệu
          </h3>

          <div className="query-input-area">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Nhập câu hỏi của bạn..."
              rows={3}
              disabled={isQuerying}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && e.ctrlKey) {
                  handleQuery();
                }
              }}
            />
            
            <div className="query-options">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={showContext}
                  onChange={(e) => setShowContext(e.target.checked)}
                />
                Hiển thị context đã retrieve
              </label>
            </div>

            <button
              className="btn btn-primary btn-ask"
              onClick={handleQuery}
              disabled={!question.trim() || isQuerying}
            >
              {isQuerying ? (
                <>
                  <Loader2 size={16} className="spin" />
                  Đang xử lý...
                </>
              ) : (
                <>
                  <Search size={16} />
                  Ask (Ctrl+Enter)
                </>
              )}
            </button>
          </div>

          {queryError && (
            <div className="message error">
              <AlertCircle size={16} />
              {queryError}
            </div>
          )}
        </div>

        {/* Results Section */}
        {queryResult && (
          <div className="results-section">
            <h3>Kết quả</h3>
            
            {/* Answer */}
            <div className="answer-box">
              <h4>Answer</h4>
              <div className="answer-content">
                {queryResult.answer}
              </div>
            </div>

            {/* Sources */}
            {queryResult.sources.length > 0 && (
              <div className="sources-box">
                <button
                  className="sources-toggle"
                  onClick={() => setShowSources(!showSources)}
                >
                  <h4>Sources ({queryResult.sources.length})</h4>
                  {showSources ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
                
                {showSources && (
                  <div className="sources-list">
                    {queryResult.sources.map((source, idx) => (
                      <div key={idx} className="source-item">
                        <div className="source-header">
                          <FileText size={14} />
                          <span className="source-name">{source.filename || source.source}</span>
                          <span className="source-page">Trang {source.page}</span>
                        </div>
                        <div className="source-snippet">
                          {source.snippet}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Context (optional) */}
            {showContext && queryResult.context && (
              <div className="context-box">
                <h4>Retrieved Context</h4>
                <pre className="context-content">
                  {queryResult.context}
                </pre>
              </div>
            )}
          </div>
        )}
        </>
        )}

        {/* Uploaded Files List */}
        {uploadedFiles.length > 0 && (
          <div className="files-section">
            <h3>
              <FileIcon size={18} />
              Files đã upload
            </h3>
            <div className="files-list">
              {uploadedFiles.map((file, idx) => (
                <div key={idx} className="file-item">
                  <FileText size={16} />
                  <span className="file-name">{file.filename}</span>
                  <span className="file-size">{formatFileSize(file.size)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <style>{`
        .document-rag-panel {
          display: flex;
          flex-direction: column;
          height: 100%;
          overflow: hidden;
        }

        .panel-header {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 20px 24px;
          border-bottom: 1px solid var(--border-color, #e5e7eb);
        }

        .panel-header h2 {
          margin: 0;
          font-size: 1.25rem;
          font-weight: 600;
        }

        .rag-content {
          flex: 1;
          overflow-y: auto;
          padding: 24px;
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        /* Status Section */
        .status-section {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .status-cards {
          display: flex;
          gap: 12px;
          flex: 1;
          flex-wrap: wrap;
        }

        .status-card {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          background: white;
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 10px;
          min-width: 150px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
          transition: all 0.2s ease;
        }

        .status-card:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
          transform: translateY(-1px);
        }

        .status-card.connected {
          border-color: #10b981;
          background: #ecfdf5;
        }

        .status-card.disconnected {
          border-color: #ef4444;
          background: #fef2f2;
        }

        .status-info {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .status-label {
          font-size: 0.75rem;
          color: var(--text-secondary, #6b7280);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .status-value {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 0.875rem;
          font-weight: 600;
          color: #1e293b;
        }

        .status-icon.success {
          color: #10b981;
        }

        .status-icon.error {
          color: #ef4444;
        }

        .refresh-btn {
          padding: 8px;
          border-radius: 6px;
        }

        /* Upload Section */
        .upload-section, .query-section, .results-section, .files-section {
          background: white;
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 16px;
          padding: 24px;
          box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
          transition: box-shadow 0.2s ease;
        }

        .upload-section:hover, .query-section:hover, .results-section:hover, .files-section:hover {
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        }

        .upload-section h3, .query-section h3, .results-section h3, .files-section h3 {
          display: flex;
          align-items: center;
          gap: 10px;
          margin: 0 0 20px 0;
          font-size: 1.1rem;
          font-weight: 700;
          color: #1e293b;
          padding-bottom: 12px;
          border-bottom: 2px solid #e2e8f0;
        }

        .upload-section h3 svg, .query-section h3 svg, .results-section h3 svg, .files-section h3 svg {
          color: #3b82f6;
        }

        .upload-area {
          margin-bottom: 20px;
        }

        .file-input {
          display: none;
        }

        .file-label {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
          padding: 40px;
          border: 3px dashed #cbd5e1;
          border-radius: 16px;
          cursor: pointer;
          transition: all 0.3s ease;
          color: #64748b;
          background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        }

        .file-label:hover {
          border-color: #3b82f6;
          background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
          color: #3b82f6;
          transform: translateY(-2px);
        }

        .file-label svg {
          color: #94a3b8;
          transition: color 0.3s ease;
        }

        .file-label:hover svg {
          color: #3b82f6;
        }

        .file-label span {
          font-weight: 500;
          font-size: 0.95rem;
        }

        .upload-actions {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }

        /* Buttons */
        .btn {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          font-size: 0.875rem;
          font-weight: 500;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .btn-primary {
          background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
          color: white;
          box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
        }

        .btn-primary:hover:not(:disabled) {
          background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
          box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
          transform: translateY(-1px);
        }

        .btn-danger {
          background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
          color: #dc2626;
          border: 1px solid #fca5a5;
        }

        .btn-danger:hover:not(:disabled) {
          background: linear-gradient(135deg, #fecaca 0%, #fca5a5 100%);
          transform: translateY(-1px);
        }

        .btn-icon {
          padding: 10px;
          background: white;
          border: 2px solid #e2e8f0;
          border-radius: 10px;
          cursor: pointer;
          color: #64748b;
          transition: all 0.2s ease;
        }

        .btn-icon:hover {
          background: #f1f5f9;
          border-color: #94a3b8;
          color: #475569;
        }

        /* Messages */
        .message {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 14px 16px;
          border-radius: 12px;
          font-size: 0.9rem;
          font-weight: 500;
          margin-top: 16px;
        }

        .message.success {
          background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
          color: #065f46;
          border: 2px solid #10b981;
        }

        .message.error {
          background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
          color: #991b1b;
          border: 2px solid #ef4444;
        }

        .message.info {
          background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
          color: #1e40af;
          border: 2px solid #3b82f6;
        }

        /* Query Section */
        .query-input-area textarea {
          width: 100%;
          padding: 14px;
          border: 2px solid #e2e8f0;
          border-radius: 12px;
          resize: vertical;
          font-family: inherit;
          font-size: 0.9rem;
          color: #1e293b;
          background: #f8fafc;
          transition: all 0.2s ease;
        }

        .query-input-area textarea::placeholder {
          color: #94a3b8;
        }

        .query-input-area textarea:focus {
          outline: none;
          border-color: #3b82f6;
          background: white;
          box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.15);
        }

        .query-options {
          margin: 14px 0;
        }

        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 0.9rem;
          color: #475569;
          cursor: pointer;
          font-weight: 500;
        }

        .checkbox-label input {
          cursor: pointer;
          width: 18px;
          height: 18px;
          accent-color: #3b82f6;
        }

        .btn-ask {
          width: 100%;
          justify-content: center;
          padding: 14px;
          font-size: 0.95rem;
        }

        /* Results */
        .answer-box, .sources-box, .context-box {
          background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 16px;
          border: 1px solid #e2e8f0;
        }

        .answer-box h4, .sources-box h4, .context-box h4 {
          margin: 0 0 14px 0;
          font-size: 0.95rem;
          font-weight: 700;
          color: #1e293b;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .answer-box h4::before {
          content: '💬';
        }

        .sources-box h4::before {
          content: '📚';
        }

        .context-box h4::before {
          content: '📄';
        }

        .answer-content {
          font-size: 0.95rem;
          line-height: 1.7;
          white-space: pre-wrap;
          color: #1e293b;
        }

        .sources-toggle {
          display: flex;
          align-items: center;
          justify-content: space-between;
          width: 100%;
          background: none;
          border: none;
          cursor: pointer;
          padding: 0;
        }

        .sources-toggle h4 {
          margin: 0;
        }

        .sources-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
          margin-top: 12px;
        }

        .source-item {
          background: white;
          border: 2px solid #e2e8f0;
          border-radius: 10px;
          padding: 14px;
          transition: all 0.2s ease;
        }

        .source-item:hover {
          border-color: #93c5fd;
          box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
        }

        .source-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 10px;
          font-size: 0.875rem;
        }

        .source-name {
          font-weight: 600;
          color: #1e293b;
        }

        .source-page {
          margin-left: auto;
          color: #64748b;
          font-size: 0.8rem;
          font-weight: 500;
          background: #f1f5f9;
          padding: 2px 8px;
          border-radius: 4px;
        }

        .source-snippet {
          font-size: 0.875rem;
          color: #475569;
          line-height: 1.6;
        }

        .context-content {
          font-size: 0.875rem;
          line-height: 1.6;
          max-height: 300px;
          overflow-y: auto;
          white-space: pre-wrap;
          margin: 0;
          font-family: inherit;
          color: #475569;
        }

        /* Files List */
        .files-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .file-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
          border: 1px solid #e2e8f0;
          border-radius: 10px;
          font-size: 0.9rem;
          transition: all 0.2s ease;
        }

        .file-item:hover {
          background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
          border-color: #93c5fd;
        }

        .file-name {
          flex: 1;
          color: #1e293b;
          font-weight: 500;
        }

        .file-size {
          font-size: 0.8rem;
          color: #64748b;
          font-weight: 500;
        }

        /* Animations */
        .spin {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }

        /* Tab Navigation */
        .tab-navigation {
          display: flex;
          gap: 8px;
          padding: 6px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
          border: 1px solid #e5e7eb;
        }

        .tab-btn {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 24px;
          background: transparent;
          border: none;
          border-radius: 10px;
          font-size: 0.9rem;
          font-weight: 600;
          color: #64748b;
          cursor: pointer;
          transition: all 0.2s ease;
          flex: 1;
          justify-content: center;
        }

        .tab-btn:hover {
          background: rgba(255, 255, 255, 0.5);
        }

        .tab-btn.active {
          background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
          color: white;
          box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
        }

        .tab-btn.active svg {
          color: white;
        }

        /* Quiz Section */
        .quiz-section {
          background: white;
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 16px;
          padding: 24px;
          box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
        }

        .quiz-section h3 {
          display: flex;
          align-items: center;
          gap: 10px;
          margin: 0 0 20px 0;
          font-size: 1.1rem;
          font-weight: 700;
          color: #1e293b;
          padding-bottom: 12px;
          border-bottom: 2px solid #e2e8f0;
        }

        .quiz-section h3 svg {
          color: #3b82f6;
        }

        .quiz-form {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .form-group {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        /* Document selector for topic suggestions */
        .document-selector {
          margin-bottom: 8px;
        }

        .document-selector label {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--text-secondary, #64748b);
        }

        .document-select {
          padding: 8px 12px;
          border: 1px solid var(--border-color, #e2e8f0);
          border-radius: 8px;
          font-size: 0.875rem;
          background: white;
          cursor: pointer;
          transition: all 0.2s;
        }

        .document-select:hover {
          border-color: var(--primary, #3b82f6);
        }

        .document-select:focus {
          outline: none;
          border-color: var(--primary, #3b82f6);
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .topic-input-group {
          position: relative;
        }

        .topic-input-wrapper {
          display: flex;
          gap: 8px;
        }

        .topic-input-wrapper input {
          flex: 1;
        }

        .btn-suggest-topics {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px 12px;
          background: var(--bg-secondary, #f3f4f6);
          border: 1px solid var(--border-color, #d1d5db);
          border-radius: 8px;
          font-size: 0.8125rem;
          color: var(--text-secondary, #6b7280);
          cursor: pointer;
          transition: all 0.2s;
          white-space: nowrap;
        }

        .btn-suggest-topics:hover:not(:disabled) {
          background: var(--primary-light, #eff6ff);
          border-color: var(--primary, #3b82f6);
          color: var(--primary, #3b82f6);
        }

        .btn-suggest-topics:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .topic-suggestions {
          position: absolute;
          top: 100%;
          left: 0;
          right: 0;
          margin-top: 4px;
          background: white;
          border: 1px solid var(--border-color, #d1d5db);
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          z-index: 100;
          max-height: 300px;
          overflow-y: auto;
        }

        .suggestions-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 10px 12px;
          border-bottom: 1px solid var(--border-color, #e5e7eb);
          font-size: 0.8125rem;
          font-weight: 500;
          color: var(--text-secondary, #6b7280);
        }

        .btn-close-suggestions {
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 4px;
          background: none;
          border: none;
          color: var(--text-tertiary, #9ca3af);
          cursor: pointer;
          border-radius: 4px;
        }

        .btn-close-suggestions:hover {
          background: var(--bg-secondary, #f3f4f6);
          color: var(--text-secondary, #6b7280);
        }

        .suggestions-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .suggestion-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
          padding: 10px 12px;
          cursor: pointer;
          transition: background 0.15s;
          border-bottom: 1px solid var(--border-light, #f3f4f6);
        }

        .suggestion-item:last-child {
          border-bottom: none;
        }

        .suggestion-item:hover {
          background: var(--primary-light, #eff6ff);
        }

        .topic-name {
          font-size: 0.9rem;
          font-weight: 600;
          color: #1e293b;
        }

        .topic-description {
          font-size: 0.8rem;
          color: #64748b;
          line-height: 1.4;
        }

        .form-group label {
          font-size: 0.875rem;
          font-weight: 600;
          color: #374151;
        }

        .form-group input,
        .form-group select {
          padding: 12px 14px;
          border: 2px solid #e2e8f0;
          border-radius: 10px;
          font-size: 0.9rem;
          color: #1e293b;
          background: #f8fafc;
          transition: all 0.2s ease;
        }

        .form-group input::placeholder {
          color: #94a3b8;
        }

        .form-group input:focus,
        .form-group select:focus {
          outline: none;
          border-color: #3b82f6;
          background: white;
          box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.15);
        }

        .form-row {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
        }

        .btn-generate {
          width: 100%;
          justify-content: center;
          padding: 12px;
        }

        /* Quiz Display */
        .quiz-display {
          margin-top: 24px;
          border-top: 1px solid var(--border-color, #e5e7eb);
          padding-top: 24px;
        }

        .quiz-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 20px;
        }

        .quiz-header h4 {
          display: flex;
          align-items: center;
          gap: 8px;
          margin: 0;
          font-size: 1.1rem;
          color: var(--text-primary, #111827);
        }

        .quiz-score {
          padding: 8px 16px;
          background: var(--primary, #3b82f6);
          color: white;
          border-radius: 20px;
          font-weight: 600;
          font-size: 0.875rem;
        }

        .quiz-questions {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .quiz-question {
          background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
          border: 2px solid #e2e8f0;
          border-radius: 16px;
          padding: 24px;
          transition: all 0.2s ease;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }

        .quiz-question:hover {
          border-color: #cbd5e1;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }

        .quiz-question.editing {
          border-color: #3b82f6;
          background: linear-gradient(135deg, #eff6ff 0%, #f0f9ff 100%);
          box-shadow: 0 4px 16px rgba(59, 130, 246, 0.15);
        }

        .quiz-question.correct {
          border-color: #10b981;
          background: #ecfdf5;
        }

        .quiz-question.incorrect {
          border-color: #ef4444;
          background: #fef2f2;
        }

        .question-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 12px;
        }

        .question-number {
          font-weight: 700;
          color: white;
          font-size: 0.8rem;
          background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
          padding: 6px 14px;
          border-radius: 20px;
          box-shadow: 0 2px 6px rgba(59, 130, 246, 0.3);
        }

        .btn-edit-question {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          padding: 6px 12px;
          border: 1px solid #cbd5e1;
          background: #f8fafc;
          border-radius: 8px;
          cursor: pointer;
          color: #475569;
          transition: all 0.2s;
          font-size: 13px;
          font-weight: 500;
          white-space: nowrap;
        }

        .btn-edit-question:hover {
          background: #e0e7ff;
          border-color: #3b82f6;
          color: #3b82f6;
        }

        .question-edit-actions {
          display: flex;
          justify-content: flex-end;
          gap: 8px;
          margin-top: 16px;
          padding-top: 16px;
          border-top: 1px solid #e2e8f0;
        }

        .btn.btn-sm {
          padding: 6px 12px;
          font-size: 0.8125rem;
        }

        .btn.btn-success {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: white;
          border: none;
        }

        .btn.btn-success:hover {
          background: linear-gradient(135deg, #059669 0%, #047857 100%);
        }

        .answer-status {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 0.8125rem;
          font-weight: 500;
        }

        .answer-status.correct {
          color: #10b981;
        }

        .answer-status.incorrect {
          color: #ef4444;
        }

        .question-text {
          font-size: 1rem;
          font-weight: 600;
          margin-bottom: 20px;
          line-height: 1.6;
          color: #1e293b;
        }

        .question-options {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .option-label {
          display: flex;
          align-items: center;
          gap: 14px;
          padding: 14px 18px;
          background: white;
          border: 2px solid #e2e8f0;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .option-label:hover:not(.correct-answer):not(.wrong-answer) {
          border-color: var(--primary, #3b82f6);
          background: #eff6ff;
        }

        .option-label.selected {
          border-color: var(--primary, #3b82f6);
          background: #eff6ff;
        }

        .option-label.correct-answer {
          border-color: #10b981;
          background: #ecfdf5;
        }

        .option-label.wrong-answer {
          border-color: #ef4444;
          background: #fef2f2;
        }

        .option-label input {
          cursor: pointer;
        }

        .option-key {
          font-weight: 700;
          color: #475569;
          min-width: 28px;
          height: 28px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #f1f5f9;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          font-size: 0.85rem;
        }

        .correct-answer .option-key {
          background: #dcfce7;
          border-color: #10b981;
          color: #166534;
        }

        .option-value {
          font-size: 0.9rem;
          color: #1e293b;
          font-weight: 500;
        }

        .question-explanation {
          margin-top: 20px;
          padding: 16px;
          background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
          border: 2px solid #f59e0b;
          border-radius: 12px;
          font-size: 0.875rem;
          color: #78350f;
          font-weight: 500;
          line-height: 1.5;
        }

        .question-explanation::before {
          content: '💡 ';
        }

        .quiz-actions {
          margin-top: 24px;
          display: flex;
          justify-content: center;
          gap: 12px;
        }

        .quiz-actions .btn {
          min-width: 200px;
          justify-content: center;
        }

        /* Quiz Edit Mode */
        .quiz-header-actions {
          display: flex;
          gap: 12px;
        }

        .btn-secondary {
          background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
          color: #475569;
          border: 1px solid #cbd5e1;
        }

        .btn-secondary:hover:not(:disabled) {
          background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
          color: #334155;
        }

        .edit-question-text {
          width: 100%;
          padding: 14px;
          border: 2px solid #e2e8f0;
          border-radius: 10px;
          font-size: 1rem;
          font-weight: 500;
          margin-bottom: 16px;
          font-family: inherit;
          resize: vertical;
          color: #1e293b;
          background: #f8fafc;
        }

        .edit-question-text:focus {
          outline: none;
          border-color: var(--primary, #3b82f6);
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .question-options.edit-mode {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .edit-option {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 14px;
          background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
          border: 2px solid #e2e8f0;
          border-radius: 12px;
        }

        .edit-option-input {
          flex: 1;
          padding: 10px 14px;
          border: 2px solid #e2e8f0;
          border-radius: 8px;
          font-size: 0.9rem;
          color: #1e293b;
          background: white;
        }

        .edit-option-input:focus {
          outline: none;
          border-color: var(--primary, #3b82f6);
        }

        .correct-label {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 0.8125rem;
          color: #10b981;
          font-weight: 500;
          white-space: nowrap;
          cursor: pointer;
        }

        .edit-explanation {
          margin-top: 16px;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .edit-explanation label {
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--text-secondary, #6b7280);
        }

        .edit-explanation textarea {
          width: 100%;
          padding: 10px 12px;
          border: 1px solid var(--border-color, #d1d5db);
          border-radius: 8px;
          font-size: 0.8125rem;
          font-family: inherit;
          resize: vertical;
        }

        .edit-explanation textarea:focus {
          outline: none;
          border-color: var(--primary, #3b82f6);
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .correct-icon {
          margin-left: auto;
        }
      `}</style>
    </div>
  );
};

export default DocumentRAGPanel;
