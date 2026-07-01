import { CommandAutocompleteResult } from '../../types/agent';

interface CommandAutocompleteProps {
  suggestions: CommandAutocompleteResult[];
  selectedIndex: number;
  onSelect: (suggestion: CommandAutocompleteResult) => void;
  onHover: (index: number) => void;
}

/**
 * Command Autocomplete Dropdown
 *
 * Shows slash command suggestions as user types.
 * Displays command, description, and example.
 */
export function CommandAutocomplete({
  suggestions,
  selectedIndex,
  onSelect,
  onHover
}: CommandAutocompleteProps) {
  if (suggestions.length === 0) return null;

  return (
    <div
      className="absolute bottom-full left-0 mb-2 w-72 z-50 overflow-hidden transform transition-all"
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-card)',
        boxShadow: '0 10px 30px -12px rgba(0,0,0,0.28)'
      }}
    >
      <div className="max-h-64 overflow-y-auto py-1">
        {suggestions.map((suggestion, index) => (
          <button
            key={suggestion.command}
            onClick={() => onSelect(suggestion)}
            onMouseEnter={() => onHover(index)}
            className="clickable-scale qp-transition w-full text-left px-3 py-2.5 flex items-center gap-3"
            style={{
              background: index === selectedIndex ? 'var(--accent-soft)' : 'transparent'
            }}
          >
            {/* Icon */}
            <div
              className="size-8 flex items-center justify-center flex-shrink-0"
              style={{
                borderRadius: 'var(--radius-ctl)',
                background: index === selectedIndex ? 'var(--accent)' : 'var(--surface-2)',
                color: index === selectedIndex ? 'var(--accent-ink)' : 'var(--ink-500)'
              }}
            >
              <span className="material-symbols-outlined text-[18px]">
                {getCategoryIcon(suggestion.category || 'general')}
              </span>
            </div>

            {/* Info */}
            <div className="min-w-0 flex-1">
              <div
                className="text-sm font-medium font-mono"
                style={{ color: index === selectedIndex ? 'var(--accent)' : 'var(--ink-900)' }}
              >
                {suggestion.command}
              </div>
              <div
                className="text-xs truncate"
                style={{ color: index === selectedIndex ? 'var(--accent)' : 'var(--ink-500)' }}
              >
                {suggestion.description}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function getCategoryIcon(category: string): string {
  const icons: Record<string, string> = {
    communication: 'email',
    documents: 'description',
    meetings: 'event',
    analysis: 'analytics',
    general: 'terminal'
  };
  return icons[category] || 'terminal';
}

export default CommandAutocomplete;
