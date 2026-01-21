import React from 'react';
import { useApp } from '../context/AppContext';
import { Settings, Cpu } from 'lucide-react';

const SettingsPanel: React.FC = () => {
  const { config, model, setModel, maxIterations, setMaxIterations } = useApp();

  return (
    <div className="settings-panel">
      <h2>
        <Settings size={24} />
        Cài đặt
      </h2>

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
