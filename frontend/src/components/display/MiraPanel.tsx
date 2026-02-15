"use client";

import {
  forwardRef,
  useImperativeHandle,
  useRef,
  useState,
  useEffect,
  useCallback,
} from "react";
import styles from "./display.module.css";

// ── Avatar States ──

export type MiraState =
  | "idle"
  | "thinking"
  | "happy"
  | "excited"
  | "talking"
  | "concerned";

const STATES: MiraState[] = [
  "idle",
  "thinking",
  "happy",
  "excited",
  "talking",
  "concerned",
];

const VIDEO_BASE = "/jenny/videos";
const IMAGE_BASE = "/jenny";

const LOOP_VIDEOS: Record<MiraState, string> = {
  idle: `${VIDEO_BASE}/idle_loop.mp4`,
  thinking: `${VIDEO_BASE}/thinking_loop.mp4`,
  happy: `${VIDEO_BASE}/happy_loop.mp4`,
  excited: `${VIDEO_BASE}/excited_loop.mp4`,
  talking: `${VIDEO_BASE}/talking_loop.mp4`,
  concerned: `${VIDEO_BASE}/concerned_loop.mp4`,
};

const FALLBACK_IMAGES: Record<MiraState, string> = {
  idle: `${IMAGE_BASE}/idle.png`,
  thinking: `${IMAGE_BASE}/thinking.png`,
  happy: `${IMAGE_BASE}/happy.png`,
  excited: `${IMAGE_BASE}/excited.png`,
  talking: `${IMAGE_BASE}/talking.png`,
  concerned: `${IMAGE_BASE}/concerned.png`,
};

// ── Scripted Responses (one-shot videos with baked-in audio) ──

interface ScriptedResponse {
  video: string;
  emotion: MiraState;
  keywords: string[];
}

const SCRIPTED_RESPONSES: Record<string, ScriptedResponse> = {
  "ew that's gross": {
    video: `${VIDEO_BASE}/scripted/judgmental_gross.mp4`,
    emotion: "concerned",
    keywords: ["gross", "ew", "disgusting", "ugly"],
  },
  "oh no honey what is that": {
    video: `${VIDEO_BASE}/scripted/judgmental_honey.mp4`,
    emotion: "concerned",
    keywords: ["honey", "what is that", "oh no"],
  },
  "that's... a choice": {
    video: `${VIDEO_BASE}/scripted/judgmental_choice.mp4`,
    emotion: "concerned",
    keywords: ["choice", "interesting choice", "bold"],
  },
  "why would you wear that": {
    video: `${VIDEO_BASE}/scripted/confused_why.mp4`,
    emotion: "thinking",
    keywords: ["why", "wear that", "why would"],
  },
  "wait what is happening here": {
    video: `${VIDEO_BASE}/scripted/confused_what.mp4`,
    emotion: "thinking",
    keywords: ["what is happening", "what", "wait"],
  },
  "i'm so confused right now": {
    video: `${VIDEO_BASE}/scripted/confused_lost.mp4`,
    emotion: "thinking",
    keywords: ["confused", "lost", "don't understand"],
  },
  "okay i love that": {
    video: `${VIDEO_BASE}/scripted/positive_love.mp4`,
    emotion: "excited",
    keywords: ["love", "love that", "love it"],
  },
  "yes this is it": {
    video: `${VIDEO_BASE}/scripted/positive_yes.mp4`,
    emotion: "excited",
    keywords: ["yes", "this is it", "perfect"],
  },
  "you look amazing": {
    video: `${VIDEO_BASE}/scripted/positive_amazing.mp4`,
    emotion: "happy",
    keywords: ["amazing", "look amazing", "stunning", "gorgeous"],
  },
  "hmm let me see": {
    video: `${VIDEO_BASE}/scripted/neutral_see.mp4`,
    emotion: "thinking",
    keywords: ["hmm", "let me see", "thinking"],
  },
  "okay here's the thing": {
    video: `${VIDEO_BASE}/scripted/neutral_thing.mp4`,
    emotion: "thinking",
    keywords: ["here's the thing", "the thing is", "okay so"],
  },
  "you know what it works": {
    video: `${VIDEO_BASE}/scripted/supportive_works.mp4`,
    emotion: "happy",
    keywords: ["it works", "works", "actually works"],
  },
  "not bad at all": {
    video: `${VIDEO_BASE}/scripted/supportive_notbad.mp4`,
    emotion: "happy",
    keywords: ["not bad", "pretty good", "decent"],
  },
};

// ── Matching & Sentiment ──

function findScriptedResponse(
  text: string
): (ScriptedResponse & { phrase: string }) | null {
  const lower = text.toLowerCase();

  // Exact phrase match first
  for (const [phrase, data] of Object.entries(SCRIPTED_RESPONSES)) {
    if (lower.includes(phrase)) {
      return { phrase, ...data };
    }
  }

  // Keyword scoring fallback
  let bestMatch: (ScriptedResponse & { phrase: string }) | null = null;
  let bestScore = 0;
  for (const [phrase, data] of Object.entries(SCRIPTED_RESPONSES)) {
    let score = 0;
    for (const kw of data.keywords) {
      if (lower.includes(kw)) score += kw.length;
    }
    if (score > bestScore) {
      bestScore = score;
      bestMatch = { phrase, ...data };
    }
  }

  return bestScore >= 4 ? bestMatch : null;
}

function detectEmotion(text: string): MiraState {
  const lower = text.toLowerCase();
  if (/ew|gross|ugly|terrible|awful|yuck|no no|honey/.test(lower))
    return "concerned";
  if (/confused|what|why|huh|\?{2,}|don't understand/.test(lower))
    return "thinking";
  if (/love|amazing|perfect|yes!|gorgeous|stunning|beautiful|great/.test(lower))
    return "excited";
  if (/good|nice|works|not bad|decent|okay|fine/.test(lower)) return "happy";
  if (/hmm|let me|thinking|consider/.test(lower)) return "thinking";
  return "talking";
}

// ── Component ──

export interface MiraPanelHandle {
  speak: (text: string) => Promise<void>;
  setState: (state: MiraState) => void;
}

const MiraPanel = forwardRef<MiraPanelHandle>(function MiraPanel(_, ref) {
  const [currentState, setCurrentState] = useState<MiraState>("idle");
  const [isScripted, setIsScripted] = useState(false);
  const [videoFailed, setVideoFailed] = useState<Set<string>>(new Set());

  // Refs for each loop video element
  const loopVideoRefs = useRef<Record<string, HTMLVideoElement | null>>({});
  const scriptedVideoRef = useRef<HTMLVideoElement>(null);

  // Set loop video ref
  const setLoopRef = useCallback(
    (state: string) => (el: HTMLVideoElement | null) => {
      loopVideoRefs.current[state] = el;
    },
    []
  );

  // Play the active loop video, pause others
  useEffect(() => {
    if (isScripted) {
      // Pause all loop videos during scripted playback
      for (const v of Object.values(loopVideoRefs.current)) {
        v?.pause();
      }
      return;
    }

    for (const [state, el] of Object.entries(loopVideoRefs.current)) {
      if (!el) continue;
      if (state === currentState) {
        el.currentTime = 0;
        el.play().catch(() => {});
      } else {
        el.pause();
      }
    }
  }, [currentState, isScripted]);

  const playScriptedVideo = useCallback((videoPath: string): Promise<void> => {
    return new Promise((resolve) => {
      const el = scriptedVideoRef.current;
      if (!el) {
        resolve();
        return;
      }

      setIsScripted(true);
      el.src = videoPath;

      const cleanup = () => {
        el.removeEventListener("ended", onEnded);
        el.removeEventListener("error", onError);
        setIsScripted(false);
        setCurrentState("idle");
        resolve();
      };

      const onEnded = () => cleanup();
      const onError = () => {
        console.warn("[Mira] Scripted video failed:", videoPath);
        cleanup();
      };

      el.addEventListener("ended", onEnded, { once: true });
      el.addEventListener("error", onError, { once: true });
      el.play().catch(() => cleanup());
    });
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      speak: async (text: string) => {
        // Check for scripted response first
        const scripted = findScriptedResponse(text);
        if (scripted) {
          await playScriptedVideo(scripted.video);
          return;
        }

        // Otherwise, set emotion state from text sentiment
        const emotion = detectEmotion(text);
        setCurrentState(emotion);

        // Return to idle after emotion display
        if (emotion !== "idle" && emotion !== "talking") {
          setTimeout(() => setCurrentState("idle"), 5000);
        }
      },

      setState: (state: MiraState) => {
        setCurrentState(state);
      },
    }),
    [playScriptedVideo]
  );

  const handleVideoError = useCallback(
    (state: string) => () => {
      setVideoFailed((prev) => new Set(prev).add(state));
    },
    []
  );

  return (
    <div
      className={`${styles.glassPanel} ${styles.miraPanel} ${isScripted ? styles.miraPanelActive : ""}`}
      aria-label="Mira AI Avatar"
    >
      {/* Loop videos — one per state, stacked; only active one visible */}
      {STATES.map((state) => {
        const failed = videoFailed.has(state);
        const isVisible = state === currentState && !isScripted;

        return (
          <div
            key={state}
            className={styles.miraVideoWrapper}
            style={{
              opacity: isVisible ? 1 : 0,
              zIndex: isVisible ? 1 : 0,
            }}
          >
            {!failed ? (
              <video
                ref={setLoopRef(state)}
                src={LOOP_VIDEOS[state]}
                loop
                muted
                playsInline
                preload="auto"
                className={styles.miraVideo}
                onError={handleVideoError(state)}
              />
            ) : (
              // Fallback to static image
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={FALLBACK_IMAGES[state]}
                alt={`Mira ${state}`}
                className={styles.miraVideo}
              />
            )}
          </div>
        );
      })}

      {/* Scripted video (one-shot with audio) */}
      <div
        className={styles.miraVideoWrapper}
        style={{
          opacity: isScripted ? 1 : 0,
          zIndex: isScripted ? 2 : 0,
        }}
      >
        <video
          ref={scriptedVideoRef}
          playsInline
          muted={false}
          preload="none"
          className={styles.miraVideo}
        />
      </div>
    </div>
  );
});

export default MiraPanel;
