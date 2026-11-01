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
  switchLanguage,
} from './api';
import { AlertCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [persona, setPersona] = useState<AudienceType>('citizen');
  const [language, setLanguage] = useState<string>('hi');
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean>(false);
  const [verifiedSources, setVerifiedSources] = useState<VerifiedSource[]>([]);

  // Pipeline execution state
  const [runId, setRunId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSubmittingAnswers, setIsSubmittingAnswers] = useState<boolean>(false);
  const [isSwitchingLanguage, setIsSwitchingLanguage] = useState<boolean>(false);
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
      const isWaiting =
        snap.status === 'waiting_for_answers' ||
        (snap as any).is_paused ||
        (snap.questions && snap.questions.length > 0 && !snap.verdict);

      setPipelineStatus((prev) => ({
        ...prev,
        ...snap,
        status: isWaiting ? 'waiting_for_answers' : (snap.verdict ? 'completed' : snap.status || prev.status),
        questions: (snap.questions && snap.questions.length > 0) ? snap.questions : prev.questions,
      }));

      if (isWaiting || snap.verdict || snap.error) {
        setIsLoading(false);
      }
    } catch (e) {
      console.warn('Failed to fetch status snapshot', e);
    }
  };

  // Dynamic live language switcher without page reload
  const handleLanguageChange = async (newLang: string) => {
    setLanguage(newLang);

    if (runId && (pipelineStatus.scheme || pipelineStatus.verdict || pipelineStatus.status === 'waiting_for_answers')) {
      setIsSwitchingLanguage(true);
      try {
        const result = await switchLanguage(runId, newLang);
        setPipelineStatus((prev) => ({
          ...prev,
          explainer: result.explainer || prev.explainer,
          questions: result.questions && result.questions.length > 0 ? result.questions : prev.questions,
        }));
      } catch (err: any) {
        console.warn('Dynamic language switch notice:', err);
      } finally {
        setIsSwitchingLanguage(false);
      }
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

      // Periodic poller while processing
      const pollTimer = setInterval(() => {
        refreshStatus(res.run_id);
      }, 1500);

      // Subscribe to real-time Server-Sent Events (SSE)
      const unsubscribe = subscribePipelineEvents(
        res.run_id,
        (eventData) => {
          console.log('[SSE Event]', eventData);

          if (eventData.type === 'trace' || eventData.type === 'step_complete') {
            setPipelineStatus((prev) => {
              const existingTrace = prev.trace || [];
              const updatedTrace: TraceStep[] = [
                ...existingTrace.filter((t) => t.node !== eventData.node),
                {
                  node: eventData.node,
                  status: eventData.status || 'ok',
                  latency_ms: eventData.latency_ms || eventData.trace_entry?.ms,
                },
              ];
              return {
                ...prev,
                current_node: eventData.node,
                trace: updatedTrace,
              };
            });
            refreshStatus(res.run_id);
          }

          if (eventData.type === 'interview_required') {
            setIsLoading(false);
            clearInterval(pollTimer);
            setPipelineStatus((prev) => ({
              ...prev,
              status: 'waiting_for_answers',
              questions: eventData.questions,
            }));
            refreshStatus(res.run_id);
          }

          if (eventData.type === 'language_switched') {
            setPipelineStatus((prev) => ({
              ...prev,
              explainer: eventData.explainer || prev.explainer,
              questions: eventData.questions && eventData.questions.length > 0 ? eventData.questions : prev.questions,
            }));
            setIsSwitchingLanguage(false);
          }

          if (eventData.type === 'completed' || eventData.type === 'pipeline_complete') {
            setIsLoading(false);
            clearInterval(pollTimer);
            refreshStatus(res.run_id);
          }

          if (eventData.type === 'error' || eventData.type === 'pipeline_error') {
            setIsLoading(false);
            clearInterval(pollTimer);
            setErrorMessage(eventData.message || eventData.error || 'A processing error occurred');
          }
        },
        (err) => {
          console.warn('SSE stream disconnected, falling back to snapshot poll', err);
          refreshStatus(res.run_id);
        }
      );

      // Initial snapshot fetch after 1s
      setTimeout(() => refreshStatus(res.run_id), 1000);

      return () => {
        clearInterval(pollTimer);
        unsubscribe();
      };
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

      // Periodically poll for the resumed verdict and voice explainer
      let attempts = 0;
      const resumePoll = setInterval(async () => {
        attempts++;
        await refreshStatus(runId);
        if (attempts >= 8) {
          clearInterval(resumePoll);
          setIsLoading(false);
        }
      }, 1200);
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
        setLanguage={handleLanguageChange}
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
          <PipelineStepper
            currentNode={pipelineStatus.current_node}
            trace={pipelineStatus.trace || []}
            status={pipelineStatus.status}
            confidence={pipelineStatus.scheme?.confidence}
            onReset={handleReset}
          />
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
            {((pipelineStatus.status === 'waiting_for_answers' &&
              pipelineStatus.questions &&
              pipelineStatus.questions.length > 0) ||
              (pipelineStatus.verdict &&
                pipelineStatus.verdict.status === 'MAYBE' &&
                pipelineStatus.verdict.missing_fields &&
                pipelineStatus.verdict.missing_fields.length > 0)) && (
                <InterviewCard
                  questions={
                    pipelineStatus.questions && pipelineStatus.questions.length > 0
                      ? pipelineStatus.questions
                      : pipelineStatus.verdict.missing_fields.map((f) => ({
                          field: f,
                          question_text:
                            f === 'business_type'
                              ? 'What is your enterprise classification?'
                              : f === 'annual_turnover'
                              ? 'What is your business annual turnover in INR?'
                              : `Please provide value for ${f.replace(/_/g, ' ')}`,
                          input_type: f === 'business_type' ? 'choice' : 'number',
                          choices: f === 'business_type' ? ['Micro', 'Small', 'Medium', 'Other'] : [],
                        }))
                  }
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
              <VoicePlayer
                explainer={pipelineStatus.explainer}
                isSwitchingLanguage={isSwitchingLanguage}
              />
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

