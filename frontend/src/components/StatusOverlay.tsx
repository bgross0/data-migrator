import { useEffect, useRef } from 'react'

export interface StatusStep {
  id: string
  label: string
  status: 'pending' | 'in_progress' | 'complete' | 'error'
  detail?: string
}

export interface StatusOverlayProps {
  isOpen: boolean
  title: string
  steps: StatusStep[]
  progress: number  // 0-100
  estimatedTime?: string
  onClose?: () => void
  canClose?: boolean
}

export default function StatusOverlay({
  isOpen,
  title,
  steps,
  progress,
  estimatedTime,
  onClose,
  canClose = false
}: StatusOverlayProps) {
  const stepsContainerRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to current step
  useEffect(() => {
    if (!stepsContainerRef.current) return

    const inProgressStep = stepsContainerRef.current.querySelector('[data-status="in_progress"]')
    if (inProgressStep) {
      inProgressStep.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [steps])

  if (!isOpen) return null

  const hasError = steps.some(s => s.status === 'error')
  const isComplete = steps.every(s => s.status === 'complete' || s.status === 'error')

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 animate-scale-in">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
              hasError ? 'bg-red-100' : isComplete ? 'bg-green-100' : 'bg-blue-100'
            }`}>
              {hasError ? (
                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : isComplete ? (
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className="animate-spin h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              )}
            </div>
            <div>
              <h2 className="text-2xl font-bold">{title}</h2>
              {estimatedTime && !isComplete && (
                <p className="text-sm text-gray-500">{estimatedTime}</p>
              )}
            </div>
          </div>

          {canClose && isComplete && onClose && (
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Progress Bar */}
        {!hasError && !isComplete && (
          <div className="mb-6">
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-600 transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-sm text-gray-600 mt-2 text-center">{Math.round(progress)}% complete</p>
          </div>
        )}

        {/* Steps */}
        <div
          ref={stepsContainerRef}
          className="space-y-3 max-h-80 overflow-y-auto pr-2"
        >
          {steps.map(step => (
            <div
              key={step.id}
              className="flex items-start gap-3 transition-all duration-300"
              data-status={step.status}
            >
              {/* Icon based on status */}
              <div className="flex-shrink-0 mt-0.5">
                {step.status === 'complete' && (
                  <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                )}
                {step.status === 'in_progress' && (
                  <svg className="animate-spin h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                {step.status === 'pending' && (
                  <div className="w-5 h-5 rounded-full border-2 border-gray-300 flex items-center justify-center">
                    <div className="w-2 h-2 rounded-full bg-gray-300"></div>
                  </div>
                )}
                {step.status === 'error' && (
                  <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                )}
              </div>

              {/* Label */}
              <div className="flex-1 min-w-0">
                <p className={`font-medium transition-colors ${
                  step.status === 'in_progress' ? 'text-blue-600' :
                  step.status === 'complete' ? 'text-gray-700' :
                  step.status === 'error' ? 'text-red-600' :
                  'text-gray-400'
                }`}>
                  {step.label}
                </p>
                {step.detail && (
                  <p className="text-sm text-gray-500 mt-0.5">{step.detail}</p>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Error message */}
        {hasError && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <h4 className="font-semibold text-red-800 mb-1">Operation Failed</h4>
            <p className="text-sm text-red-600">
              {steps.find(s => s.status === 'error')?.detail || 'An error occurred during processing.'}
            </p>
          </div>
        )}

        {/* Success message */}
        {isComplete && !hasError && (
          <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <h4 className="font-semibold text-green-800 mb-1">✓ Operation Complete</h4>
            <p className="text-sm text-green-600">
              All steps completed successfully.
            </p>
          </div>
        )}
      </div>

      {/* CSS animations - using style tag without jsx prop */}
      <style>{`
        @keyframes fade-in {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }

        @keyframes scale-in {
          from {
            transform: scale(0.95);
            opacity: 0;
          }
          to {
            transform: scale(1);
            opacity: 1;
          }
        }

        .animate-fade-in {
          animation: fade-in 0.2s ease-out;
        }

        .animate-scale-in {
          animation: scale-in 0.3s ease-out;
        }
      `}</style>
    </div>
  )
}
