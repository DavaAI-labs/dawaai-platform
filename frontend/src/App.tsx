// App.tsx
// Routing between the 3 screens: Scan → Review → Bill
// Uses React Router v6.

import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import ScanPage from "./pages/ScanPage";
import ReviewPage from "./pages/ReviewPage";
import BillPage from "./pages/BillPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"       element={<ScanPage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/bill"   element={<BillPage />} />
        <Route path="*"       element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}