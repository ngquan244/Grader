import React from 'react';
import { useApp } from '../context/AppContext';
import { Settings, Bot, Cpu, RotateCcw } from 'lucide-react';

const SettingsPanel: React.FC = () => {
  const { config, model, setModel, maxIterations, setMaxIterations, role, switchRole } = useApp();

  const handleSwitchRole = async () => {
    try {
      await switchRole();
    } catch (error) {
      console.error('Failed to switch role:', error);
    }
  };

  return (
    <div className="settings-panel">
      <h2>
        <Settings size={24} />
        Cài đặt
      </h2>

      <div className="settings-section">
        <h3>
          <Bot size={20} />
          Vai trò người dùng
        </h3>
        <div className="role-selector">
          <div className={`role-option ${role === 'STUDENT' ? 'active' : ''}`}>
            <span>Sinh viên</span>
          </div>
          <button className="btn-switch" onClick={handleSwitchRole}>
            <RotateCcw size={16} />
          </button>
          <div className={`role-option ${role === 'TEACHER' ? 'active' : ''}`}>
            <span>Giáo viên</span>
          </div>
        </div>
        <p className="hint">
          {role === 'TEACHER'
            ? 'Bạn có quyền truy cập tất cả tính năng'
            : 'Một số tính năng bị giới hạn cho sinh viên'}
        </p>
      </div>

      <div className="settings-section">
        <h3>
          <Cpu size={20} />
          Model AI
        </h3>
        <div className="form-group">
          <label>Chọn model:</label>
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            {config?.available_models.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Số vòng lặp tối đa:</label>
          <input
            type="range"
            min={5}
            max={20}
            value={maxIterations}
            onChange={(e) => setMaxIterations(parseInt(e.target.value))}
          />
          <span className="range-value">{maxIterations}</span>
        </div>
      </div>

      <div className="settings-section">
        <h3>Thông tin hệ thống</h3>
        <div className="info-list">
          <div className="info-item">
            <span>API URL:</span>
            <code>http://localhost:8000</code>
          </div>
          <div className="info-item">
            <span>Model mặc định:</span>
            <code>{config?.default_model}</code>
          </div>
          <div className="info-item">
            <span>Phiên bản:</span>
            <code>1.0.0</code>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;
