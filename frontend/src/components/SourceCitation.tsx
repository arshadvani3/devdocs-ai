/**
 * SourceCitation component for displaying file references.
 * Shows file path, line numbers, and expandable code snippet.
 */

import { useState } from 'react';
import type { SourceCitation as SourceCitationType } from '../types';
import { CodeBlock } from './CodeBlock';

interface SourceCitationProps {
  citation: SourceCitationType;
}

export function SourceCitation({ citation }: SourceCitationProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Extract language from file path
  const getLanguage = (filePath: string): string => {
    const extension = filePath.split('.').pop() || '';
    return extension;
  };

  // Format relevance score as percentage
  const relevancePercentage = Math.round(citation.relevance_score * 100);

  // Determine color based on relevance score
  const getRelevanceColor = (score: number): string => {
    if (score >= 0.8) return 'bg-green-500';
    if (score >= 0.6) return 'bg-yellow-500';
    return 'bg-orange-500';
  };

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden bg-gray-800/50 hover:bg-gray-800 transition-colors">
      {/* Header - clickable to expand/collapse */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-700/30 transition-colors"
      >
        <div className="flex-1 min-w-0">
          {/* File path */}
          <div className="flex items-center gap-2 mb-1">
            <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="text-sm font-mono text-gray-200 truncate">
              {citation.file_path}
            </span>
          </div>

          {/* Line numbers and relevance */}
          <div className="flex items-center gap-3 text-xs text-gray-400">
            <span className="font-mono">
              Lines {citation.start_line}-{citation.end_line}
            </span>
            <span className="flex items-center gap-1">
              <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full ${getRelevanceColor(citation.relevance_score)} transition-all`}
                  style={{ width: `${relevancePercentage}%` }}
                />
              </div>
              <span>{relevancePercentage}%</span>
            </span>
          </div>
        </div>

        {/* Expand/collapse icon */}
        <svg
          className={`w-5 h-5 text-gray-400 flex-shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded code snippet */}
      {isExpanded && (
        <div className="border-t border-gray-700">
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
