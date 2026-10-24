import React from "react";
import { Search } from "lucide-react";

interface CaseFiltersProps {
  search: string;
  onSearchChange: (val: string) => void;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
}

const STATUS_OPTIONS = [
  { label: "All Cases", value: "" },
  { label: "Complete", value: "COMPLETE" },
  { label: "Incomplete", value: "INCOMPLETE" },
  { label: "Not Applicable", value: "NOT_APPLICABLE" },
];

export const CaseFilters: React.FC<CaseFiltersProps> = ({
  search,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
}) => {
  return (
    <div style={{
      display: "flex",
      flexWrap: "wrap",
      alignItems: "center",
      justifyContent: "space-between",
      gap: "16px",
      marginBottom: "20px",
    }}>
      <div style={{
        position: "relative",
        maxWidth: "360px",
        width: "100%",
      }}>
        <Search
          size={16}
          style={{
            position: "absolute",
            left: "14px",
            top: "50%",
            transform: "translateY(-50%)",
            color: "var(--muted)",
          }}
        />
        <input
          type="text"
          placeholder="Search case ID or email..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          style={{
            width: "100%",
            padding: "10px 14px 10px 38px",
            background: "rgba(18, 18, 18, 0.8)",
            border: "1px solid var(--border)",
            borderRadius: "7px",
            color: "#ffffff",
            fontSize: "13.5px",
            outline: "none",
          }}
        />
      </div>

      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
        {STATUS_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            className={`liquid-pill ${statusFilter === opt.value ? "active" : ""}`}
            onClick={() => onStatusFilterChange(opt.value)}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
};
