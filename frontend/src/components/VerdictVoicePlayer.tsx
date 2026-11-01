import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2, Headphones, ShieldCheck, Sparkles } from 'lucide-react';
import { Explainer, Verdict } from '../types';
import { resolveAudioUrl } from '../api';

interface VerdictVoicePlayerProps {
  verdict?: Verdict;
  explainer?: Explainer;
  isSwitchingLanguage?: boolean;
  language?: string;
}

const LANGUAGE_DISPLAY_NAMES: Record<string, string> = {
  hi: 'Hindi (हिन्दी)',
  mr: 'Marathi (मराठी)',
  en: 'English',
  ta: 'Tamil (தமிழ்)',
  te: 'Telugu (తెలుగు)',
  bn: 'Bengali (বাংলা)',
  gu: 'Gujarati (ગુજરાતી)',
  kn: 'Kannada (ಕನ್ನಡ)',
  ml: 'Malayalam (മലയാളം)',
  ur: 'Urdu (اردو)',
};

export const VerdictVoicePlayer: React.FC<VerdictVoicePlayerProps> = ({
  verdict,
  explainer,
  isSwitchingLanguage,
  language,
}) => {
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const segment = explainer?.verdict_segment;
  const audioSrc = segment?.audio_url ? resolveAudioUrl(segment.audio_url) : '';

  const activeLang = (explainer?.language || language || 'hi').toLowerCase();
  const displayLang = LANGUAGE_DISPLAY_NAMES[activeLang] || activeLang.toUpperCase();

  const isYes = verdict?.status === 'YES';
  const isNo = verdict?.status === 'NO';

  // Pause playback when language changes
  useEffect(() => {
    setIsPlaying(false);
    setCurrentTime(0);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
  }, [explainer?.language]);

  // Load new audio URL into element
  useEffect(() => {
    if (audioRef.current) {
      if (audioSrc) {
        audioRef.current.src = audioSrc;
        audioRef.current.playbackRate = playbackSpeed;
        audioRef.current.load();
      } else {
        audioRef.current.removeAttribute('src');
      }
    }
  }, [audioSrc, playbackSpeed]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().then(() => setIsPlaying(true)).catch(() => setIsPlaying(false));
    }
  };

  const toggleSpeed = () => {
    const nextSpeed = playbackSpeed === 1.0 ? 1.25 : playbackSpeed === 1.25 ? 1.5 : 1.0;
    setPlaybackSpeed(nextSpeed);
    if (audioRef.current) {
      audioRef.current.playbackRate = nextSpeed;
    }
  };

  if (!verdict && !segment) {
    return null;
  }

  // Display text in localized form
  const displayText =
    segment?.text ||
    (isNo
      ? `Eligibility Verdict: You currently do not qualify under this policy because one or more criteria were not met.`
      : isYes
      ? `Congratulations! You qualify for this scheme based on verified criteria.`
      : `Your eligibility is conditional and pending additional details.`);

  return (
    <div
      className={`rounded-2xl border-2 p-5 sm:p-6 mb-6 shadow-sm transition-all ${
        isYes
          ? 'bg-emerald-50/70 border-emerald-300'
          : isNo
          ? 'bg-rose-50/70 border-rose-300'
          : 'bg-amber-50/70 border-amber-300'
      }`}
    >
      <audio
        ref={audioRef}
        onTimeUpdate={() => {
          if (audioRef.current) setCurrentTime(audioRef.current.currentTime);
        }}
        onLoadedMetadata={() => {
          if (audioRef.current) setDuration(audioRef.current.duration);
        }}
        onEnded={() => setIsPlaying(false)}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
      />

      {isSwitchingLanguage && (
        <div className="mb-3.5 p-2.5 bg-white/90 border border-slate-200 rounded-xl flex items-center space-x-2 text-xs text-slate-700 shadow-xs">
          <div className="w-3.5 h-3.5 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin flex-shrink-0" />
          <span>Regenerating regional voice verdict in {displayLang}...</span>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 mb-3.5 border-b border-slate-200/80">
        <div className="flex items-center space-x-3">
          <div
            className={`p-2.5 rounded-xl text-white shadow-sm ${
              isYes
                ? 'bg-emerald-600 shadow-emerald-500/20'
                : isNo
                ? 'bg-rose-600 shadow-rose-500/20'
                : 'bg-amber-500 shadow-amber-500/20'
            }`}
          >
            <Headphones className="w-5 h-5" />
          </div>
          <div>
            <span
              className={`text-[10px] font-bold uppercase tracking-wider flex items-center ${
                isYes ? 'text-emerald-800' : isNo ? 'text-rose-800' : 'text-amber-800'
              }`}
            >
              <Sparkles className="w-3 h-3 mr-1" />
              Regional Voice Verdict Explainer • {displayLang}
            </span>
            <h3 className="text-sm sm:text-base font-black text-slate-900 leading-tight">
              Listen to Your Eligibility Decision & Rationale
            </h3>
          </div>
        </div>

        {/* Speed button */}
        <button
          onClick={toggleSpeed}
          className="text-xs font-mono font-bold px-2.5 py-1 bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 rounded-lg shadow-xs transition"
          title="Toggle Voice Playback Speed"
        >
          {playbackSpeed}x
        </button>
      </div>

      {/* Playback Controls & Wave Progress */}
      <div className="bg-white/90 p-3.5 rounded-xl border border-slate-200/80 shadow-xs mb-3.5 flex items-center space-x-3.5">
        <button
          onClick={togglePlay}
          className={`p-3 rounded-full text-white shadow-md active:scale-95 transition flex-shrink-0 ${
            isYes
              ? 'bg-emerald-600 hover:bg-emerald-700 shadow-emerald-500/20'
              : isNo
              ? 'bg-rose-600 hover:bg-rose-700 shadow-rose-500/20'
              : 'bg-amber-500 hover:bg-amber-600 shadow-amber-500/20'
          }`}
          title={isPlaying ? 'Pause Voice Verdict' : 'Play Voice Verdict'}
        >
          {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
        </button>

        <div className="flex-1">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span className="font-semibold text-slate-700">
              {isPlaying ? 'Speaking Your Decision...' : 'Click Play to Listen'}
            </span>
            <span className="flex items-center text-[11px] font-mono">
              <Volume2 className="w-3.5 h-3.5 mr-1 text-slate-400" />
              Edge-TTS Neural Voice
            </span>
          </div>

          <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-200 ${
                isYes ? 'bg-emerald-600' : isNo ? 'bg-rose-600' : 'bg-amber-500'
              }`}
              style={{
                width: duration > 0 ? `${(currentTime / duration) * 100}%` : isPlaying ? '60%' : '0%',
              }}
            />
          </div>
        </div>
      </div>

      {/* Spoken Decision Transcript in Regional Script */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
              Spoken Transcript ({displayLang}):
            </span>
            <p className="text-slate-900 font-bold leading-relaxed text-sm sm:text-base">
              {displayText}
            </p>
          </div>

          {segment?.clause_ids && segment.clause_ids[0] && (
            <span className="text-[10px] font-mono text-slate-500 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded flex-shrink-0 mt-0.5">
              {segment.clause_ids[0]}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

