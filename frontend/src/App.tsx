import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { IngestBar } from './components/IngestBar';
import { PipelineStepper } from './components/PipelineStepper';
import { GroundingInspector } from './components/GroundingInspector';
import { InterviewCard } from './components/InterviewCard';
import { VerdictCard } from './components/VerdictCard';
import { VoicePlayer } from './components/VoicePlayer';
import { ActionChecklist } from './components/ActionChecklist';
import {
  AudienceType,
  PipelineStatus,
  TraceStep,
  VerifiedSource,
} from './types';
import {
  fetchVerifiedSources,
  startPipeline,
  getPipelineStatus,
  submitAnswers,
  subscribePipelineEvents,
} from './api';
import { AlertCircle, RotateCcw } from 'lucide-react';

export const App: React.FC = () => {
  const [persona, setPersona] = useState<AudienceType>('citizen');
  const [language, setLanguage] = useState<string>('hi');
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean>(false);
  const [verifiedSources, setVerifiedSources] = useState<VerifiedSource[]>([]);

  // Pipeline execution state
  const [runId, setRunId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSubmittingAnswers, setIsSubmittingAnswers] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>({
    run_id: '',
    status: 'started',
    trace: [],
  });

  // Check health and load sources on mount
  useEffect(() => {
    fetch('/health')
      .then((res) => res.json())
      .then(() => setIsBackendHealthy(true))
      .catch(() => setIsBackendHealthy(false));

    fetchVerifiedSources()
      .then((sources) => setVerifiedSources(sources))
      .catch((err) => console.warn('Could not load verified sources', err));
  }, []);

  // Poll fallback / snapshot fetcher
  const refreshStatus = async (id: string) => {
    try {
      const snap = await getPipelineStatus(id);
      setPipelineStatus((prev) => ({
        ...prev,
        ...snap,
      }));
    } catch (e) {
      console.warn('Failed to fetch status snapshot', e);
    }
  };

  const handleStart = async (file: File | null, url: string | null) => {
    setIsLoading(true);
    setErrorMessage(null);
    setPipelineStatus({
      run_id: '',
      status: 'running',
      trace: [],
    });

    try {
      const res = await startPipeline(file, url, persona, language);
      setRunId(res.run_id);

      // Subscribe to real-time Server-Sent Events (SSE)
      const unsubscribe = subscribePipelineEvents(
        res.run_id,
        (eventData) => {
          console.log('[SSE Event]', eventData);

          if (eventData.type === 'step_complete') {
            setPipelineStatus((prev) => {
              const existingTrace = prev.trace || [];
              const updatedTrace: TraceStep[] = [
                ...existingTrace.filter((t) => t.node !== eventData.node),
                {
                  node: eventData.node,
                  status: 'ok',
                  latency_ms: eventData.latency_ms,
                },
              ];
              return {
                ...prev,
                current_node: eventData.node,
                trace: updatedTrace,
              };
            });
            // Fetch updated state when scheme or intermediate data is extracted
            refreshStatus(res.run_id);
          }

          if (eventData.type === 'interview_required') {
            setIsLoading(false);
            setPipelineStatus((prev) => ({
              ...prev,
              status: 'waiting_for_answers',
              questions: eventData.questions,
            }));
            refreshStatus(res.run_id);
          }

          if (eventData.type === 'pipeline_complete') {
            setIsLoading(false);
            refreshStatus(res.run_id);
          }

          if (eventData.type === 'pipeline_error') {
            setIsLoading(false);
            setErrorMessage(eventData.error || 'A processing error occurred');
          }
        },
        (err) => {
          console.warn('SSE stream disconnected, falling back to snapshot poll', err);
          refreshStatus(res.run_id);
        }
      );

      // Initial snapshot fetch after 1.5 seconds
      setTimeout(() => refreshStatus(res.run_id), 1500);

      return () => unsubscribe();
    } catch (err: any) {
      setIsLoading(false);
      setErrorMessage(err.message || 'Failed to start pipeline');
    }
  };

  const handleSubmitInterview = async (
    answers: Record<string, any>,
    units: Record<string, string>
  ) => {
    if (!runId) return;
    setIsSubmittingAnswers(true);
    setErrorMessage(null);

    try {
      await submitAnswers(runId, answers, units);
      setIsSubmittingAnswers(false);
      setIsLoading(true);

      // Fetch the updated snapshot
      setTimeout(async () => {
        await refreshStatus(runId);
        setIsLoading(false);
      }, 2000);
    } catch (err: any) {
      setIsSubmittingAnswers(false);
      setIsLoading(false);
      setErrorMessage(err.message || 'Failed to submit answers');
    }
  };

  const handleReset = () => {
    setRunId(null);
    setIsLoading(false);
    setErrorMessage(null);
    setPipelineStatus({
      run_id: '',
      status: 'started',
      trace: [],
    });
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {/* Top Navigation */}
      <Navbar
        persona={persona}
        setPersona={setPersona}
        language={language}
        setLanguage={setLanguage}
        isBackendHealthy={isBackendHealthy}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Ingestion & Upload Zone */}
        <IngestBar
          onStart={handleStart}
          isLoading={isLoading}
          verifiedSources={verifiedSources}
        />

        {/* Error Banner */}
        {errorMessage && (
          <div className="mb-6 p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-start justify-between text-rose-800 text-sm shadow-sm">
            <div className="flex items-center space-x-2.5">
              <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
              <div>
                <p className="font-bold">Execution Error</p>
                <p className="text-xs text-rose-700">{errorMessage}</p>
              </div>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-xs underline font-medium hover:text-rose-950"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Real-Time Stepper (If pipeline has started) */}
        {runId && (
          <div className="relative">
            <PipelineStepper
              currentNode={pipelineStatus.current_node}
              trace={pipelineStatus.trace || []}
              status={pipelineStatus.status}
              confidence={pipelineStatus.scheme?.confidence}
            />
            <button
              onClick={handleReset}
              className="absolute top-4 right-4 text-xs text-slate-400 hover:text-slate-700 flex items-center space-x-1 transition"
              title="Reset Analysis"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">New Scheme</span>
            </button>
          </div>
        )}

        {/* Split-View Cockpit (2-Column Layout) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column (5 Cols): Legal Grounding Inspector */}
          <div className="lg:col-span-5">
            <GroundingInspector scheme={pipelineStatus.scheme} />
          </div>

          {/* Right Column (7 Cols): Dynamic Interview & Verdict Cards */}
          <div className="lg:col-span-7 space-y-6">
            {/* Dynamic Interview Card (Human-in-the-Loop) */}
            {pipelineStatus.status === 'waiting_for_answers' &&
              pipelineStatus.questions &&
              pipelineStatus.questions.length > 0 && (
                <InterviewCard
                  questions={pipelineStatus.questions}
                  onSubmit={handleSubmitInterview}
                  isSubmitting={isSubmittingAnswers}
                  language={language}
                />
              )}

            {/* Verdict Headline Card */}
            {pipelineStatus.verdict && (
              <VerdictCard verdict={pipelineStatus.verdict} />
            )}

            {/* Regional Voice Player */}
            {pipelineStatus.explainer && (
              <VoicePlayer explainer={pipelineStatus.explainer} />
            )}

            {/* Action Checklist */}
            {(pipelineStatus.explainer || pipelineStatus.scheme) && (
              <ActionChecklist
                explainer={pipelineStatus.explainer}
                scheme={pipelineStatus.scheme}
              />
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 mt-12 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p>© 2026 CivicFlow — Deterministic AI Policy & Welfare Intelligence</p>
          <p className="text-slate-400">
            Powered by LangGraph • Google Gemini 3 Flash • Edge-TTS • Pure Python Engine
          </p>
        </div>
      </footer>
    </div>
  );
};

