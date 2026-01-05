import { useState } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Sidebar, ChatPanel, UploadPanel, QuizPanel, GradingPanel, SettingsPanel } from './components';
import { Loader2 } from 'lucide-react';
import { TABS, type TabType } from './types';
import './App.css';

const AppContent: React.FC = () => {
  const { loading } = useApp();
  const [activeTab, setActiveTab] = useState<TabType>(TABS.CHAT);

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
      case TABS.CHAT:
        return <ChatPanel />;
      case TABS.UPLOAD:
        return <UploadPanel />;
      case TABS.QUIZ:
        return <QuizPanel />;
      case TABS.GRADING:
        return <GradingPanel />;
      case TABS.SETTINGS:
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
