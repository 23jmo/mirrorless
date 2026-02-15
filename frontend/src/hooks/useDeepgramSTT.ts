"use client";

import { useCallback, useState } from "react";

export interface UseDeepgramSTTReturn {
  startListening: () => void;
  stopListening: () => void;
  isListening: boolean;
  transcript: string;
  interimTranscript: string;
}

export function useDeepgramSTT(): UseDeepgramSTTReturn {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");

  const startListening = useCallback(() => {
    setIsListening(true);
    // Stub: real Deepgram streaming integration will replace this
  }, []);

  const stopListening = useCallback(() => {
    setIsListening(false);
    setTranscript("");
    setInterimTranscript("");
  }, []);

  return { startListening, stopListening, isListening, transcript, interimTranscript };
}
