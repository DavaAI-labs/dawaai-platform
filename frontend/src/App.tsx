// src/App.tsx — v3
import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import AuthPage from "./pages/AuthPage";
import HomePage from "./pages/HomePage";
import ScanPage from "./pages/ScanPage";
import BarcodeScanPage from "./pages/BarcodeScanPage";
import ReviewPage from "./pages/ReviewPage";
import BillPage from "./pages/BillPage";
import InventoryPage from "./pages/InventoryPage";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { session, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!session) return <Navigate to="/auth" replace />;
  return <>{children}</>;
}

function LoadingScreen() {
  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#F0FBF7", fontFamily: "system-ui, sans-serif" }}>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>💊</div>
        <p style={{ color: "#1D9E75", fontWeight: 600, fontSize: 16 }}>DavaAI</p>
        <p style={{ color: "#888780", fontSize: 13 }}>Loading…</p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/" element={<PrivateRoute><HomePage /></PrivateRoute>} />
          <Route path="/scan" element={<PrivateRoute><ScanPage /></PrivateRoute>} />
          <Route path="/barcode" element={<PrivateRoute><BarcodeScanPage /></PrivateRoute>} />
          <Route path="/review" element={<PrivateRoute><ReviewPage /></PrivateRoute>} />
          <Route path="/bill" element={<PrivateRoute><BillPage /></PrivateRoute>} />
          <Route path="/inventory" element={<PrivateRoute><InventoryPage /></PrivateRoute>} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}