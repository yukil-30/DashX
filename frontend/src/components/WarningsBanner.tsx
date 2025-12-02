

interface WarningsBannerProps {
  warningsCount: number;
  message: string | null;
  isNearThreshold: boolean;
  onDismiss: () => void;
}

export default function WarningsBanner({
  warningsCount,
  message,
  isNearThreshold,
  onDismiss,
}: WarningsBannerProps) {
  if (warningsCount === 0) return null;

  return (
    <div
      className={`rounded-lg p-4 mb-4 flex items-start gap-3 ${
        isNearThreshold
          ? 'bg-red-50 border-2 border-red-400'
          : 'bg-yellow-50 border-2 border-yellow-400'
      }`}
      role="alert"
    >
      <span className="text-2xl flex-shrink-0">
        {isNearThreshold ? '🚨' : '⚠️'}
      </span>
      <div className="flex-1">
        <p
          className={`font-semibold ${
            isNearThreshold ? 'text-red-800' : 'text-yellow-800'
          }`}
        >
          {message || `You have ${warningsCount} warning${warningsCount > 1 ? 's' : ''}`}
        </p>
        <p className="text-sm text-gray-700 mt-1">
          Please contact support if you believe this is an error.
        </p>
      </div>
      <button
        onClick={onDismiss}
        className="text-gray-500 hover:text-gray-700 text-xl font-bold"
        aria-label="Dismiss warning"
      >
        ×
      </button>
    </div>
  );
}
