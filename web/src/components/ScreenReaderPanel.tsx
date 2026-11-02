import type { Finding } from "../state/types";
import { CodeBadge, MetaBadge } from "./MetaBadge";

export function srQuote(f: Pick<Finding, "sr_role" | "sr_name">): string | null {
  if (!f.sr_role && !f.sr_name) return null;
  return `${f.sr_role}, "${f.sr_name}"`;
}

export const VOICE_GATE = 0.9; // spec §16 G-V: at or above it Voice is primary evidence, below it corroboration with the accuracy beside it

export function voiceStanding(accuracy: number | null | undefined): string {
  if (accuracy === null || accuracy === undefined) return "Transcript word accuracy not measured on this clip; corroboration only.";
  const pct = `${Math.round(100 * accuracy)}%`;
  return accuracy >= VOICE_GATE
    ? `Primary evidence: real VoiceOver audio, transcript word accuracy ${pct} against what VoiceOver spoke.`
    : `Corroboration: transcript word accuracy ${pct} against what VoiceOver spoke, below the 90% gate; the accessibility tree stays the evidence.`;
}

export function ScreenReaderPanel({ finding, voiceAccuracy }: { finding: Finding | null; voiceAccuracy?: number | null }) {
  const quote = finding ? srQuote(finding) : null;
  return (
    <section className="surface flex flex-col min-h-0 overflow-auto" aria-labelledby="sr-h" tabIndex={0}>
      <div className="flex items-center justify-between px-3 py-2 border-b hairline">
        <h2 id="sr-h" className="text-xs uppercase tracking-wider muted font-medium m-0">Screen reader</h2>
        <CodeBadge what="AX tree · deterministic" />
      </div>
      <div className="p-4 flex flex-col gap-4">
        {!finding ? (
          <p className="muted m-0">Select a finding to see what a screen reader announces for it.</p>
        ) : (
          <>
            <div>
              <div className="text-xs uppercase tracking-wider muted mb-1">On screen</div>
              <div className="sr-pair price-line">{finding.sighted_text}</div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wider muted mb-1">Announced</div>
              <div className="sr-pair sr-quote" aria-live="polite">
                {quote ?? <span className="sr-silent">— not announced —</span>}
              </div>
            </div>
            {finding.why_it_matters && !finding.judgement?.impact && <p className="m-0 muted">{finding.why_it_matters}</p>}
            {finding.judgement?.impact && (
              <p className="m-0 flex flex-col gap-1">
                <span>{finding.judgement.impact}</span>
                <span><MetaBadge model={String(finding.judgement.model_meta?.model ?? "muse-spark-1.3")} capability="judge" /></span>
              </p>
            )}
            {finding.voice && (
              <div aria-label="VoiceOver evidence">
                <div className="text-xs uppercase tracking-wider muted mb-1">VoiceOver, recorded on this page</div>
                <audio controls preload="metadata" aria-label="VoiceOver reading this element" src={`/store/voice/${finding.voice.clip_key}#t=${finding.voice.start_ms / 1000},${finding.voice.end_ms / 1000}`} />
                <div className="mono text-sm mt-1">{finding.voice.transcript}</div>
                <div className="text-sm mt-1">
                  <span aria-hidden="true">{finding.voice.agrees ? "✓" : "✗"}</span> {finding.voice.agrees ? "Transcript agrees with the accessibility tree" : "Transcript differs from the accessibility tree"}
                </div>
                <div className="mt-1"><MetaBadge model="muse-voice-transcribe-1.0" capability="real VoiceOver audio" /></div>
                <p className="text-xs muted mt-1 mb-0">{voiceStanding(voiceAccuracy)} Recorded store pages only: Live runs on the hosted app do not run VoiceOver.</p>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
