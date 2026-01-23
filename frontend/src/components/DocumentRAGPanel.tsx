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
} from 'lucide-react';
import {
  uploadAndIndexDocument,
  queryRAG,
  getRAGStats,
  resetRAGIndex,
  checkOllamaStatus,
  listUploadedFiles,
  generateQuiz,
  type RAGSource,
  type RAGIndexStats,
  type RAGUploadedFile,
  type OllamaStatus,
  type QuizQuestion,
} from '../api/documentRag';

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
  const [userAnswers, setUserAnswers] = useState<{[key: number]: string}>({});
  const [showAnswers, setShowAnswers] = useState(false);
  
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
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load initial data
  useEffect(() => {
    loadIndexStats();
    loadOllamaStatus();
    loadUploadedFiles();
  }, []);

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
        // Reload stats
        await loadIndexStats();
        await loadUploadedFiles();
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
    setUserAnswers({});
    setShowAnswers(false);

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

  const handleAnswerSelect = (questionNum: number, answer: string) => {
    if (!showAnswers) {
      setUserAnswers(prev => ({
        ...prev,
        [questionNum]: answer,
      }));
    }
  };

  const handleSubmitQuiz = () => {
    setShowAnswers(true);
  };

  const calculateScore = () => {
    let correct = 0;
    generatedQuiz.forEach(q => {
      if (userAnswers[q.question_number] === q.correct_answer) {
        correct++;
      }
    });
    return { correct, total: generatedQuiz.length };
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
            {/* Ollama Status */}
            <div className={`status-card ${ollamaStatus?.connected ? 'connected' : 'disconnected'}`}>
              <Server size={20} />
              <div className="status-info">
                <span className="status-label">Ollama</span>
                <span className="status-value">
                  {ollamaStatus?.connected ? (
                    <>
                      <CheckCircle size={14} className="status-icon success" />
                      {ollamaStatus.model || 'Connected'}
                    </>
                  ) : (
                    <>
                      <AlertCircle size={14} className="status-icon error" />
                      Chưa kết nối
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
            }}
            title="Refresh status"
          >
            <RefreshCw size={16} />
          </button>
        </div>

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
              <div className="form-group">
                <label>Chủ đề Quiz</label>
                <input
                  type="text"
                  value={quizTopic}
                  onChange={(e) => setQuizTopic(e.target.value)}
                  placeholder="Nhập chủ đề bạn muốn tạo quiz..."
                  disabled={isGeneratingQuiz}
                />
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
                  {showAnswers && (
                    <div className="quiz-score">
                      Điểm: {calculateScore().correct}/{calculateScore().total}
                    </div>
                  )}
                </div>

                <div className="quiz-questions">
                  {generatedQuiz.map((q, idx) => (
                    <div key={idx} className={`quiz-question ${showAnswers ? (userAnswers[q.question_number] === q.correct_answer ? 'correct' : 'incorrect') : ''}`}>
                      <div className="question-header">
                        <span className="question-number">Câu {q.question_number}</span>
                        {showAnswers && (
                          <span className={`answer-status ${userAnswers[q.question_number] === q.correct_answer ? 'correct' : 'incorrect'}`}>
                            {userAnswers[q.question_number] === q.correct_answer ? (
                              <><Check size={14} /> Đúng</>
                            ) : (
                              <><X size={14} /> Sai</>
                            )}
                          </span>
                        )}
                      </div>
                      <div className="question-text">{q.question}</div>
                      
                      <div className="question-options">
                        {Object.entries(q.options).map(([key, value]) => (
                          <label
                            key={key}
                            className={`option-label ${
                              userAnswers[q.question_number] === key ? 'selected' : ''
                            } ${
                              showAnswers && key === q.correct_answer ? 'correct-answer' : ''
                            } ${
                              showAnswers && userAnswers[q.question_number] === key && key !== q.correct_answer ? 'wrong-answer' : ''
                            }`}
                          >
                            <input
                              type="radio"
                              name={`question-${q.question_number}`}
                              value={key}
                              checked={userAnswers[q.question_number] === key}
                              onChange={() => handleAnswerSelect(q.question_number, key)}
                              disabled={showAnswers}
                            />
                            <span className="option-key">{key}</span>
                            <span className="option-value">{value}</span>
                          </label>
                        ))}
                      </div>

                      {showAnswers && q.explanation && (
                        <div className="question-explanation">
                          <strong>Giải thích:</strong> {q.explanation}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                <div className="quiz-actions">
                  {!showAnswers ? (
                    <button
                      className="btn btn-primary"
                      onClick={handleSubmitQuiz}
                      disabled={Object.keys(userAnswers).length !== generatedQuiz.length}
                    >
                      <Check size={16} />
                      Nộp bài ({Object.keys(userAnswers).length}/{generatedQuiz.length})
                    </button>
                  ) : (
                    <button
                      className="btn btn-primary"
                      onClick={() => {
                        setGeneratedQuiz([]);
                        setUserAnswers({});
                        setShowAnswers(false);
                      }}
                    >
                      <RefreshCw size={16} />
                      Tạo Quiz mới
                    </button>
                  )}
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
          background: var(--card-bg, #f9fafb);
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 8px;
          min-width: 150px;
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
          font-weight: 500;
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
          background: var(--card-bg, #ffffff);
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 12px;
          padding: 20px;
        }

        .upload-section h3, .query-section h3, .results-section h3, .files-section h3 {
          display: flex;
          align-items: center;
          gap: 8px;
          margin: 0 0 16px 0;
          font-size: 1rem;
          font-weight: 600;
        }

        .upload-area {
          margin-bottom: 16px;
        }

        .file-input {
          display: none;
        }

        .file-label {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
          padding: 32px;
          border: 2px dashed var(--border-color, #d1d5db);
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s;
          color: var(--text-secondary, #6b7280);
        }

        .file-label:hover {
          border-color: var(--primary, #3b82f6);
          background: var(--primary-light, #eff6ff);
        }

        .file-size {
          font-size: 0.75rem;
          color: var(--text-tertiary, #9ca3af);
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
          background: var(--primary, #3b82f6);
          color: white;
        }

        .btn-primary:hover:not(:disabled) {
          background: var(--primary-dark, #2563eb);
        }

        .btn-danger {
          background: #fee2e2;
          color: #dc2626;
        }

        .btn-danger:hover:not(:disabled) {
          background: #fecaca;
        }

        .btn-icon {
          padding: 8px;
          background: transparent;
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 6px;
          cursor: pointer;
        }

        .btn-icon:hover {
          background: var(--hover-bg, #f3f4f6);
        }

        /* Messages */
        .message {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px;
          border-radius: 8px;
          font-size: 0.875rem;
          margin-top: 12px;
        }

        .message.success {
          background: #ecfdf5;
          color: #065f46;
          border: 1px solid #a7f3d0;
        }

        .message.error {
          background: #fef2f2;
          color: #991b1b;
          border: 1px solid #fecaca;
        }

        .message.info {
          background: #eff6ff;
          color: #1e40af;
          border: 1px solid #bfdbfe;
        }

        /* Query Section */
        .query-input-area textarea {
          width: 100%;
          padding: 12px;
          border: 1px solid var(--border-color, #d1d5db);
          border-radius: 8px;
          resize: vertical;
          font-family: inherit;
          font-size: 0.875rem;
        }

        .query-input-area textarea:focus {
          outline: none;
          border-color: var(--primary, #3b82f6);
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .query-options {
          margin: 12px 0;
        }

        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.875rem;
          color: var(--text-secondary, #6b7280);
          cursor: pointer;
        }

        .checkbox-label input {
          cursor: pointer;
        }

        .btn-ask {
          width: 100%;
          justify-content: center;
        }

        /* Results */
        .answer-box, .sources-box, .context-box {
          background: var(--bg-secondary, #f9fafb);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 12px;
        }

        .answer-box h4, .sources-box h4, .context-box h4 {
          margin: 0 0 12px 0;
          font-size: 0.875rem;
          font-weight: 600;
          color: var(--text-secondary, #6b7280);
        }

        .answer-content {
          font-size: 0.9375rem;
          line-height: 1.6;
          white-space: pre-wrap;
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
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 6px;
          padding: 12px;
        }

        .source-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;
          font-size: 0.8125rem;
        }

        .source-name {
          font-weight: 500;
        }

        .source-page {
          margin-left: auto;
          color: var(--text-tertiary, #9ca3af);
          font-size: 0.75rem;
        }

        .source-snippet {
          font-size: 0.8125rem;
          color: var(--text-secondary, #6b7280);
          line-height: 1.5;
        }

        .context-content {
          font-size: 0.8125rem;
          line-height: 1.5;
          max-height: 300px;
          overflow-y: auto;
          white-space: pre-wrap;
          margin: 0;
          font-family: inherit;
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
          padding: 10px 12px;
          background: var(--bg-secondary, #f9fafb);
          border-radius: 6px;
          font-size: 0.875rem;
        }

        .file-name {
          flex: 1;
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
          padding: 4px;
          background: var(--bg-secondary, #f3f4f6);
          border-radius: 10px;
        }

        .tab-btn {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 20px;
          background: transparent;
          border: none;
          border-radius: 8px;
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--text-secondary, #6b7280);
          cursor: pointer;
          transition: all 0.2s;
          flex: 1;
          justify-content: center;
        }

        .tab-btn:hover {
          background: rgba(255, 255, 255, 0.5);
        }

        .tab-btn.active {
          background: white;
          color: var(--primary, #3b82f6);
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        /* Quiz Section */
        .quiz-section {
          background: var(--card-bg, #ffffff);
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 12px;
          padding: 20px;
        }

        .quiz-section h3 {
          display: flex;
          align-items: center;
          gap: 8px;
          margin: 0 0 16px 0;
          font-size: 1rem;
          font-weight: 600;
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

        .form-group label {
          font-size: 0.8125rem;
          font-weight: 500;
          color: var(--text-secondary, #6b7280);
        }

        .form-group input,
        .form-group select {
          padding: 10px 12px;
          border: 1px solid var(--border-color, #d1d5db);
          border-radius: 8px;
          font-size: 0.875rem;
          transition: border-color 0.2s, box-shadow 0.2s;
        }

        .form-group input:focus,
        .form-group select:focus {
          outline: none;
          border-color: var(--primary, #3b82f6);
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
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
          background: var(--bg-secondary, #f9fafb);
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 12px;
          padding: 20px;
          transition: border-color 0.2s;
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
          font-weight: 600;
          color: var(--primary, #3b82f6);
          font-size: 0.875rem;
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
          font-size: 0.9375rem;
          font-weight: 500;
          margin-bottom: 16px;
          line-height: 1.5;
          color: #111827;
        }

        .question-options {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .option-label {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          background: white;
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s;
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
          font-weight: 600;
          color: var(--primary, #3b82f6);
          min-width: 20px;
        }

        .option-value {
          font-size: 0.875rem;
          color: #374151;
        }

        .question-explanation {
          margin-top: 16px;
          padding: 12px;
          background: #fffbeb;
          border: 1px solid #fbbf24;
          border-radius: 8px;
          font-size: 0.8125rem;
          color: #92400e;
        }

        .quiz-actions {
          margin-top: 24px;
          display: flex;
          justify-content: center;
        }

        .quiz-actions .btn {
          min-width: 200px;
          justify-content: center;
        }
      `}</style>
    </div>
  );
};

export default DocumentRAGPanel;
