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
    <div className="absolute bottom-full left-0 mb-2 w-64 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-xl z-50 overflow-hidden transform transition-all">

      <div className="max-h-48 overflow-y-auto py-1">
        {suggestions.map((suggestion, index) => (
          <button
            key={suggestion.mention}
            onClick={() => onSelect(suggestion)}
            onMouseEnter={() => onHover(index)}
            className={`clickable-scale w-full text-left px-3 py-2 transition-colors flex items-center gap-3 ${index === selectedIndex
              ? 'bg-teal-50 dark:bg-teal-900/40'
              : 'hover:bg-gray-50 dark:hover:bg-slate-800'
              }`}
          >
            {/* Agent Icon */}
            <div className={`size-6 rounded-md flex items-center justify-center flex-shrink-0 ${index === selectedIndex
              ? 'bg-teal-100 dark:bg-teal-800 text-teal-600 dark:text-teal-200'
              : 'bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-gray-400'
              }`}>
              <span className="material-symbols-outlined text-[16px]">
                {suggestion.icon}
              </span>
            </div>

            {/* Agent Info */}
            <div className="min-w-0">
              <div className={`text-xs font-medium truncate ${index === selectedIndex
                ? 'text-teal-700 dark:text-teal-100'
                : 'text-gray-700 dark:text-gray-200'
                }`}>
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
