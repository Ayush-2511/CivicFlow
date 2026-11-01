import React from 'react';
import { Check, Loader2, AlertCircle, RotateCcw } from 'lucide-react';
import { TraceStep } from '../types';

interface PipelineStepperProps {
  currentNode?: string;
  trace: TraceStep[];
  status: string;
  confidence?: number;
  onReset?: () => void;
}

const NODES = [
  { key: 'ingest', label: 'Ingest' },
  { key: 'parse', label: 'OCR & Parse' },
  { key: 'index', label: 'Clause Index' },
  { key: 'extract', label: 'Extract' },
  { key: 'verify', label: 'Verifier' },
  { key: 'interview', label: 'Interview' },
  { key: 'evaluate', label: 'Rule Engine' },
  { key: 'compose', label: 'Explainer' },
  { key: 'voice', label: 'Voice TTS' },
];

export const PipelineStepper: React.FC<PipelineStepperProps> = ({
  currentNode,
  trace,
  status,
  confidence,
  onReset,
}) => {
  const getNodeInfo = (nodeKey: string, nodeIndex: number) => {
    // Find all trace entries for this node
    const nodeEntries = trace.filter((t) => t.node === nodeKey);
    const traceEntry = nodeEntries.length > 0 ? nodeEntries[nodeEntries.length - 1] : undefined;

    // A node is completed if:
    // 1. Any of its trace entries has a completed status ('ok', 'interview_completed', 'interview_ready', etc.)
    // 2. OR any downstream node in the linear pipeline is already completed
    const hasSuccessfulEntry = nodeEntries.some((t) =>
      t.status === 'ok' ||
      t.status === 'interview_completed' ||
      t.status === 'interview_ready' ||
      t.status === 'completed' ||
      t.status === 'evaluated' ||
      t.status === 'composed'
    );

    const hasLaterStepCompleted = NODES.slice(nodeIndex + 1).some((laterNode) =>
      trace.some((t) => t.node === laterNode.key && (t.status === 'ok' || t.status === 'completed' || t.status === 'evaluated' || t.status === 'composed'))
    );

    const isCompleted = hasSuccessfulEntry || hasLaterStepCompleted;

    const isCurrent =
      (currentNode === nodeKey && status === 'running') ||
      (nodeKey === 'interview' && status === 'waiting_for_answers');

    const isPending = !isCompleted && !isCurrent;
    const hasError = !isCompleted && nodeEntries.some((t) => t.status === 'error');

    return { traceEntry, isCompleted, isCurrent, isPending, hasError };
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-4 sm:p-5 mb-6">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3 border-b border-slate-100 pb-3">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Real-Time State Machine
          </span>
          <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded-full font-medium">
            LangGraph Orchestration
          </span>
        </div>

        <div className="flex items-center space-x-3">
          {typeof confidence === 'number' && (
            <div className="flex items-center space-x-1.5 text-xs">
              <span className="text-slate-500">Grounding Confidence:</span>
              <span
                className={`font-bold px-2 py-0.5 rounded-full ${
                  confidence >= 0.8
                    ? 'bg-emerald-100 text-emerald-800'
                    : confidence >= 0.5
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-rose-100 text-rose-800'
                }`}
              >
                {(confidence * 100).toFixed(0)}%
              </span>
            </div>
          )}

          {onReset && (
            <button
              type="button"
              onClick={onReset}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 border border-slate-300 hover:border-slate-400 rounded-lg text-xs font-semibold shadow-sm transition active:scale-95 cursor-pointer"
              title="Reset analysis and load another scheme"
            >
              <RotateCcw className="w-3.5 h-3.5 text-emerald-600" />
              <span>New Scheme</span>
            </button>
          )}
        </div>
      </div>

      {/* Stepper bar */}
      <div className="overflow-x-auto pb-1">
        <div className="flex items-center justify-between min-w-[700px]">
          {NODES.map((node, index) => {
            const { traceEntry, isCompleted, isCurrent, hasError } = getNodeInfo(node.key, index);

            return (
              <React.Fragment key={node.key}>
                {/* Step Item */}
                <div className="flex flex-col items-center relative">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center font-semibold text-xs transition-all ${
                      isCompleted
                        ? 'bg-emerald-600 text-white shadow-sm'
                        : isCurrent
                        ? 'bg-amber-500 text-white ring-4 ring-amber-100 animate-pulse'
                        : hasError
                        ? 'bg-rose-600 text-white'
                        : 'bg-slate-100 text-slate-400 border border-slate-200'
                    }`}
                  >
                    {isCompleted ? (
                      <Check className="w-4 h-4 stroke-[3]" />
                    ) : isCurrent ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : hasError ? (
                      <AlertCircle className="w-4 h-4" />
                    ) : (
                      index + 1
                    )}
                  </div>

                  <span
                    className={`text-xs mt-1.5 font-medium whitespace-nowrap ${
                      isCompleted
                        ? 'text-emerald-700 font-semibold'
                        : isCurrent
                        ? 'text-amber-700 font-bold'
                        : hasError
                        ? 'text-rose-600'
                        : 'text-slate-400'
                    }`}
                  >
                    {node.label}
                  </span>

                  {traceEntry?.latency_ms !== undefined && (
                    <span className="text-[10px] text-slate-400 font-mono mt-0.5">
                      {traceEntry.latency_ms}ms
                    </span>
                  )}
                </div>

                {/* Connecting Line */}
                {index < NODES.length - 1 && (
                  <div
                    className={`flex-1 h-0.5 mx-2 mb-4 transition-all ${
                      isCompleted ? 'bg-emerald-500' : 'bg-slate-200'
                    }`}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
};

