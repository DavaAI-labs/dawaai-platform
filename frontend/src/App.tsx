// App.tsx — upgraded routing with Home, Scan (OCR), Barcode, Review, Bill
import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import HomePage from "./pages/HomePage";
import ScanPage from "./pages/ScanPage";
import BarcodeScanPage from "./pages/BarcodeScanPage";
import ReviewPage from "./pages/ReviewPage";
import BillPage from "./pages/BillPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/scan" element={<ScanPage />} />
        <Route path="/barcode" element={<BarcodeScanPage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/bill" element={<BillPage />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}