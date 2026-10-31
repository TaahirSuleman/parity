import type { Finding } from "../state/types";
import { CodeBadge, MetaBadge } from "./MetaBadge";

export function srQuote(f: Pick<Finding, "sr_role" | "sr_name">): string | null {
  if (!f.sr_role && !f.sr_name) return null;
  return `${f.sr_role}, "${f.sr_name}"`;
}

export function ScreenReaderPanel({ finding }: { finding: Finding | null }) {
  const quote = finding ? srQuote(finding) : null;
  return (
    <section className="surface flex flex-col" aria-labelledby="sr-h">
      <div className="flex items-center justify-between px-3 py-2 border-b hairline">
        <h2 id="sr-h" className="text-xs uppercase tracking-wider muted font-medium m-0">Screen reader</h2>
        <CodeBadge what="AX tree · deterministic" />
      </div>
      <div className="p-4 flex flex-col gap-4">
        {!finding ? (
          <p className="muted m-0">Select a finding to hear what a screen reader announces for it.</p>
        ) : (
          <>
            <div>
              <div className="text-xs uppercase tracking-wider muted mb-1">Announced</div>
              <div className="sr-quote" aria-live="polite">
                {quote ?? <span className="sr-silent">— not announced —</span>}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wider muted mb-1">On screen</div>
              <div className="price-line">{finding.sighted_text}</div>
            </div>
            {finding.why_it_matters && <p className="m-0 muted">{finding.why_it_matters}</p>}
            {finding.judgement?.impact && (
              <p className="m-0 flex flex-col gap-1">
                <span>{finding.judgement.impact}</span>
                <span><MetaBadge model={String(finding.judgement.model_meta?.model ?? "muse-spark-1.3")} capability="judge" /></span>
              </p>
            )}
            {finding.voice && (
              <div>
                <div className="text-xs uppercase tracking-wider muted mb-1">VoiceOver</div>
                <audio controls src={`/store/voice/${finding.voice.clip_key}#t=${finding.voice.start_ms / 1000},${finding.voice.end_ms / 1000}`} />
                <div className="mono text-sm mt-1">{finding.voice.transcript}</div>
                <MetaBadge model="muse-voice-transcribe-1.0" capability="real VoiceOver audio" />
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
