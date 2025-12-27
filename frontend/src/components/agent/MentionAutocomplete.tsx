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
    <div className="absolute bottom-full left-0 mb-2 w-full max-w-md bg-slate-800 border border-slate-700 rounded-lg shadow-2xl z-50 overflow-hidden">
      <div className="p-2 border-b border-slate-700 bg-slate-900/50">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="material-symbols-outlined text-[16px]">alternate_email</span>
          <span>Mention Agent</span>
          <span className="ml-auto text-slate-500">↑↓ navigate • ↵ select</span>
        </div>
      </div>

      <div className="max-h-64 overflow-y-auto">
        {suggestions.map((suggestion, index) => (
          <button
            key={suggestion.mention}
            onClick={() => onSelect(suggestion)}
            onMouseEnter={() => onHover(index)}
            className={`w-full text-left px-4 py-3 transition-colors ${
              index === selectedIndex
                ? 'bg-purple-600 text-white'
                : 'hover:bg-slate-700 text-slate-200'
            }`}
          >
            <div className="flex items-start gap-3">
              {/* Agent Icon */}
              <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                index === selectedIndex
                  ? 'bg-white/20'
                  : 'bg-gradient-to-br from-purple-500 to-blue-600'
              }`}>
                <span className="material-symbols-outlined text-white text-[20px]">
                  {suggestion.icon}
                </span>
              </div>

              {/* Agent Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm font-mono">{suggestion.mention}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    index === selectedIndex
                      ? 'bg-white/20'
                      : 'bg-slate-700'
                  }`}>
                    {suggestion.agent_id}
                  </span>
                </div>
                <p className={`text-xs mt-0.5 font-medium ${
                  index === selectedIndex ? 'text-purple-100' : 'text-slate-300'
                }`}>
                  {suggestion.name}
                </p>
                <p className={`text-xs mt-1 ${
                  index === selectedIndex ? 'text-purple-200/80' : 'text-slate-500'
                }`}>
                  {suggestion.description}
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

export default MentionAutocomplete;
