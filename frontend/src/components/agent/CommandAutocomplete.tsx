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
    <div className="absolute bottom-full left-0 mb-2 w-full max-w-md bg-slate-800 border border-slate-700 rounded-lg shadow-2xl z-50 overflow-hidden">
      <div className="p-2 border-b border-slate-700 bg-slate-900/50">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="material-symbols-outlined text-[16px]">terminal</span>
          <span>Commands</span>
          <span className="ml-auto text-slate-500">↑↓ navigate • ↵ select</span>
        </div>
      </div>

      <div className="max-h-64 overflow-y-auto">
        {suggestions.map((suggestion, index) => (
          <button
            key={suggestion.command}
            onClick={() => onSelect(suggestion)}
            onMouseEnter={() => onHover(index)}
            className={`w-full text-left px-4 py-3 transition-colors ${
              index === selectedIndex
                ? 'bg-blue-600 text-white'
                : 'hover:bg-slate-700 text-slate-200'
            }`}
          >
            <div className="flex items-start gap-3">
              <span className="material-symbols-outlined text-[20px] mt-0.5">
                {getCategoryIcon(suggestion.category || 'general')}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm font-mono">{suggestion.command}</span>
                  {suggestion.category && (
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      index === selectedIndex
                        ? 'bg-white/20'
                        : 'bg-slate-700'
                    }`}>
                      {suggestion.category}
                    </span>
                  )}
                </div>
                <p className={`text-xs mt-0.5 ${
                  index === selectedIndex ? 'text-blue-100' : 'text-slate-400'
                }`}>
                  {suggestion.description}
                </p>
                {suggestion.examples && (
                  <p className={`text-xs mt-1 font-mono ${
                    index === selectedIndex ? 'text-blue-200/80' : 'text-slate-500'
                  }`}>
                    e.g., {suggestion.examples}
                  </p>
                )}
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
