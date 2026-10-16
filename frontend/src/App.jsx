import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import AppShell from "./components/layout/AppShell";
import { ToastProvider } from "./context/ToastContext";
import Dashboard from "./pages/Dashboard";
import LectureView from "./pages/LectureView";
import QuizView from "./pages/QuizView";

export default function App() {
  return (
    <ToastProvider>
      <Router>
        <AppShell>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/lectures/:id" element={<LectureView />} />
            <Route path="/lectures/:id/quiz" element={<QuizView />} />
          </Routes>
        </AppShell>
      </Router>
    </ToastProvider>
  );
}
