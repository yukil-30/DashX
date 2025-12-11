import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { 
  AlertTriangle, 
  AlertCircle,
  ShieldCheck,
  Crown,
  XCircle,
  MessageSquare
} from 'lucide-react';
import { CustomerWarningSummary } from '@/types/api';
import { apiService } from '@/lib/api';

interface CustomerWarningCardProps {
  showDisputeButton?: boolean;
  onDisputeClick?: () => void;
}

export function CustomerWarningCard({ showDisputeButton = true, onDisputeClick }: CustomerWarningCardProps) {
  const [warnings, setWarnings] = useState<CustomerWarningSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchWarnings() {
      try {
        setLoading(true);
        const data = await apiService.get<CustomerWarningSummary>('/complaints/reputation/my-warnings');
        setWarnings(data);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to load warning data';
        setError(message);
      } finally {
        setLoading(false);
      }
    }

    fetchWarnings();
  }, []);

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

  if (error || !warnings) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{error || 'Failed to load warning data'}</AlertDescription>
      </Alert>
    );
  }

  const getTierBadge = () => {
    switch (warnings.customer_tier) {
      case 'vip':
        return (
          <Badge className="bg-purple-100 text-purple-800">
            <Crown className="w-3 h-3 mr-1" />
            VIP
          </Badge>
        );
      case 'deregistered':
        return (
          <Badge variant="destructive">
            <XCircle className="w-3 h-3 mr-1" />
            Deregistered
          </Badge>
        );
      default:
        return (
          <Badge variant="secondary">
            <ShieldCheck className="w-3 h-3 mr-1" />
            Registered
          </Badge>
        );
    }
  };

  const getWarningColor = () => {
    if (warnings.warning_count === 0) return 'bg-green-50 border-green-200';
    if (warnings.near_threshold) return 'bg-red-50 border-red-200';
    return 'bg-yellow-50 border-yellow-200';
  };

  const getWarningTextColor = () => {
    if (warnings.warning_count === 0) return 'text-green-800';
    if (warnings.near_threshold) return 'text-red-800';
    return 'text-yellow-800';
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              Account Status
              {getTierBadge()}
            </CardTitle>
            <CardDescription>{warnings.email}</CardDescription>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Warning Count Display */}
        <div className={`p-6 rounded-lg border-2 ${getWarningColor()}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Warning Count</p>
              <p className={`text-4xl font-bold ${getWarningTextColor()}`}>
                {warnings.warning_count} / {warnings.threshold}
              </p>
            </div>
            <div className={`p-3 rounded-full ${warnings.warning_count === 0 ? 'bg-green-100' : warnings.near_threshold ? 'bg-red-100' : 'bg-yellow-100'}`}>
              {warnings.warning_count === 0 ? (
                <ShieldCheck className={`w-8 h-8 ${getWarningTextColor()}`} />
              ) : warnings.near_threshold ? (
                <AlertTriangle className={`w-8 h-8 ${getWarningTextColor()}`} />
              ) : (
                <AlertCircle className={`w-8 h-8 ${getWarningTextColor()}`} />
              )}
            </div>
          </div>
        </div>

        {/* Warning Message Alert */}
        {warnings.warning_message && (
          <Alert variant={warnings.near_threshold ? 'destructive' : 'default'}>
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>
              {warnings.near_threshold ? 'Critical Warning' : 'Account Notice'}
            </AlertTitle>
            <AlertDescription>
              {warnings.warning_message}
            </AlertDescription>
          </Alert>
        )}

        {/* Near Threshold Warning */}
        {warnings.near_threshold && !warnings.is_blacklisted && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Account at Risk</AlertTitle>
            <AlertDescription>
              {warnings.customer_tier === 'vip' 
                ? 'One more warning will result in losing your VIP status.'
                : 'One more warning will result in account suspension.'}
            </AlertDescription>
          </Alert>
        )}

        {/* Blacklisted Notice */}
        {warnings.is_blacklisted && (
          <Alert variant="destructive">
            <XCircle className="h-4 w-4" />
            <AlertTitle>Account Suspended</AlertTitle>
            <AlertDescription>
              Your account has been permanently suspended due to excessive warnings.
              Please contact support for more information.
            </AlertDescription>
          </Alert>
        )}

        {/* Active Dispute Notice */}
        {warnings.has_active_dispute && (
          <Alert>
            <MessageSquare className="h-4 w-4" />
            <AlertTitle>Dispute Pending</AlertTitle>
            <AlertDescription>
              You have an active dispute being reviewed by management.
            </AlertDescription>
          </Alert>
        )}

        {/* Good Standing Message */}
        {warnings.warning_count === 0 && (
          <Alert className="border-green-200 bg-green-50">
            <ShieldCheck className="h-4 w-4 text-green-600" />
            <AlertTitle className="text-green-800">Good Standing</AlertTitle>
            <AlertDescription className="text-green-700">
              Your account is in good standing with no warnings.
            </AlertDescription>
          </Alert>
        )}

        {/* Dispute Button */}
        {showDisputeButton && warnings.warning_count > 0 && !warnings.is_blacklisted && (
          <Button 
            variant="outline" 
            className="w-full"
            onClick={onDisputeClick}
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            View & Dispute Complaints
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

export default CustomerWarningCard;
