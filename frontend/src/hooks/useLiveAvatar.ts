"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  LiveAvatarSession,
  SessionEvent,
  AgentEventsEnum,
} from "@heygen/liveavatar-web-sdk";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UseLiveAvatarReturn {
  isReady: boolean;
  isSpeaking: boolean;
  startSession: () => Promise<void>;
  stopSession: () => Promise<void>;
  speak: (text: string) => void;
  interrupt: () => void;
  clearQueue: () => void;
  avatarRef: React.RefObject<HTMLVideoElement | null>;
}

async function fetchSessionToken(): Promise<string> {
  const res = await fetch(`${API_URL}/api/heygen/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_sandbox: true }),
  });
  if (!res.ok) throw new Error(`Failed to fetch LiveAvatar token: ${res.status}`);
  const data = await res.json();
  return data.session_token;
}

export function useLiveAvatar(): UseLiveAvatarReturn {
  const [isReady, setIsReady] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const avatarRef = useRef<HTMLVideoElement | null>(null);
  const sessionRef = useRef<LiveAvatarSession | null>(null);

  // Speech queue — process one sentence at a time to prevent overlapping speech
  const speechQueueRef = useRef<string[]>([]);
  const isProcessingQueueRef = useRef(false);

  const processQueue = useCallback(() => {
    if (isProcessingQueueRef.current || !sessionRef.current) return;
    const next = speechQueueRef.current.shift();
    if (!next) {
      setIsSpeaking(false);
      return;
    }
    isProcessingQueueRef.current = true;
    setIsSpeaking(true);
    try {
      sessionRef.current.repeat(next);
    } catch (err) {
      console.error("[LiveAvatar] repeat() failed:", err);
      isProcessingQueueRef.current = false;
      processQueue();
    }
    // isProcessingQueueRef is reset by AVATAR_SPEAK_ENDED handler
  }, []);

  const clearQueue = useCallback(() => {
    speechQueueRef.current = [];
    isProcessingQueueRef.current = false;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearQueue();
      sessionRef.current?.stop().catch(() => {});
      sessionRef.current = null;
    };
  }, [clearQueue]);

  const startSession = useCallback(async () => {
    if (sessionRef.current) return;

    const token = await fetchSessionToken();
    const session = new LiveAvatarSession(token);
    sessionRef.current = session;

    session.on(SessionEvent.SESSION_STREAM_READY, () => {
      if (avatarRef.current) {
        session.attach(avatarRef.current);
      }
      setIsReady(true);
    });

    session.on(AgentEventsEnum.AVATAR_SPEAK_STARTED, () => {
      setIsSpeaking(true);
    });

    session.on(AgentEventsEnum.AVATAR_SPEAK_ENDED, () => {
      isProcessingQueueRef.current = false;
      processQueue();
    });

    session.on(SessionEvent.SESSION_DISCONNECTED, () => {
      setIsReady(false);
      setIsSpeaking(false);
      clearQueue();
      sessionRef.current = null;
    });

    await session.start();
  }, [processQueue, clearQueue]);

  const stopSession = useCallback(async () => {
    if (!sessionRef.current) return;
    clearQueue();
    await sessionRef.current.stop();
    sessionRef.current = null;
    setIsReady(false);
    setIsSpeaking(false);
  }, [clearQueue]);

  const speak = useCallback(
    (text: string) => {
      if (!text.trim()) return;
      speechQueueRef.current.push(text);
      setIsSpeaking(true);
      processQueue();
    },
    [processQueue],
  );

  const interrupt = useCallback(() => {
    if (!sessionRef.current) return;
    clearQueue();
    sessionRef.current.interrupt();
  }, [clearQueue]);

  return {
    isReady,
    isSpeaking,
    startSession,
    stopSession,
    speak,
    interrupt,
    clearQueue,
    avatarRef,
  };
}
