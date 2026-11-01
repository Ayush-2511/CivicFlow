import { PipelineStartResponse, PipelineStatus, VerifiedSource } from './types';

const API_BASE = ''; // Uses Vite proxy in development

export async function fetchVerifiedSources(): Promise<VerifiedSource[]> {
  const res = await fetch(`${API_BASE}/sources/verified`);
  if (!res.ok) throw new Error(`Failed to load sources: ${res.statusText}`);
  return res.json();
}

export async function startPipeline(
  file: File | null,
  url: string | null,
  persona: 'citizen' | 'business',
  language: string
): Promise<PipelineStartResponse> {
  const formData = new FormData();
  if (file) {
    formData.append('file', file);
  }
  if (url && url.trim()) {
    formData.append('url', url.trim());
  }
  formData.append('persona', persona);
  formData.append('language', language);

  const res = await fetch(`${API_BASE}/pipeline/start`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message || errorData.detail || `Upload failed (${res.status})`);
  }

  return res.json();
}

export async function getPipelineStatus(runId: string): Promise<PipelineStatus> {
  const res = await fetch(`${API_BASE}/pipeline/${runId}/status`);
  if (!res.ok) throw new Error(`Failed to fetch status: ${res.statusText}`);
  return res.json();
}

export async function submitAnswers(
  runId: string,
  answers: Record<string, any>,
  units: Record<string, string> = {}
): Promise<any> {
  const res = await fetch(`${API_BASE}/session/${runId}/answers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers, units }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || err.detail || 'Failed to submit answers');
  }

  return res.json();
}

export function subscribePipelineEvents(
  runId: string,
  onEvent: (data: any) => void,
  onError?: (err: any) => void
): () => void {
  const eventSource = new EventSource(`${API_BASE}/pipeline/${runId}/events`);

  eventSource.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data);
      onEvent(parsed);
    } catch (e) {
      console.error('Failed to parse SSE event data', e);
    }
  };

  eventSource.onerror = (err) => {
    if (onError) onError(err);
    eventSource.close();
  };

  return () => {
    eventSource.close();
  };
}

export function resolveAudioUrl(url: string): string {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  return `${API_BASE}${url.startsWith('/') ? '' : '/'}${url}`;
}

