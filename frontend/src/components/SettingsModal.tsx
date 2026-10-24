import React, { useState } from "react";
import { getApiConfig, saveApiConfig } from "../api/client";
import { X, Key, Globe, Check } from "lucide-react";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose, onSaved }) => {
  if (!isOpen) return null;

  const current = getApiConfig();
  const [baseUrl, setBaseUrl] = useState(current.baseUrl);
  const [secretKey, setSecretKey] = useState(current.secretKey);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    saveApiConfig(baseUrl, secretKey);
    setSaved(true);
    setTimeout(() => {
      setSaved(false);
      onSaved();
      onClose();
    }, 600);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="card-glass"
        onClick={(e) => e.stopPropagation()}
        style={{ width: "100%", maxWidth: "460px", background: "#0a0a0a" }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <h3 style={{ margin: 0, fontSize: "16px" }}>API & Authentication Settings</h3>
          <button className="btn-ghost" onClick={onClose} style={{ padding: "4px 8px" }}>
            <X size={14} />
          </button>
        </div>

        <div style={{ marginBottom: "16px" }}>
          <label style={{ display: "block", fontSize: "12px", color: "var(--muted)", marginBottom: "6px" }}>
            Backend Base URL
          </label>
          <div style={{ position: "relative" }}>
            <Globe size={14} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "var(--muted)" }} />
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="/api/v1 or https://your-backend.onrender.com/api/v1"
              style={{
                width: "100%",
                padding: "8px 12px 8px 34px",
                background: "rgba(20, 20, 20, 0.8)",
                border: "1px solid var(--border)",
                borderRadius: "6px",
                color: "#ffffff",
                fontSize: "13px",
              }}
            />
          </div>
        </div>

        <div style={{ marginBottom: "24px" }}>
          <label style={{ display: "block", fontSize: "12px", color: "var(--muted)", marginBottom: "6px" }}>
            SECRET_KEY (Bearer Token)
          </label>
          <div style={{ position: "relative" }}>
            <Key size={14} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "var(--muted)" }} />
            <input
              type="password"
              value={secretKey}
              onChange={(e) => setSecretKey(e.target.value)}
              placeholder="Enter SECRET_KEY from server env..."
              style={{
                width: "100%",
                padding: "8px 12px 8px 34px",
                background: "rgba(20, 20, 20, 0.8)",
                border: "1px solid var(--border)",
                borderRadius: "6px",
                color: "#ffffff",
                fontSize: "13px",
              }}
            />
          </div>
        </div>

        <button className="btn-solid" onClick={handleSave} style={{ width: "100%", justifyContent: "center" }}>
          {saved ? <Check size={14} /> : null}
          <span>{saved ? "Saved" : "Save Settings"}</span>
        </button>
      </div>
    </div>
  );
};
