import { useState } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Sidebar, ChatPanel, UploadPanel, QuizPanel, GradingPanel, SettingsPanel } from './components';
import { Loader2 } from 'lucide-react';
import './App.css';

const AppContent: React.FC = () => {
  const { loading } = useApp();
  const [activeTab, setActiveTab] = useState('chat');

  if (loading) {
    return (
      <div className="loading-screen">
        <Loader2 className="spin" size={48} />
        <p>Đang tải...</p>
      </div>
    );
  }

  const renderContent = () => {
    switch (activeTab) {
      case 'chat':
        return <ChatPanel />;
      case 'upload':
        return <UploadPanel />;
      case 'quiz':
        return <QuizPanel />;
      case 'grading':
        return <GradingPanel />;
      case 'settings':
        return <SettingsPanel />;
      default:
        return <ChatPanel />;
    }
  };

  return (
    <div className="app">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="main-content">{renderContent()}</main>
    </div>
  );
};

function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}

export default App;
