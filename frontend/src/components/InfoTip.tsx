import React, { useState } from 'react';

/**
 * Small "?" help marker with a hover/focus tooltip. Theme-agnostic (fixed dark
 * bubble), and resets text-transform/letter-spacing so it reads normally even
 * inside an uppercase label. Tooltip opens BELOW the marker to avoid clipping
 * at the top of the viewport.
 */
const InfoTip: React.FC<{ text: string; size?: number }> = ({ text, size = 13 }) => {
  const [open, setOpen] = useState(false);
  return (
    <span
      style={{ position: 'relative', display: 'inline-flex', verticalAlign: 'middle', marginLeft: 5 }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <span
        role="img"
        aria-label={text}
        tabIndex={0}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        style={{
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          width: size, height: size, borderRadius: '50%',
          border: '1px solid var(--ink-400, #9ca3af)', color: 'var(--ink-500, #6b7280)',
          fontSize: size - 4, fontWeight: 700, lineHeight: 1, cursor: 'help',
          fontFamily: 'inherit', textTransform: 'none', letterSpacing: 'normal',
          flexShrink: 0,
        }}
      >
        ?
      </span>
      {open && (
        <span
          role="tooltip"
          style={{
            position: 'absolute', top: '150%', left: '50%', transform: 'translateX(-50%)',
            width: 240, zIndex: 60,
            background: '#1f2937', color: '#f9fafb',
            fontSize: 11, lineHeight: 1.5, fontWeight: 400,
            padding: '8px 10px', borderRadius: 6,
            boxShadow: '0 8px 24px rgba(0,0,0,0.22)',
            textTransform: 'none', letterSpacing: 'normal',
            whiteSpace: 'normal', textAlign: 'left', pointerEvents: 'none',
          }}
        >
          {text}
        </span>
      )}
    </span>
  );
};

export default InfoTip;
