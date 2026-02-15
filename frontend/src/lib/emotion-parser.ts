import type { MiraEmotion } from "@/hooks/useOrbAvatar";

const VALID_EMOTIONS: MiraEmotion[] = [
  "idle",
  "thinking",
  "talking",
  "happy",
  "excited",
  "concerned",
  "sassy",
  "disappointed",
  "surprised",
  "proud",
  "flirty",
  "judgy",
  "sympathetic",
];

// Map old emotion names to new ones for backward compatibility
const EMOTION_ALIASES: Record<string, MiraEmotion> = {
  neutral: "idle",
  teasing: "sassy",
  worried: "concerned",
  sad: "disappointed",
  confident: "proud",
  playful: "flirty",
  skeptical: "judgy",
  caring: "sympathetic",
  joy: "happy",
  enthusiasm: "excited",
  shock: "surprised",
};

/** Parse [emotion:X] prefix tag from Claude's response. */
export function parseEmotionTag(text: string): {
  emotion: MiraEmotion;
  cleanText: string;
} {
  const match = text.match(/^\[emotion:(\w+)\]\s*/i);
  if (match) {
    const rawTag = match[1].toLowerCase();
    
    // Check if it's a valid emotion
    if (VALID_EMOTIONS.includes(rawTag as MiraEmotion)) {
      return {
        emotion: rawTag as MiraEmotion,
        cleanText: text.slice(match[0].length),
      };
    }
    
    // Check aliases
    if (rawTag in EMOTION_ALIASES) {
      return {
        emotion: EMOTION_ALIASES[rawTag],
        cleanText: text.slice(match[0].length),
      };
    }
    
    // Unknown emotion, default to idle
    console.warn(`[EmotionParser] Unknown emotion: ${rawTag}, defaulting to idle`);
    return {
      emotion: "idle",
      cleanText: text.slice(match[0].length),
    };
  }
  
  return { emotion: "idle", cleanText: text };
}

/**
 * Detect emotion from text content using keyword matching.
 * Used as a fallback when no explicit emotion tag is present.
 */
export function detectEmotionFromText(text: string): MiraEmotion {
  const lower = text.toLowerCase();
  
  // Excited keywords
  if (/\b(amazing|awesome|incredible|fantastic|wow|omg|oh my god|can't wait|so excited|yay|woohoo)\b/.test(lower)) {
    return "excited";
  }
  
  // Happy keywords
  if (/\b(happy|glad|pleased|delighted|love|wonderful|great|nice|lovely)\b/.test(lower)) {
    return "happy";
  }
  
  // Sassy keywords
  if (/\b(obviously|clearly|duh|honey|sweetie|girl|please|excuse me|well well|oh really)\b/.test(lower)) {
    return "sassy";
  }
  
  // Judgy keywords
  if (/\b(really\?|seriously\?|hmm|suspicious|doubt|questionable|uh huh|sure jan)\b/.test(lower)) {
    return "judgy";
  }
  
  // Concerned keywords
  if (/\b(worried|concern|careful|watch out|be safe|oh no|uh oh|trouble)\b/.test(lower)) {
    return "concerned";
  }
  
  // Disappointed keywords
  if (/\b(unfortunately|sadly|sorry to|bad news|disappointing|bummer|too bad)\b/.test(lower)) {
    return "disappointed";
  }
  
  // Surprised keywords
  if (/\b(what\!|no way|seriously|really\!|oh\!|whoa|wait what|huh)\b/.test(lower)) {
    return "surprised";
  }
  
  // Proud keywords
  if (/\b(proud|accomplished|nailed it|crushed it|killed it|you did it|well done|excellent)\b/.test(lower)) {
    return "proud";
  }
  
  // Flirty keywords
  if (/\b(cute|handsome|gorgeous|looking good|hot|stunning|beautiful|charming)\b/.test(lower)) {
    return "flirty";
  }
  
  // Sympathetic keywords
  if (/\b(sorry to hear|that's tough|i understand|must be hard|here for you|it's okay|hang in there)\b/.test(lower)) {
    return "sympathetic";
  }
  
  // Thinking keywords
  if (/\b(let me think|hmm|considering|pondering|analyzing|checking|looking into)\b/.test(lower)) {
    return "thinking";
  }
  
  // Default to idle/talking
  return "idle";
}
