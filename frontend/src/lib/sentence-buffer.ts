export class SentenceBuffer {
  private buffer = "";
  private onSentence: (s: string) => void;

  constructor(onSentence: (sentence: string) => void) {
    this.onSentence = onSentence;
  }

  feed(text: string): void {
    this.buffer += text;
    const re = /([^.!?]*[.!?])\s*/g;
    let match: RegExpExecArray | null;
    let lastIndex = 0;
    while ((match = re.exec(this.buffer)) !== null) {
      this.onSentence(match[1].trim());
      lastIndex = re.lastIndex;
    }
    this.buffer = this.buffer.slice(lastIndex);
  }

  flush(): void {
    if (this.buffer.trim()) {
      this.onSentence(this.buffer.trim());
    }
    this.buffer = "";
  }
}
