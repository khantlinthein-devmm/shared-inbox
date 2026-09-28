"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const CANDIDATE_TYPES: Array<[mime: string, ext: string]> = [
  ["audio/webm;codecs=opus", "webm"],
  ["audio/ogg;codecs=opus", "ogg"],
  ["audio/mp4", "m4a"],
];

function pickMimeType(): [string, string] | null {
  if (typeof MediaRecorder === "undefined") return null;
  return CANDIDATE_TYPES.find(([mime]) => MediaRecorder.isTypeSupported(mime)) ?? ["", "webm"];
}

/** Records microphone audio; `stop()` resolves with the recording as a File. */
export function useVoiceRecorder() {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const release = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    recorderRef.current?.stream.getTracks().forEach((t) => t.stop());
    recorderRef.current = null;
    setRecording(false);
    setSeconds(0);
  }, []);

  useEffect(() => release, [release]);

  const start = useCallback(async () => {
    const picked = pickMimeType();
    if (!picked || !navigator.mediaDevices?.getUserMedia) {
      throw new Error("Voice recording isn't supported in this browser (it needs HTTPS or localhost).");
    }
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      throw new Error("Microphone access was blocked. Allow it in the browser's site settings.");
    }
    const recorder = new MediaRecorder(stream, picked[0] ? { mimeType: picked[0] } : undefined);
    chunksRef.current = [];
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    recorder.start();
    recorderRef.current = recorder;
    setRecording(true);
    setSeconds(0);
    timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
  }, []);

  const stop = useCallback(async (): Promise<File | null> => {
    const recorder = recorderRef.current;
    if (!recorder) return null;
    const ext = CANDIDATE_TYPES.find(([mime]) => recorder.mimeType.startsWith(mime.split(";")[0]))?.[1] ?? "webm";
    const done = new Promise<void>((resolve) => {
      recorder.onstop = () => resolve();
    });
    recorder.stop();
    await done;
    const type = recorder.mimeType || "audio/webm";
    release();
    const blob = new Blob(chunksRef.current, { type });
    chunksRef.current = [];
    return blob.size > 0 ? new File([blob], `voice-${Date.now()}.${ext}`, { type }) : null;
  }, [release]);

  const cancel = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    chunksRef.current = [];
    release();
  }, [release]);

  return { recording, seconds, start, stop, cancel };
}
