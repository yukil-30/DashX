interface LoadingSkeletonProps {
  variant?: 'card' | 'text' | 'circle' | 'rect';
  width?: string;
  height?: string;
  className?: string;
  count?: number;
}

export default function LoadingSkeleton({
  variant = 'rect',
  width,
  height,
  className = '',
  count = 1,
}: LoadingSkeletonProps) {
  const skeletonClass = {
    card: 'rounded-xl',
    text: 'rounded',
    circle: 'rounded-full',
    rect: 'rounded-lg',
  }[variant];

  const defaultHeight = {
    card: 'h-80',
    text: 'h-4',
    circle: 'h-12 w-12',
    rect: 'h-48',
  }[variant];

  const skeleton = (
    <div
      className={`animate-pulse bg-gray-300 ${skeletonClass} ${defaultHeight} ${className}`}
      style={{ width: width, height: height }}
    />
  );

  if (count === 1) {
    return skeleton;
  }

  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="mb-4">
          {skeleton}
        </div>
      ))}
    </>
  );
}

export function DishCardSkeleton() {
  return (
    <div className="card animate-pulse">
      {/* Image skeleton */}
      <div className="h-48 bg-gray-300 rounded-t-xl" />
      
      <div className="p-4 space-y-3">
        {/* Title skeleton */}
        <div className="h-6 bg-gray-300 rounded w-3/4" />
        
        {/* Description skeleton */}
        <div className="space-y-2">
          <div className="h-4 bg-gray-300 rounded" />
          <div className="h-4 bg-gray-300 rounded w-5/6" />
        </div>
        
        {/* Price and rating skeleton */}
        <div className="flex justify-between items-center pt-2">
          <div className="h-6 bg-gray-300 rounded w-20" />
          <div className="h-4 bg-gray-300 rounded w-24" />
        </div>
        
        {/* Button skeleton */}
        <div className="h-10 bg-gray-300 rounded-lg w-full" />
      </div>
    </div>
  );
}

export function DishDetailSkeleton() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-8 animate-pulse">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Image carousel skeleton */}
        <div className="h-96 bg-gray-300 rounded-xl" />
        
        {/* Details skeleton */}
        <div className="space-y-4">
          <div className="h-8 bg-gray-300 rounded w-3/4" />
          <div className="h-6 bg-gray-300 rounded w-32" />
          <div className="space-y-2">
            <div className="h-4 bg-gray-300 rounded" />
            <div className="h-4 bg-gray-300 rounded" />
            <div className="h-4 bg-gray-300 rounded w-4/5" />
          </div>
          <div className="h-12 bg-gray-300 rounded-lg" />
        </div>
      </div>
    </div>
  );
}
