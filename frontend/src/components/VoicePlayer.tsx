import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, SkipForward, SkipBack, Volume2, Sparkles, Headphones } from 'lucide-react';
import { Explainer, Segment } from '../types';
import { resolveAudioUrl } from '../api';

interface VoicePlayerProps {
  explainer?: Explainer;
  isSwitchingLanguage?: boolean;
}

const LANGUAGE_DISPLAY_NAMES: Record<string, string> = {
  hi: 'Hindi (हिन्दी)',
  mr: 'Marathi (मराठी)',
  en: 'English',
  ta: 'Tamil (தமிழ்)',
  te: 'Telugu (తెలుగు)',
  bn: 'Bengali (বাংলা)',
};

export const VoicePlayer: React.FC<VoicePlayerProps> = ({ explainer, isSwitchingLanguage }) => {
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState<number>(0);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Reset to first segment and pause when explainer language changes
  useEffect(() => {
    setCurrentSegmentIndex(0);
    setIsPlaying(false);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
  }, [explainer?.language]);

  // Pause immediately when actively switching language
  useEffect(() => {
    if (isSwitchingLanguage && audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    }
  }, [isSwitchingLanguage]);

  if (!explainer || !explainer.segments || explainer.segments.length === 0) {
    return null;
  }

  const currentSegment: Segment = explainer.segments[currentSegmentIndex] || explainer.segments[0];
  const audioSrc = currentSegment?.audio_url ? resolveAudioUrl(currentSegment.audio_url) : '';

  useEffect(() => {
    if (audioRef.current && audioSrc) {
      audioRef.current.src = audioSrc;
      audioRef.current.playbackRate = playbackSpeed;
      audioRef.current.load();
      if (isPlaying) {
        audioRef.current.play().catch(() => setIsPlaying(false));
      }
    }
  }, [currentSegmentIndex, audioSrc]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().then(() => setIsPlaying(true)).catch(() => setIsPlaying(false));
    }
  };

  const handleAudioEnded = () => {
    if (currentSegmentIndex < explainer.segments.length - 1) {
      setCurrentSegmentIndex((prev) => prev + 1);
    } else {
      setIsPlaying(false);
    }
  };

  const jumpToSegment = (idx: number) => {
    setCurrentSegmentIndex(idx);
    setIsPlaying(true);
  };

  const toggleSpeed = () => {
    const nextSpeed = playbackSpeed === 1.0 ? 1.25 : playbackSpeed === 1.25 ? 1.5 : 1.0;
    setPlaybackSpeed(nextSpeed);
    if (audioRef.current) {
      audioRef.current.playbackRate = nextSpeed;
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 sm:p-6 mb-6">
      <audio
        ref={audioRef}
        onEnded={handleAudioEnded}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
      />

      {isSwitchingLanguage && (
        <div className="mb-4 p-2.5 bg-amber-50 border border-amber-200 rounded-xl flex items-center space-x-2 text-xs text-amber-800">
          <div className="w-3.5 h-3.5 border-2 border-amber-600 border-t-transparent rounded-full animate-spin flex-shrink-0" />
          <span>Regenerating regional voice audio & synchronized transcript...</span>
        </div>
      )}

      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 bg-emerald-100 text-emerald-800 rounded-lg">
            <Headphones className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[11px] font-bold text-emerald-700 uppercase tracking-wider flex items-center">
              <Sparkles className="w-3 h-3 mr-1" />
              Policy Voice Explainer ({LANGUAGE_DISPLAY_NAMES[explainer.language.toLowerCase()] || explainer.language.toUpperCase()})
            </span>
            <h3 className="text-sm sm:text-base font-bold text-slate-800">
              Listen to Scheme Policy & Requirements
            </h3>
          </div>
        </div>

        {/* Speed toggle */}
        <button
          onClick={toggleSpeed}
          className="text-xs font-mono font-bold px-2.5 py-1 bg-slate-100 text-slate-700 hover:bg-slate-200 rounded-lg transition"
        >
          {playbackSpeed}x
        </button>
      </div>

      {/* Main Playback Bar */}
      <div className="flex items-center space-x-3 bg-slate-50 p-3.5 rounded-xl border border-slate-200 mb-4">
        <button
          onClick={() => jumpToSegment(Math.max(0, currentSegmentIndex - 1))}
          disabled={currentSegmentIndex === 0}
          className="p-2 text-slate-500 hover:text-slate-900 disabled:opacity-30 transition"
        >
          <SkipBack className="w-4 h-4" />
        </button>

        <button
          onClick={togglePlay}
          className="p-3 bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white rounded-full shadow-md shadow-emerald-500/20 transition"
        >
          {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
        </button>

        <button
          onClick={() => jumpToSegment(Math.min(explainer.segments.length - 1, currentSegmentIndex + 1))}
          disabled={currentSegmentIndex === explainer.segments.length - 1}
          className="p-2 text-slate-500 hover:text-slate-900 disabled:opacity-30 transition"
        >
          <SkipForward className="w-4 h-4" />
        </button>

        {/* Progress Tracker */}
        <div className="flex-1 ml-2">
          <div className="flex justify-between text-xs text-slate-500 mb-1">
            <span>Segment {currentSegmentIndex + 1} of {explainer.segments.length}</span>
            <span className="flex items-center">
              <Volume2 className="w-3.5 h-3.5 mr-1 text-slate-400" />
              Edge-TTS High-Definition
            </span>
          </div>
          <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-emerald-500 h-full transition-all duration-300"
              style={{
                width: `${((currentSegmentIndex + 1) / explainer.segments.length) * 100}%`,
              }}
            />
          </div>
        </div>
      </div>

      {/* Synchronized Transcript */}
      <div className="space-y-2.5">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
          Interactive Synchronized Transcript (Click any sentence to listen):
        </span>
        {explainer.segments.map((seg: Segment, idx: number) => {
          const isCurrent = idx === currentSegmentIndex;

          return (
            <div
              key={idx}
              onClick={() => jumpToSegment(idx)}
              className={`p-3.5 rounded-xl border text-sm cursor-pointer transition-all ${
                isCurrent
                  ? 'bg-emerald-50/80 border-emerald-400 shadow-sm ring-1 ring-emerald-300'
                  : 'bg-white border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="flex items-start justify-between">
                <p
                  className={`flex-1 font-medium leading-relaxed ${
                    isCurrent ? 'text-emerald-950 font-bold' : 'text-slate-700'
                  }`}
                >
                  {seg.text}
                </p>
                {seg.clause_ids && seg.clause_ids[0] && (
                  <span className="text-[10px] font-mono text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded ml-2 flex-shrink-0">
                    {seg.clause_ids[0]}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

