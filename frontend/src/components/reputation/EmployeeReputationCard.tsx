import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { 
  Star, 
  AlertTriangle, 
  TrendingUp, 
  TrendingDown, 
  Award,
  ThumbsUp,
  ThumbsDown,
  DollarSign
} from 'lucide-react';
import { EmployeeReputationSummary } from '@/types/api';
import { apiService } from '@/lib/api';

interface EmployeeReputationCardProps {
  employeeId?: number;  // If not provided, shows current user's reputation
  showFullDetails?: boolean;
}

export function EmployeeReputationCard({ employeeId, showFullDetails = true }: EmployeeReputationCardProps) {
  const [reputation, setReputation] = useState<EmployeeReputationSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchReputation() {
      try {
        setLoading(true);
        const endpoint = employeeId 
          ? `/complaints/reputation/employees/${employeeId}`
          : '/complaints/reputation/my-status';
        
        const data = await apiService.get<EmployeeReputationSummary>(endpoint);
        setReputation(data);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to load reputation data';
        setError(message);
      } finally {
        setLoading(false);
      }
    }

    fetchReputation();
  }, [employeeId]);

  if (loading) {
    return (
      <Card className="w-full">
        <CardContent className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="h-8 bg-gray-200 rounded w-1/2"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !reputation) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{error || 'Failed to load reputation data'}</AlertDescription>
      </Alert>
    );
  }

  const getStatusBadge = () => {
    switch (reputation.employment_status) {
      case 'fired':
        return <Badge variant="destructive">Fired</Badge>;
      case 'demoted':
        return <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">Demoted</Badge>;
      default:
        return <Badge variant="default" className="bg-green-100 text-green-800">Active</Badge>;
    }
  };

  const getRatingColor = (rating: number) => {
    if (rating >= 4) return 'text-green-600';
    if (rating >= 2) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getRatingProgress = (rating: number) => {
    return (rating / 5) * 100;
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <span className="capitalize">{reputation.type}</span> Profile
              {getStatusBadge()}
            </CardTitle>
            <CardDescription>{reputation.email}</CardDescription>
          </div>
          {reputation.bonus_eligible && (
            <Badge className="bg-purple-100 text-purple-800">
              <Award className="w-4 h-4 mr-1" />
              Bonus Eligible
            </Badge>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Warning Alert */}
        {reputation.status_warning && (
          <Alert variant={reputation.near_firing ? 'destructive' : 'default'} className={reputation.bonus_eligible ? 'border-purple-300 bg-purple-50' : ''}>
            {reputation.near_firing ? (
              <AlertTriangle className="h-4 w-4" />
            ) : reputation.bonus_eligible ? (
              <Award className="h-4 w-4" />
            ) : (
              <TrendingDown className="h-4 w-4" />
            )}
            <AlertTitle>
              {reputation.near_firing ? 'Critical Warning' : reputation.bonus_eligible ? 'Great Work!' : 'Warning'}
            </AlertTitle>
            <AlertDescription>{reputation.status_warning}</AlertDescription>
          </Alert>
        )}

        {/* Rating Section */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Average Rating</span>
            <span className={`text-2xl font-bold ${getRatingColor(reputation.rolling_avg_rating)}`}>
              {reputation.rolling_avg_rating.toFixed(2)}
              <Star className="w-5 h-5 inline ml-1 fill-current" />
            </span>
          </div>
          <Progress value={getRatingProgress(reputation.rolling_avg_rating)} className="h-2" />
          <p className="text-xs text-muted-foreground">
            Based on {reputation.total_rating_count} rating{reputation.total_rating_count !== 1 ? 's' : ''}
          </p>
        </div>

        {/* Stats Grid */}
        {showFullDetails && (
          <div className="grid grid-cols-2 gap-4">
            {/* Complaints */}
            <div className="p-4 rounded-lg bg-red-50 border border-red-100">
              <div className="flex items-center gap-2 text-red-700">
                <ThumbsDown className="w-4 h-4" />
                <span className="text-sm font-medium">Complaints</span>
              </div>
              <p className="text-2xl font-bold text-red-800 mt-1">
                {reputation.complaint_count}
              </p>
              <p className="text-xs text-red-600">
                {3 - reputation.complaint_count} until demotion
              </p>
            </div>

            {/* Compliments */}
            <div className="p-4 rounded-lg bg-green-50 border border-green-100">
              <div className="flex items-center gap-2 text-green-700">
                <ThumbsUp className="w-4 h-4" />
                <span className="text-sm font-medium">Compliments</span>
              </div>
              <p className="text-2xl font-bold text-green-800 mt-1">
                {reputation.compliment_count}
              </p>
              <p className="text-xs text-green-600">
                {3 - reputation.compliment_count} until bonus
              </p>
            </div>

            {/* Demotions */}
            <div className="p-4 rounded-lg bg-yellow-50 border border-yellow-100">
              <div className="flex items-center gap-2 text-yellow-700">
                <TrendingDown className="w-4 h-4" />
                <span className="text-sm font-medium">Demotions</span>
              </div>
              <p className="text-2xl font-bold text-yellow-800 mt-1">
                {reputation.demotion_count}
              </p>
              <p className="text-xs text-yellow-600">
                {2 - reputation.demotion_count} until termination
              </p>
            </div>

            {/* Bonuses */}
            <div className="p-4 rounded-lg bg-purple-50 border border-purple-100">
              <div className="flex items-center gap-2 text-purple-700">
                <Award className="w-4 h-4" />
                <span className="text-sm font-medium">Bonuses</span>
              </div>
              <p className="text-2xl font-bold text-purple-800 mt-1">
                {reputation.bonus_count}
              </p>
              <p className="text-xs text-purple-600">
                Total bonuses received
              </p>
            </div>
          </div>
        )}

        {/* Wage Info */}
        {showFullDetails && reputation.wage_cents !== null && (
          <div className="p-4 rounded-lg bg-gray-50 border">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <DollarSign className="w-4 h-4" />
                <span className="text-sm font-medium">Current Wage</span>
              </div>
              <span className="text-lg font-bold">
                ${(reputation.wage_cents / 100).toFixed(2)}/hr
              </span>
            </div>
          </div>
        )}

        {/* Risk Indicators */}
        {(reputation.near_demotion || reputation.near_firing) && (
          <div className="flex gap-2 flex-wrap">
            {reputation.near_demotion && (
              <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
                <AlertTriangle className="w-3 h-3 mr-1" />
                Near Demotion Threshold
              </Badge>
            )}
            {reputation.near_firing && (
              <Badge variant="destructive">
                <AlertTriangle className="w-3 h-3 mr-1" />
                At Risk of Termination
              </Badge>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default EmployeeReputationCard;
