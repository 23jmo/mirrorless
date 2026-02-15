"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { socket } from "@/lib/socket";
import { generateSpeech } from "@/lib/avatar-api";
import { playAudioWithAnalysis } from "@/lib/audio-analysis";

// Web Speech API types (not included in all TS dom libs)
interface SpeechRecognitionResult {
  readonly isFinal: boolean;
  readonly length: number;
  [index: number]: { readonly transcript: string; readonly confidence: number };
}
interface SpeechRecognitionResultList {
  readonly length: number;
  [index: number]: SpeechRecognitionResult;
}
interface SpeechRecognitionEventLike {
  readonly resultIndex: number;
  readonly results: SpeechRecognitionResultList;
}
interface SpeechRecognitionErrorEventLike {
  readonly error: string;
}
interface SpeechRecognitionInstance {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

interface UseVoiceChatOptions {
  userId?: string;
  onAmplitude?: (amplitude: number) => void;
}

interface UseVoiceChatReturn {
  isListening: boolean;
  isSpeaking: boolean;
  transcript: string;
  miraText: string;
  start: () => void;
  stop: () => void;
}

/**
 * Full voice chat loop: mic STT → socket → orchestrator → Mira text → TTS → audio playback.
 *
 * Uses Web Speech API (webkitSpeechRecognition) for browser-side STT.
 * Pauses recognition while Mira is speaking to avoid feedback loops.
 */
export function useVoiceChat({
  userId,
  onAmplitude,
}: UseVoiceChatOptions): UseVoiceChatReturn {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [miraText, setMiraText] = useState("");

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const miraBufferRef = useRef("");
  const shouldResumeRef = useRef(false);
  const isListeningRef = useRef(false);

  // Keep ref in sync with state
  useEffect(() => {
    isListeningRef.current = isListening;
  }, [isListening]);

  // TTS playback for Mira's response
  const speakMira = useCallback(
    async (text: string) => {
      if (!text.trim()) return;
      setIsSpeaking(true);

      // Pause STT while Mira speaks
      if (recognitionRef.current && isListeningRef.current) {
        shouldResumeRef.current = true;
        try {
          recognitionRef.current.stop();
        } catch {
          // ignore if already stopped
        }
      }

      try {
        const audioBuffer = await generateSpeech(text);
        await playAudioWithAnalysis(audioBuffer, (a) => {
          onAmplitude?.(a);
        });
      } catch (err) {
        console.error("[useVoiceChat] TTS failed:", err);
      } finally {
        setIsSpeaking(false);
        onAmplitude?.(0);

        // Resume STT after Mira finishes speaking
        if (shouldResumeRef.current) {
          shouldResumeRef.current = false;
          try {
            recognitionRef.current?.start();
          } catch {
            // ignore if already started
          }
        }
      }
    },
    [onAmplitude]
  );

  // Listen for Mira's streamed response chunks and speech-done signal
  useEffect(() => {
    function handleMiraSpeech(data: { text: string; is_chunk: boolean }) {
      miraBufferRef.current += data.text;
      setMiraText(miraBufferRef.current);
    }

    function handleMiraSpeechDone(data: { text: string }) {
      const fullText = data.text || miraBufferRef.current;
      miraBufferRef.current = "";
      speakMira(fullText);
    }

    socket.on("mira_speech", handleMiraSpeech);
    socket.on("mira_speech_done", handleMiraSpeechDone);

    return () => {
      socket.off("mira_speech", handleMiraSpeech);
      socket.off("mira_speech_done", handleMiraSpeechDone);
    };
  }, [speakMira]);

  // Initialize Web Speech API recognition
  const start = useCallback(() => {
    const SpeechRecognitionCtor: (new () => SpeechRecognitionInstance) | undefined =
      // Chrome uses webkitSpeechRecognition; standard is SpeechRecognition
      (window as unknown as { webkitSpeechRecognition?: new () => SpeechRecognitionInstance }).webkitSpeechRecognition ??
      (window as unknown as { SpeechRecognition?: new () => SpeechRecognitionInstance }).SpeechRecognition;

    if (!SpeechRecognitionCtor) {
      console.error("[useVoiceChat] SpeechRecognition not supported");
      return;
    }

    const recognition = new SpeechRecognitionCtor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event: SpeechRecognitionEventLike) => {
      let interimTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          const finalText = result[0].transcript.trim();
          if (finalText && userId) {
            setTranscript(finalText);
            // Send to orchestrator via socket
            socket.emit("mirror_event", {
              user_id: userId,
              event: { type: "voice", transcript: finalText },
            });
            // Clear Mira's previous text for fresh response
            miraBufferRef.current = "";
            setMiraText("");
          }
        } else {
          interimTranscript += result[0].transcript;
        }
      }
      if (interimTranscript) {
        setTranscript(interimTranscript);
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEventLike) => {
      // "no-speech" and "aborted" are expected during normal use
      if (event.error !== "no-speech" && event.error !== "aborted") {
        console.error("[useVoiceChat] Recognition error:", event.error);
      }
    };

    recognition.onend = () => {
      // Auto-restart if we're still supposed to be listening and not paused for TTS
      if (isListeningRef.current && !shouldResumeRef.current) {
        try {
          recognition.start();
        } catch {
          // ignore
        }
      }
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }, [userId]);

  const stop = useCallback(() => {
    setIsListening(false);
    shouldResumeRef.current = false;
    try {
      recognitionRef.current?.stop();
    } catch {
      // ignore
    }
    recognitionRef.current = null;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      try {
        recognitionRef.current?.stop();
      } catch {
        // ignore
      }
    };
  }, []);

  return { isListening, isSpeaking, transcript, miraText, start, stop };
}
