import React, { useEffect, useId, useRef, useState } from 'react';

interface InfoTooltipProps {
  /** Tooltip body. Plain text or JSX (e.g. a short bulleted definition). */
  text: React.ReactNode;
  /** Accessible label for the trigger icon. */
  ariaLabel?: string;
  /** Material Symbols icon name for the trigger (e.g. 'help' for a question mark). */
  icon?: string;
}

/**
 * Small (i) info icon that reveals a popover on hover (desktop) or tap (mobile).
 * Closes on outside click or Escape. Used to explain intake fields whose
 * Yes/No answer needs a threshold the submitter may not know.
 */
const InfoTooltip: React.FC<InfoTooltipProps> = ({ text, ariaLabel = 'More information', icon = 'info' }) => {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLSpanElement>(null);
  const tipId = useId();

  useEffect(() => {
    if (!open) return;
    const onDocClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <span
      ref={wrapRef}
      className="relative inline-flex items-center align-middle"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        aria-label={ariaLabel}
        aria-describedby={open ? tipId : undefined}
        onClick={(e) => { e.preventDefault(); setOpen(v => !v); }}
        className="material-symbols-outlined text-slate-400 hover:text-teal-500 transition-colors cursor-help leading-none"
        style={{ fontSize: '16px' }}
      >
        {icon}
      </button>
      {open && (
        <span
          id={tipId}
          role="tooltip"
          className="absolute z-50 left-1/2 -translate-x-1/2 top-full mt-2 w-72 max-w-[80vw] rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-xs leading-relaxed text-slate-700 dark:text-slate-200 shadow-lg"
        >
          {text}
        </span>
      )}
    </span>
  );
};

export default InfoTooltip;
