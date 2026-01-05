import React from 'react';
import { useApp } from '../context/AppContext';
import { MessageSquare, FileUp, BookOpen, BarChart3, Settings, GraduationCap, User } from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  const { role, switchRole } = useApp();

  const tabs = [
    { id: 'chat', label: 'Chat AI', icon: MessageSquare },
    { id: 'upload', label: 'Upload', icon: FileUp },
    { id: 'quiz', label: 'Tạo Quiz', icon: BookOpen, teacherOnly: true },
    { id: 'grading', label: 'Chấm điểm', icon: BarChart3, teacherOnly: true },
    { id: 'settings', label: 'Cài đặt', icon: Settings },
  ];

  const handleRoleSwitch = async () => {
    try {
      await switchRole();
    } catch (error) {
      console.error('Failed to switch role:', error);
    }
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <GraduationCap size={32} />
        <h1>TA Grader</h1>
      </div>

      <div className="role-badge" onClick={handleRoleSwitch}>
        {role === 'TEACHER' ? <GraduationCap size={18} /> : <User size={18} />}
        <span>{role === 'TEACHER' ? 'Giáo viên' : 'Sinh viên'}</span>
        <span className="role-switch-hint">Click để đổi</span>
      </div>

      <nav className="sidebar-nav">
        {tabs.map((tab) => {
          if (tab.teacherOnly && role !== 'TEACHER') return null;
          
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={`nav-item ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => onTabChange(tab.id)}
            >
              <Icon size={20} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <p>Teaching Assistant</p>
        <p className="version">v1.0.0</p>
      </div>
    </div>
  );
};

export default Sidebar;
