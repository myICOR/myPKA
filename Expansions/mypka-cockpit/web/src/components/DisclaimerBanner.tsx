import { ShieldCheck } from 'lucide-react';

// Mandatory, prominent. Reference-range framing, NOT diagnosis. Calm, not alarmist.
export function DisclaimerBanner() {
  return (
    <div
      role="note"
      className="flex items-start gap-sm rounded-panel border border-border bg-surface-1 px-md py-sm"
    >
      <ShieldCheck size={20} strokeWidth={1.5} className="mt-[2px] shrink-0 text-marker-text" aria-hidden="true" />
      <p className="text-meta leading-relaxed text-fg-muted">
        <span className="font-[520] text-fg">An assessment against reference ranges</span>{' '}
        — not a diagnosis, not a medical opinion. The numbers are a calm look at the trend,
        not a finding. Every medical judgment belongs with your doctor.
      </p>
    </div>
  );
}
