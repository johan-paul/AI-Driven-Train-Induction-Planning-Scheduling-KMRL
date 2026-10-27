// src/App.jsx
import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";

// Pages
import LoginPage from "./pages/LoginPage";
import ConfigPage from "./pages/ConfigPage";
import DashboardPage from "./pages/DashboardPage";

// (optional) global components are imported inside pages as needed

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route path="/config" element={<ConfigPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Router>
  );
}

export default App;
