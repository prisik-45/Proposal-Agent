import React from 'react'
import { ProposalConversationResponse, ExtractedParams } from '../types'

interface ParametersDisplayProps {
  params: ExtractedParams | null
  result: ProposalConversationResponse | null
}

const ParametersDisplay: React.FC<ParametersDisplayProps> = ({ params, result }) => {
  if (!params && !result) return null

  const pdfUrl = result?.drive_link || result?.pdf_data_url || null

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="bg-gray-800 text-white rounded-lg p-4">
        <h2 className="text-sm">Proposal Details</h2>
      </div>

      {/* Extracted Parameters */}
      {params && (
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 space-y-3">
          <h3 className="text-sm text-gray-100">Extracted Parameters</h3>
          
          {params.client_business_name && (
            <div>
              <p className="text-xs text-gray-400">Client</p>
              <p className="text-sm text-gray-100">{params.client_business_name}</p>
            </div>
          )}

          {params.client_requirements && (
            <div>
              <p className="text-xs text-gray-400">Requirements</p>
              <p className="text-sm text-gray-300 line-clamp-3">{params.client_requirements}</p>
            </div>
          )}

          {params.timeline_days && (
            <div>
              <p className="text-xs text-gray-400">Timeline</p>
              <p className="text-sm text-gray-100">{params.timeline_days} days</p>
            </div>
          )}

          {(params.price_min || params.price_max) && (
            <div>
              <p className="text-xs text-gray-400">Budget</p>
              <p className="text-sm text-gray-100">
                ₹{params.price_min} - ₹{params.price_max}
              </p>
            </div>
          )}

          {params.includes_text && (
            <div>
              <p className="text-xs text-gray-400">Includes</p>
              <p className="text-sm text-gray-300 line-clamp-3">{params.includes_text}</p>
            </div>
          )}

          {params.technology_stack_text && (
            <div>
              <p className="text-xs text-gray-400">Technology Stack</p>
              <p className="text-sm text-gray-300 line-clamp-3">{params.technology_stack_text}</p>
            </div>
          )}

          {/* Word Limits */}
          <div className="border-t border-gray-700 pt-3">
            <p className="text-xs text-gray-400 mb-2">Word Limits</p>
            <div className="space-y-1 text-xs">
              {params.scope_of_work_max_words && (
                <p className="text-gray-300">Scope: {params.scope_of_work_max_words} words</p>
              )}
              {params.project_objective_max_words && (
                <p className="text-gray-300">Objective: {params.project_objective_max_words} words</p>
              )}
              {params.technology_stack_max_words && (
                <p className="text-gray-300">Tech Stack: {params.technology_stack_max_words} words</p>
              )}
              {params.additional_notes_max_words && (
                <p className="text-gray-300">Notes: {params.additional_notes_max_words} words</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Result Status */}
      {result && (
        <div className={`rounded-lg border p-4 ${result.success ? 'bg-green-950 border-green-800' : 'bg-red-950 border-red-800'}`}>
          <h3 className={`text-sm ${result.success ? 'text-green-300' : 'text-red-300'}`}>
            {result.success ? 'Success' : 'Error'}
          </h3>
          <p className={`text-xs mt-2 ${result.success ? 'text-green-200' : 'text-red-200'}`}>
            {result.message}
          </p>

          {result.changed_fields && result.changed_fields.length > 0 && (
            <div className="mt-3 text-xs text-gray-300">
              <p className="text-gray-400">Changed Fields</p>
              <ul className="list-disc list-inside space-y-1">
                {result.changed_fields.map((field) => (
                  <li key={field}>{field}</li>
                ))}
              </ul>
            </div>
          )}


          {result.success && pdfUrl && (
            <a
              href={pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-3 bg-gray-700 hover:bg-gray-600 text-white text-xs py-2 px-3 rounded transition-colors"
            >
              View PDF
            </a>
          )}

          {result.error && (
            <div className={`text-xs mt-2 p-2 rounded ${result.success ? 'bg-green-100' : 'bg-red-100'}`}>
              <code className={result.success ? 'text-green-800' : 'text-red-800'}>
                {result.error}
              </code>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ParametersDisplay
