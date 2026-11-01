import { useEffect, useRef, useState } from "react";
import type { Candidate } from "./types";

type RecognitionResult = { isFinal: boolean; 0: { transcript: string } };
type Recognition = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: { results: ArrayLike<RecognitionResult> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
};
type VoiceWindow = Window & {
  SpeechRecognition?: new () => Recognition;
  webkitSpeechRecognition?: new () => Recognition;
};

export function useInterviewVoice(
  upgrade: boolean,
  onTranscript: (text: string) => void,
) {
  const [muted, setMuted] = useState(false);
  const [talking, setTalking] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [notice, setNotice] = useState("");
  const mutedRef = useRef(false);
  const voices = useRef<SpeechSynthesisVoice[]>([]);
  const utterance = useRef<SpeechSynthesisUtterance | null>(null);
  const audio = useRef<HTMLAudioElement | null>(null);
  const audioUrl = useRef("");
  const speechVersion = useRef(0);
  const micVersion = useRef(0);
  const holding = useRef(false);
  const recognition = useRef<Recognition | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const voiceWindow = window as VoiceWindow;
  const RecognitionClass =
    voiceWindow.SpeechRecognition || voiceWindow.webkitSpeechRecognition;
  const browserMic = !!RecognitionClass;
  const upgradeMic =
    upgrade && !!navigator.mediaDevices?.getUserMedia && !!window.MediaRecorder;

  function stopSpeech() {
    speechVersion.current++;
    window.speechSynthesis?.cancel();
    utterance.current = null;
    audio.current?.pause();
    audio.current = null;
    if (audioUrl.current) URL.revokeObjectURL(audioUrl.current);
    audioUrl.current = "";
    setTalking(false);
  }

  function stopRecording() {
    holding.current = false;
    recognition.current?.stop();
    if (recorder.current?.state === "recording") recorder.current.stop();
    setRecording(false);
  }

  function cancelRecording() {
    micVersion.current++;
    holding.current = false;
    recognition.current?.abort();
    recognition.current = null;
    if (recorder.current?.state === "recording") recorder.current.stop();
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
    setRecording(false);
    setTranscribing(false);
    setNotice("");
  }

  useEffect(() => {
    const synth = window.speechSynthesis;
    const update = () => {
      voices.current = (synth?.getVoices() || []).sort((a, b) => {
        const language =
          Number(!a.lang.toLowerCase().startsWith("en")) -
          Number(!b.lang.toLowerCase().startsWith("en"));
        return language || a.voiceURI.localeCompare(b.voiceURI);
      });
    };
    update();
    synth?.addEventListener("voiceschanged", update);
    return () => {
      synth?.removeEventListener("voiceschanged", update);
      stopSpeech();
      cancelRecording();
    };
  }, []);

  async function speak(text: string, candidate: Candidate, index: number) {
    stopSpeech();
    if (mutedRef.current) return;
    const version = speechVersion.current;
    const current = () =>
      version === speechVersion.current && !mutedRef.current;
    let browserStarted = false;
    function browserSpeak() {
      if (
        browserStarted ||
        !current() ||
        !window.speechSynthesis ||
        !window.SpeechSynthesisUtterance
      )
        return;
      browserStarted = true;
      const speech = new SpeechSynthesisUtterance(text);
      const available = voices.current;
      if (available.length) speech.voice = available[index % available.length];
      speech.lang = speech.voice?.lang || "en-US";
      const mood = (candidate.attributes.mood - 5) / 5;
      speech.pitch = [0.85, 1.05, 1.25][index % 3] + mood * 0.1;
      speech.rate = [0.9, 1, 1.1][index % 3] + mood * 0.05;
      speech.onstart = () => {
        if (current()) setTalking(true);
      };
      speech.onend = speech.onerror = () => {
        if (current()) setTalking(false);
      };
      utterance.current = speech;
      window.speechSynthesis.speak(speech);
    }
    if (!upgrade) {
      browserSpeak();
      return;
    }
    try {
      const response = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, voice_id: candidate.voice_id }),
      });
      if (!response.ok) throw new Error("Voice unavailable");
      const blob = await response.blob();
      if (!current()) return;
      const url = URL.createObjectURL(blob);
      audioUrl.current = url;
      const player = new Audio(url);
      audio.current = player;
      player.onplaying = () => {
        if (current()) setTalking(true);
      };
      player.onended = () => {
        URL.revokeObjectURL(url);
        if (current()) {
          setTalking(false);
          audioUrl.current = "";
        }
      };
      player.onerror = () => {
        URL.revokeObjectURL(url);
        browserSpeak();
      };
      await player.play();
    } catch {
      browserSpeak();
    }
  }

  async function beginRecord() {
    if (holding.current || transcribing || (!browserMic && !upgradeMic)) return;
    stopSpeech();
    cancelRecording();
    holding.current = true;
    setRecording(true);
    const version = micVersion.current;
    const current = () => version === micVersion.current;
    let browserText = "";
    let browserFailed = false;
    if (RecognitionClass) {
      const rec = new RecognitionClass();
      recognition.current = rec;
      rec.lang = "en-US";
      rec.continuous = true;
      rec.interimResults = true;
      rec.onresult = (event) => {
        if (!current()) return;
        browserText = Array.from(event.results)
          .map((result) => result[0].transcript)
          .join(" ");
        onTranscript(browserText);
      };
      rec.onerror = (event) => {
        browserFailed = true;
        if (current() && !upgradeMic && event.error !== "aborted") {
          setNotice(
            "Voice input unavailable. Check microphone permission or type instead.",
          );
          stopRecording();
        }
      };
      rec.onend = () => {
        if (current() && !upgradeMic) {
          holding.current = false;
          setRecording(false);
        }
      };
      try {
        rec.start();
      } catch {
        browserFailed = true;
      }
    }
    if (!upgradeMic) {
      if (browserFailed) {
        stopRecording();
        setNotice("Voice input unavailable — type instead.");
      }
      return;
    }
    try {
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!current() || !holding.current) {
        media.getTracks().forEach((track) => track.stop());
        return;
      }
      stream.current = media;
      const rec = new MediaRecorder(media);
      recorder.current = rec;
      const chunks: BlobPart[] = [];
      rec.ondataavailable = (event) => chunks.push(event.data);
      rec.onstop = async () => {
        media.getTracks().forEach((track) => track.stop());
        if (!current() || !chunks.length) return;
        setTranscribing(true);
        try {
          const form = new FormData();
          form.append(
            "audio",
            new Blob(chunks, { type: rec.mimeType }),
            "question.webm",
          );
          const response = await fetch("/api/stt", {
            method: "POST",
            body: form,
          });
          if (!response.ok) throw new Error("Transcription unavailable");
          const data = await response.json();
          if (typeof data.text !== "string")
            throw new Error("Invalid transcript");
          if (current()) {
            if (recognition.current) recognition.current.onresult = null;
            recognition.current?.abort();
            onTranscript(data.text);
          }
        } catch {
          if (current())
            setNotice(
              browserText
                ? "Using browser transcript — edit before sending."
                : "Voice input unavailable — try the mic again or type instead.",
            );
        } finally {
          if (current()) setTranscribing(false);
        }
      };
      rec.start();
    } catch {
      if (current()) {
        stream.current?.getTracks().forEach((track) => track.stop());
        stream.current = null;
        setNotice(
          browserMic && !browserFailed
            ? "Using browser voice input."
            : "Microphone permission unavailable — type instead.",
        );
        if (!browserMic || browserFailed) stopRecording();
      }
    }
  }

  function toggleMute() {
    mutedRef.current = !mutedRef.current;
    setMuted(mutedRef.current);
    if (mutedRef.current) stopSpeech();
  }

  return {
    speak,
    stopSpeech,
    cancelRecording,
    beginRecord,
    endRecord: stopRecording,
    muted,
    toggleMute,
    talking,
    recording,
    transcribing,
    notice,
    micAvailable: browserMic || upgradeMic,
    micTooltip:
      browserMic || upgradeMic
        ? "Hold to talk, release to edit your question"
        : "Voice input works in Chrome/Edge — type instead",
  };
}
