/**
 * SourceCitation component for displaying file references.
 */

import { useState } from 'react';
import type { SourceCitation as SourceCitationType } from '../types';
import { CodeBlock } from './CodeBlock';

interface SourceCitationProps {
  citation: SourceCitationType;
}

export function SourceCitation({ citation }: SourceCitationProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const getLanguage = (filePath: string): string => filePath.split('.').pop() || '';

  const relevancePercentage = Math.round(citation.relevance_score * 100);

  const getRelevanceColor = (score: number) => {
    if (score >= 0.8) return 'bg-emerald-400';
    if (score >= 0.6) return 'bg-amber-400';
    return 'bg-rose-400';
  };

  // Show a cleaner version of the file path
  const displayPath = citation.file_path.replace(/^\/tmp\/[^/]+\/repo\//, '');

  return (
    <div className="border border-slate-700/50 rounded-lg overflow-hidden bg-slate-800/30 hover:bg-slate-800/60 transition-colors">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2.5 flex items-center gap-3 text-left"
      >
        {/* File icon */}
        <svg className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>

        {/* Path + lines */}
        <div className="flex-1 min-w-0">
          <span className="text-xs font-mono text-slate-300 truncate block">{displayPath}</span>
          <span className="text-xs text-slate-500">Lines {citation.start_line}–{citation.end_line}</span>
        </div>

        {/* Relevance */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <div className="w-12 h-1 bg-slate-700 rounded-full overflow-hidden">
            <div
              className={`h-full ${getRelevanceColor(citation.relevance_score)} transition-all`}
              style={{ width: `${relevancePercentage}%` }}
            />
          </div>
          <span className="text-xs text-slate-500 w-7 text-right">{relevancePercentage}%</span>
        </div>

        {/* Chevron */}
        <svg
          className={`w-3.5 h-3.5 text-slate-600 flex-shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="border-t border-slate-700/50">
          <CodeBlock
            code={citation.text_snippet}
            language={getLanguage(citation.file_path)}
            showLineNumbers={false}
          />
        </div>
      )}
    </div>
  );
}
