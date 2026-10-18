import React, { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import PageHeader from "../components/layout/PageHeader";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import MetricChip from "../components/ui/MetricChip";
import ProgressBar from "../components/ui/ProgressBar";
import Button from "../components/ui/Button";
import Spinner from "../components/ui/Spinner";
import EmptyState from "../components/ui/EmptyState";
import { useToast } from "../hooks/useToast";
import api from "../api/client";

export default function QuizView() {
  const { id } = useParams();
  const [quizData, setQuizData] = useState(null);
  const [userAnswers, setUserAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [biometrics, setBiometrics] = useState(null);
  const [adapting, setAdapting] = useState(false);
  const { showToast } = useToast();

  const fetchBiometrics = useCallback(async () => {
    try {
      const res = await api.get("/system/biometrics");
      setBiometrics(res.data);
    } catch (err) {
      console.error("Failed to fetch biometrics:", err);
    }
  }, []);

  const fetchQuiz = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get(`/lectures/${id}/quiz`);
      let parsed = res.data.questions;
      if (typeof parsed === "string") {
        parsed = JSON.parse(parsed);
      }
      setQuizData(parsed);
    } catch (err) {
      setError("Quiz paper is not ready or could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchQuiz();
    fetchBiometrics();
    const bioTimer = setInterval(fetchBiometrics, 3000);
    return () => clearInterval(bioTimer);
  }, [fetchQuiz, fetchBiometrics]);

  const handleSimulateState = async (state) => {
    try {
      await api.post("/system/biometrics/simulate", { state });
      showToast(`Biometric sensor mode switched to: ${state}`, "info");
      await fetchBiometrics();
    } catch (err) {
      console.error("Failed to switch sensor mode:", err);
      showToast("Failed to switch biometric sensor mode.", "error");
    }
  };

  const handleToggleCamera = async () => {
    const targetEnabled = biometrics?.ppg_state === "disabled";
    try {
      await api.post("/system/biometrics/camera", { enabled: targetEnabled });
      showToast(
        targetEnabled
          ? "Webcam rPPG reader enabled - allow a few seconds to warm up"
          : "Webcam rPPG reader disabled - emulated heart rate active",
        "info"
      );
      await fetchBiometrics();
    } catch (err) {
      console.error("Failed to toggle webcam reader:", err);
      showToast("Failed to toggle webcam rPPG reader.", "error");
    }
  };

  const handleAdaptQuiz = async (difficulty = null) => {
    setAdapting(true);
    try {
      const res = await api.post(`/lectures/${id}/quiz/adapt`, { difficulty });
      let parsed = res.data.quiz.questions;
      if (typeof parsed === "string") {
        parsed = JSON.parse(parsed);
      }
      setQuizData(parsed);
      setUserAnswers({});
      setSubmitted(false);
      showToast(
        `Quiz paper adapted to ${res.data.difficulty || "new"} difficulty based on cognitive load!`,
        "success"
      );
      await fetchBiometrics();
    } catch (err) {
      console.error("Failed to adapt quiz:", err);
      showToast("Failed to adapt quiz paper. Please ensure LM Studio is running.", "error");
    } finally {
      setAdapting(false);
    }
  };

  const handleSelectOption = (qIdx, option) => {
    if (submitted) return;
    setUserAnswers((prev) => ({ ...prev, [qIdx]: option }));
  };

  const handleRetake = () => {
    setUserAnswers({});
    setSubmitted(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
    showToast("Quiz reset. Good luck on your next attempt!", "info");
  };

  const calculateScore = () => {
    if (!quizData?.questions) return 0;
    let score = 0;
    quizData.questions.forEach((q, idx) => {
      if (userAnswers[idx] === q.correct_answer) {
        score += 1;
      }
    });
    return score;
  };

  if (loading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-center">
        <Spinner size="lg" className="mb-4" />
        <h3 className="text-base font-semibold text-slate-800">Generating adaptive practice quiz...</h3>
        <p className="text-xs text-slate-400 mt-1">Retrieving questions tailored to cognitive load</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-12">
        <EmptyState
          title="Quiz Not Available"
          description={error}
          actionText="Back to Notes"
          onAction={() => window.location.href = `/lectures/${id}`}
        />
      </div>
    );
  }

  const questions = quizData?.questions || [];
  const currentDiff = quizData?.difficulty || "medium";
  const score = calculateScore();
  const percentage = questions.length > 0 ? Math.round((score / questions.length) * 100) : 0;
  const isHighStress = biometrics?.stress_index_pct > 65;
  const isLowStress = biometrics?.stress_index_pct < 35;
  const ppgLive = biometrics?.heart_rate_source === "webcam_rppg";
  const ppgState = biometrics?.ppg_state;
  const ppgWarming = ppgState === "starting" || ppgState === "warming_up";
  const cameraUnavailable = ppgState === "no_camera";
  const cameraOff = ppgState === "disabled";

  return (
    <div className="max-w-4xl mx-auto space-y-6 sm:space-y-8">
      {/* Page Header */}
      <PageHeader
        breadcrumbs={[
          { to: "/", label: "Dashboard" },
          { to: `/lectures/${id}`, label: `Lecture #${id}` },
          { label: "Adaptive Quiz" },
        ]}
        title="Interactive Practice Quiz"
        subtitle="Questions dynamically generated from the lecture transcript. Cognitive stress telemetry adapts question complexity."
        badge={
          <Badge
            variant={
              currentDiff === "hard"
                ? "purple"
                : currentDiff === "easy"
                ? "success"
                : "brand"
            }
            size="sm"
          >
            Level: {currentDiff.toUpperCase()}
          </Badge>
        }
        actions={
          <Link to={`/lectures/${id}`}>
            <Button variant="outline" size="sm">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Notes
            </Button>
          </Link>
        }
      />

      {/* Biometric Cognitive Load & Stress Adaptation Banner (Option #3) */}
      {biometrics && (
        <Card
          variant="default"
          padding="md"
          className={`border-2 transition-all duration-300 ${
            isHighStress
              ? "border-rose-300 bg-rose-50/40"
              : isLowStress
              ? "border-emerald-300 bg-emerald-50/40"
              : "border-indigo-100 bg-gradient-to-r from-white via-indigo-50/20 to-slate-50"
          }`}
        >
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xl">🧠</span>
                <h3 className="font-bold text-slate-900 text-sm tracking-wide">
                  Biometric Cognitive Load & Stress Adaptation (Option #3)
                </h3>
                <Badge
                  variant={isHighStress ? "danger" : isLowStress ? "success" : "info"}
                  size="xs"
                  dot
                  pulse={isHighStress}
                >
                  {biometrics.stress_level_label || "Optimal Focus"}
                </Badge>
              </div>

              <p className="text-xs text-slate-500 leading-relaxed max-w-xl">
                Streaming PPG (heart rate), GSR (skin conductance), and EEG spectral waves steer question paper difficulty. Heart rate is measured live from the webcam via rPPG in Live mode; GSR and EEG channels come from the built-in sensor emulator.
              </p>

              {/* Stress Gauge Bar */}
              <div className="max-w-md pt-1">
                <ProgressBar
                  value={biometrics.stress_index_pct || 40}
                  min={0}
                  max={100}
                  variant={isHighStress ? "danger" : isLowStress ? "success" : "brand"}
                  showLabels
                  labelMin="0% Calm"
                  labelMid={`Stress: ${biometrics.stress_index_pct}% • ${biometrics.adaptation_action || ""}`}
                  labelMax="100% High"
                />
              </div>
            </div>

            {/* Metrics & Simulation Controls */}
            <div className="flex flex-col items-start lg:items-end gap-2.5 shrink-0">
              <div className="flex flex-wrap items-center gap-1.5">
                <MetricChip
                  label="PPG HR"
                  value={biometrics.heart_rate_bpm ?? "--"}
                  unit="BPM"
                  variant="danger"
                  size="sm"
                />
                <Badge
                  variant={ppgLive ? "success" : ppgWarming ? "info" : "neutral"}
                  size="xs"
                  dot
                  pulse={ppgLive}
                >
                  {ppgLive
                    ? "LIVE WEBCAM"
                    : ppgWarming
                    ? "CAMERA WARMING UP"
                    : ppgState === "no_face"
                    ? "NO FACE DETECTED"
                    : "EMULATED"}
                </Badge>
                <MetricChip
                  label="GSR"
                  value={biometrics.gsr_microsiemens ?? "--"}
                  unit="µS"
                  variant="warning"
                  size="sm"
                />
                <MetricChip
                  label="EEG β/α"
                  value={(biometrics.eeg_beta_ratio / (biometrics.eeg_alpha_ratio || 1)).toFixed(2)}
                  variant="brand"
                  size="sm"
                />
              </div>

              {/* Sensor Mode & Camera Controls */}
              <div className="flex items-center gap-1.5 flex-wrap pt-1">
                <span className="text-[11px] text-slate-400 font-medium mr-1">Sensors:</span>
                <Button
                  variant={biometrics.simulated_state === "LIVE" ? "success" : "secondary"}
                  size="xs"
                  onClick={() => handleSimulateState("LIVE")}
                  title="Use the real webcam heart-rate reading (GSR/EEG remain emulated)"
                >
                  📷 Live
                </Button>
                <Button
                  variant={biometrics.simulated_state === "LOW_STRESS" ? "success" : "secondary"}
                  size="xs"
                  onClick={() => handleSimulateState("LOW_STRESS")}
                >
                  😌 Low Stress
                </Button>
                <Button
                  variant={biometrics.simulated_state === "NORMAL" ? "primary" : "secondary"}
                  size="xs"
                  onClick={() => handleSimulateState("NORMAL")}
                >
                  😐 Moderate
                </Button>
                <Button
                  variant={biometrics.simulated_state === "HIGH_STRESS" ? "danger" : "secondary"}
                  size="xs"
                  onClick={() => handleSimulateState("HIGH_STRESS")}
                >
                  😰 High Stress
                </Button>

                <Button
                  variant="secondary"
                  size="xs"
                  onClick={handleToggleCamera}
                  disabled={cameraUnavailable}
                  title="Webcam rPPG reader switch — frames are processed in memory and never stored"
                >
                  {cameraUnavailable ? "📷 No Camera" : cameraOff ? "📷 Camera Off" : "📷 Camera On"}
                </Button>

                <Button
                  variant="primary"
                  size="xs"
                  loading={adapting}
                  onClick={() => handleAdaptQuiz()}
                  className="ml-1"
                >
                  ⚡ Adapt Paper
                </Button>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Post-Submission Score Summary Card */}
      {submitted && (
        <Card
          variant="raised"
          padding="lg"
          className={`border-2 animate-in zoom-in-95 duration-200 text-center ${
            percentage >= 70
              ? "bg-emerald-50/60 border-emerald-300"
              : percentage >= 50
              ? "bg-amber-50/60 border-amber-300"
              : "bg-rose-50/60 border-rose-300"
          }`}
        >
          <div className="max-w-md mx-auto">
            <span className="text-3xl mb-2 inline-block">
              {percentage >= 80 ? "🏆" : percentage >= 50 ? "👍" : "📚"}
            </span>
            <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
              You Scored {score} out of {questions.length} ({percentage}%)
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 mt-1">
              {percentage >= 80
                ? "Outstanding comprehension! You've mastered the core concepts."
                : percentage >= 50
                ? "Solid effort! Review the detailed explanations below to cement your understanding."
                : "Good practice run! Review the notes and retake the quiz to improve your score."}
            </p>

            <div className="flex items-center justify-center gap-3 mt-5">
              <Button variant="primary" size="sm" onClick={handleRetake}>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Retake Quiz
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleAdaptQuiz()}>
                ⚡ Adapt to Current Stress
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Question Cards List */}
      <div className="space-y-5">
        {questions.map((q, qIdx) => {
          const isAnswered = userAnswers[qIdx] !== undefined;
          const isCorrect = userAnswers[qIdx] === q.correct_answer;

          return (
            <Card key={qIdx} variant="default" padding="lg" className="bg-white">
              <div className="flex items-start justify-between gap-3 mb-4">
                <span className="text-xs font-bold text-indigo-600 uppercase tracking-wider">
                  Question {qIdx + 1} of {questions.length}
                </span>
                {q.difficulty && (
                  <Badge variant="neutral" size="xs">
                    {q.difficulty}
                  </Badge>
                )}
              </div>

              <h3 className="text-base sm:text-lg font-bold text-slate-900 leading-snug mb-4">
                {q.question}
              </h3>

              {/* Selectable Options */}
              <div className="space-y-2.5">
                {q.options?.map((opt, optIdx) => {
                  const letter = String.fromCharCode(65 + optIdx);
                  const isSelected = userAnswers[qIdx] === opt;
                  const isCorrectAnswer = opt === q.correct_answer;

                  let optionStyle =
                    "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-800";
                  let letterStyle = "bg-slate-100 text-slate-700 border-slate-200";

                  if (submitted) {
                    if (isCorrectAnswer) {
                      optionStyle = "bg-emerald-50 border-emerald-400 text-emerald-950 font-semibold";
                      letterStyle = "bg-emerald-600 text-white border-emerald-600";
                    } else if (isSelected && !isCorrect) {
                      optionStyle = "bg-rose-50 border-rose-400 text-rose-950 line-through";
                      letterStyle = "bg-rose-600 text-white border-rose-600";
                    } else {
                      optionStyle = "bg-slate-50/60 border-slate-200/60 text-slate-400 opacity-70";
                      letterStyle = "bg-slate-100 text-slate-400 border-slate-200";
                    }
                  } else if (isSelected) {
                    optionStyle =
                      "bg-indigo-50 border-indigo-500 text-indigo-950 font-semibold ring-2 ring-indigo-500/20";
                    letterStyle = "bg-indigo-600 text-white border-indigo-600";
                  }

                  return (
                    <button
                      key={optIdx}
                      type="button"
                      disabled={submitted}
                      onClick={() => handleSelectOption(qIdx, opt)}
                      className={`w-full text-left p-3.5 sm:p-4 rounded-xl border transition-all duration-150 text-xs sm:text-sm flex items-center gap-3.5 cursor-pointer disabled:cursor-default ${optionStyle}`}
                    >
                      <span
                        className={`w-7 h-7 flex items-center justify-center rounded-lg border text-xs font-bold shrink-0 transition-colors ${letterStyle}`}
                      >
                        {letter}
                      </span>
                      <span className="flex-1 leading-relaxed">{opt}</span>
                      {submitted && isCorrectAnswer && (
                        <svg className="w-5 h-5 text-emerald-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                      {submitted && isSelected && !isCorrect && (
                        <svg className="w-5 h-5 text-rose-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Answer Explanation */}
              {submitted && q.explanation && (
                <div className="mt-4 p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs sm:text-sm text-slate-700 space-y-1 animate-in fade-in duration-200">
                  <div className="flex items-center gap-1.5 font-bold text-slate-900">
                    <svg className="w-4 h-4 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Explanation
                  </div>
                  <p className="leading-relaxed pl-5.5 text-slate-600">{q.explanation}</p>
                </div>
              )}
            </Card>
          );
        })}
      </div>

      {/* Bottom Submit Action */}
      {!submitted && questions.length > 0 && (
        <div className="text-center pt-4 pb-8">
          <Button
            variant="primary"
            size="lg"
            onClick={() => {
              const answeredCount = Object.keys(userAnswers).length;
              if (answeredCount < questions.length) {
                if (
                  !window.confirm(
                    `You have only answered ${answeredCount} of ${questions.length} questions. Submit anyway?`
                  )
                ) {
                  return;
                }
              }
              setSubmitted(true);
              window.scrollTo({ top: 0, behavior: "smooth" });
              showToast("Quiz submitted! Scroll through your detailed results.", "success");
            }}
            className="shadow-lg shadow-indigo-600/30 px-8"
          >
            Submit Quiz
          </Button>
        </div>
      )}
    </div>
  );
}
