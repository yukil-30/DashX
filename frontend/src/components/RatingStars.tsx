import { Star } from 'lucide-react';

interface RatingStarsProps {
  rating: number; // 0-5
  maxStars?: number;
  size?: 'sm' | 'md' | 'lg';
  showCount?: boolean;
  count?: number;
  onChange?: (rating: number) => void;
  readonly?: boolean;
}

export default function RatingStars({
  rating,
  maxStars = 5,
  size = 'md',
  showCount = false,
  count,
  onChange,
  readonly = true,
}: RatingStarsProps) {
  const sizeMap = {
    sm: 14,
    md: 18,
    lg: 24,
  };

  const textSizeClasses = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-xl',
  };

  const handleClick = (index: number) => {
    if (!readonly && onChange) {
      onChange(index + 1);
    }
  };

  const starSize = sizeMap[size];

  return (
    <div className="flex items-center gap-1">
      <div className="flex">
        {Array.from({ length: maxStars }).map((_, index) => {
          const isFilled = index < Math.floor(rating);
          const isHalf = !isFilled && index < rating;

          return (
            <button
              key={index}
              type="button"
              onClick={() => handleClick(index)}
              disabled={readonly}
              className={`${
                readonly ? 'cursor-default' : 'cursor-pointer hover:scale-110'
              } transition-transform`}
              aria-label={`Rate ${index + 1} stars`}
            >
              {isFilled ? (
                <Star size={starSize} className="text-yellow-400 fill-yellow-400" />
              ) : isHalf ? (
                <Star size={starSize} className="text-yellow-400 fill-yellow-200" />
              ) : (
                <Star size={starSize} className="text-gray-300" fill="none" />
              )}
            </button>
          );
        })}
      </div>
      {showCount && count !== undefined && (
        <span className={`${textSizeClasses[size]} text-gray-600 ml-1`}>
          ({count})
        </span>
      )}
    </div>
  );
}
