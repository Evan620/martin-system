interface AgentMentionSuggestion {
  mention: string;
  agent_id: string;
  name: string;
  icon: string;
  description: string;
  match_score?: number;
}

interface MentionAutocompleteProps {
  suggestions: AgentMentionSuggestion[];
  selectedIndex: number;
  onSelect: (suggestion: AgentMentionSuggestion) => void;
  onHover: (index: number) => void;
}

/**
 * Agent Mention Autocomplete Dropdown
 *
 * Shows TWG agent suggestions when user types @.
 * Displays agent name, icon, and description.
 */
export function MentionAutocomplete({
  suggestions,
  selectedIndex,
  onSelect,
  onHover
}: MentionAutocompleteProps) {
  if (suggestions.length === 0) return null;

  return (
    <div
      className="absolute bottom-full left-0 mb-2 w-64 z-50 overflow-hidden transform transition-all"
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-card)',
      }}
    >

      <div className="max-h-48 overflow-y-auto py-1">
        {suggestions.map((suggestion, index) => (
          <button
            key={suggestion.mention}
            onClick={() => onSelect(suggestion)}
            onMouseEnter={() => onHover(index)}
            className="clickable-scale qp-transition w-full text-left px-3 py-2 flex items-center gap-3"
            style={{
              background: index === selectedIndex ? 'var(--accent-soft)' : 'transparent',
            }}
          >
            {/* Agent Icon */}
            <div
              className="size-6 rounded-md flex items-center justify-center flex-shrink-0"
              style={
                index === selectedIndex
                  ? { background: 'var(--accent)', color: 'var(--accent-ink)' }
                  : { background: 'var(--surface-2)', color: 'var(--ink-500)' }
              }
            >
              <span className="material-symbols-outlined text-[16px]">
                {suggestion.icon}
              </span>
            </div>

            {/* Agent Info */}
            <div className="min-w-0">
              <div
                className="text-xs font-medium truncate"
                style={{ color: index === selectedIndex ? 'var(--accent)' : 'var(--ink-700)' }}
              >
                {suggestion.mention}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

export default MentionAutocomplete;
