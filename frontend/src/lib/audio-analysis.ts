/**
 * Play audio from an ArrayBuffer and report speech amplitude at ~60fps.
 *
 * Uses Web Audio AnalyserNode to sample frequency bins 2–17 (~344–2924 Hz,
 * the speech-dominant range) and normalize to a 0.0–1.0 amplitude value.
 */
export function playAudioWithAnalysis(
  buffer: ArrayBuffer,
  onAmplitude?: (amplitude: number) => void
): Promise<void> {
  return new Promise(async (resolve, reject) => {
    try {
      const ctx = new AudioContext();
      const audioBuffer = await ctx.decodeAudioData(buffer);

      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;

      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.4;

      source.connect(analyser);
      analyser.connect(ctx.destination);

      const freqData = new Uint8Array(analyser.frequencyBinCount);
      let rafId: number;

      function sample() {
        analyser.getByteFrequencyData(freqData);

        // Bins 2–17 cover ~344–2924 Hz (speech range) at 44.1 kHz / 256 FFT
        let sum = 0;
        for (let i = 2; i <= 17; i++) {
          sum += freqData[i];
        }
        const amplitude = Math.min(sum / (16 * 255), 1.0);

        onAmplitude?.(amplitude);
        rafId = requestAnimationFrame(sample);
      }

      source.onended = () => {
        cancelAnimationFrame(rafId);
        onAmplitude?.(0);
        ctx.close();
        resolve();
      };

      source.start(0);
      rafId = requestAnimationFrame(sample);
    } catch (err) {
      reject(err);
    }
  });
}
