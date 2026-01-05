import React, { useState, useEffect } from 'react';
import { quizApi } from '../api/quiz';
import { BookOpen, FileText, Loader2, ExternalLink, Trash2, RefreshCw } from 'lucide-react';
import type { QuizListItem } from '../types';

const QuizPanel: React.FC = () => {
  const [numQuestions, setNumQuestions] = useState(10);
  const [generating, setGenerating] = useState(false);
  const [quizzes, setQuizzes] = useState<QuizListItem[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string; url?: string } | null>(
    null
  );

  useEffect(() => {
    loadQuizzes();
  }, []);

  const loadQuizzes = async () => {
    setLoadingList(true);
    try {
      const response = await quizApi.getQuizList();
      setQuizzes(response.quizzes);
    } catch (error) {
      console.error('Failed to load quizzes:', error);
    } finally {
      setLoadingList(false);
    }
  };

  const generateQuiz = async () => {
    setGenerating(true);
    setResult(null);
    try {
      const response = await quizApi.generateQuiz({ num_questions: numQuestions });
      setResult({
        success: response.success,
        message: response.message,
        url: response.file_url,
      });
      if (response.success) {
        loadQuizzes();
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Lỗi khi tạo quiz';
      setResult({
        success: false,
        message: errorMessage,
      });
    } finally {
      setGenerating(false);
    }
  };

  const deleteQuiz = async (quizId: string) => {
    if (!confirm('Bạn có chắc muốn xóa quiz này?')) return;
    
    try {
      await quizApi.deleteQuiz(quizId);
      loadQuizzes();
    } catch (error) {
      console.error('Failed to delete quiz:', error);
    }
  };

  const openQuiz = (url: string) => {
    window.open(`http://localhost:8000${url}`, '_blank');
  };

  return (
    <div className="quiz-panel">
      <h2>
        <BookOpen size={24} />
        Tạo Quiz từ Đề thi
      </h2>

      <div className="quiz-generator">
        <div className="form-group">
          <label>Số câu hỏi:</label>
          <div className="input-with-buttons">
            <button onClick={() => setNumQuestions(Math.max(5, numQuestions - 5))}>-5</button>
            <input
              type="number"
              value={numQuestions}
              onChange={(e) => setNumQuestions(parseInt(e.target.value) || 10)}
              min={5}
              max={30}
            />
            <button onClick={() => setNumQuestions(Math.min(30, numQuestions + 5))}>+5</button>
          </div>
        </div>

        <button
          className="btn-primary btn-large"
          onClick={generateQuiz}
          disabled={generating}
        >
          {generating ? (
            <>
              <Loader2 className="spin" size={20} />
              Đang tạo quiz...
            </>
          ) : (
            <>
              <FileText size={20} />
              Tạo Quiz
            </>
          )}
        </button>

        {result && (
          <div className={`result-message ${result.success ? 'success' : 'error'}`}>
            <p>{result.message}</p>
            {result.success && result.url && (
              <button className="btn-link" onClick={() => openQuiz(result.url!)}>
                <ExternalLink size={16} />
                Mở Quiz
              </button>
            )}
          </div>
        )}
      </div>

      <div className="quiz-list">
        <div className="quiz-list-header">
          <h3>Danh sách Quiz đã tạo</h3>
          <button className="btn-icon" onClick={loadQuizzes} disabled={loadingList}>
            <RefreshCw size={18} className={loadingList ? 'spin' : ''} />
          </button>
        </div>

        {loadingList ? (
          <div className="loading-center">
            <Loader2 className="spin" size={24} />
          </div>
        ) : quizzes.length === 0 ? (
          <p className="empty-message">Chưa có quiz nào được tạo</p>
        ) : (
          <table className="quiz-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Thời gian</th>
                <th>Số câu</th>
                <th>Nguồn</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {quizzes.map((quiz) => (
                <tr key={quiz.id}>
                  <td>{quiz.id}</td>
                  <td>{quiz.timestamp}</td>
                  <td>{quiz.num_questions}</td>
                  <td>{quiz.source_pdf || '-'}</td>
                  <td>
                    <button
                      className="btn-icon"
                      onClick={() => openQuiz(`/static/quizzes/${quiz.id}.html`)}
                      title="Mở quiz"
                    >
                      <ExternalLink size={16} />
                    </button>
                    <button
                      className="btn-icon danger"
                      onClick={() => deleteQuiz(quiz.id)}
                      title="Xóa quiz"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default QuizPanel;
