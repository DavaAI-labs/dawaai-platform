// ConfidenceBadge.tsx
// Shows pharmacist how much to trust each OCR suggestion.
// Green = safe to tap confirm. Yellow = glance at it. Red = must verify.
// This single component is what builds pharmacist trust in the app.

import React from "react";

interface Props {
  label: "high" | "medium" | "low";
  score?: number;   // optional numeric score to show
  size?: "sm" | "md";
}

const config = {
  high: {
    emoji: "🟢",
    text: "High confidence",
    short: "High",
    bg: "#EAF3DE",
    color: "#3B6D11",
    border: "#9CC96B",
  },
  medium: {
    emoji: "🟡",
    text: "Check this",
    short: "Check",
    bg: "#FAEEDA",
    color: "#854F0B",
    border: "#F0B866",
  },
  low: {
    emoji: "🔴",
    text: "Verify manually",
    short: "Verify",
    bg: "#FCEBEB",
    color: "#A32D2D",
    border: "#F0A0A0",
  },
};

export default function ConfidenceBadge({ label, score, size = "md" }: Props) {
  const c = config[label];
  const isSmall = size === "sm";

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: isSmall ? 3 : 5,
        background: c.bg,
        color: c.color,
        border: `1px solid ${c.border}`,
        borderRadius: 20,
        padding: isSmall ? "2px 8px" : "3px 10px",
        fontSize: isSmall ? 11 : 12,
        fontWeight: 500,
        whiteSpace: "nowrap",
        fontFamily: "var(--font-sans, system-ui)",
      }}
      title={c.text}
      aria-label={`Confidence: ${c.text}${score ? ` (${score}%)` : ""}`}
    >
      <span aria-hidden="true">{c.emoji}</span>
      {isSmall ? c.short : c.text}
      {score !== undefined && (
        <span style={{ opacity: 0.7, fontSize: isSmall ? 10 : 11 }}>
          {score}%
        </span>
      )}
    </span>
  );
}