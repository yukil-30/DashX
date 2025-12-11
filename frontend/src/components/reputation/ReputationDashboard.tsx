import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Alert, 
  AlertDescription, 
  AlertTitle 
} from '@/components/ui/alert';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { 
  Users,
  UserCheck,
  UserX,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  Award,
  Star,
  RefreshCw,
  ChevronRight
} from 'lucide-react';
import { 
  ReputationDashboardStats, 
  EmployeeReputationSummary,
  CustomerWarningSummary,
  EmployeeListWithReputationResponse,
  CustomerListWithWarningsResponse
} from '@/types/api';
import { apiService } from '@/lib/api';

export function ReputationDashboard() {
  const [stats, setStats] = useState<ReputationDashboardStats | null>(null);
  const [employees, setEmployees] = useState<EmployeeReputationSummary[]>([]);
  const [customers, setCustomers] = useState<CustomerWarningSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [evaluating, setEvaluating] = useState(false);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  async function fetchDashboardData() {
    try {
      setLoading(true);
      setError(null);
      
      const [statsData, employeesData, customersData] = await Promise.all([
        apiService.get<ReputationDashboardStats>('/complaints/reputation/dashboard'),
        apiService.get<EmployeeListWithReputationResponse>('/complaints/reputation/employees?limit=10'),
        apiService.get<CustomerListWithWarningsResponse>('/complaints/reputation/customers?at_risk_only=true&limit=10')
      ]);
      
      setStats(statsData);
      setEmployees(employeesData.employees);
      setCustomers(customersData.customers);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load dashboard data';
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  async function runEvaluation() {
    try {
      setEvaluating(true);
      await apiService.post('/complaints/reputation/evaluate-all', {});
      await fetchDashboardData();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Evaluation failed';
      setError(message);
    } finally {
      setEvaluating(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse grid grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Reputation Dashboard</h2>
          <p className="text-muted-foreground">Monitor employee and customer reputation metrics</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchDashboardData}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={runEvaluation} disabled={evaluating}>
            {evaluating ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                Evaluating...
              </>
            ) : (
              <>
                <TrendingUp className="w-4 h-4 mr-2" />
                Run Evaluation
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Employee Stats */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-blue-500" />
              <span className="text-sm font-medium">Total Employees</span>
            </div>
            <p className="text-2xl font-bold mt-2">{stats.total_employees}</p>
            <p className="text-xs text-muted-foreground">
              {stats.active_employees} active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-yellow-500" />
              <span className="text-sm font-medium">At Risk</span>
            </div>
            <p className="text-2xl font-bold mt-2 text-yellow-600">
              {stats.employees_near_demotion}
            </p>
            <p className="text-xs text-muted-foreground">
              {stats.employees_near_firing} near firing
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <Award className="w-4 h-4 text-purple-500" />
              <span className="text-sm font-medium">Bonus Eligible</span>
            </div>
            <p className="text-2xl font-bold mt-2 text-purple-600">
              {stats.employees_bonus_eligible}
            </p>
            <p className="text-xs text-muted-foreground">
              {stats.recent_bonuses} recent bonuses
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <UserX className="w-4 h-4 text-red-500" />
              <span className="text-sm font-medium">Fired</span>
            </div>
            <p className="text-2xl font-bold mt-2 text-red-600">
              {stats.fired_employees}
            </p>
            <p className="text-xs text-muted-foreground">
              {stats.recent_firings} this week
            </p>
          </CardContent>
        </Card>

        {/* Customer Stats */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <UserCheck className="w-4 h-4 text-green-500" />
              <span className="text-sm font-medium">Total Customers</span>
            </div>
            <p className="text-2xl font-bold mt-2">{stats.total_customers}</p>
            <p className="text-xs text-muted-foreground">
              {stats.vip_customers} VIPs
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-orange-500" />
              <span className="text-sm font-medium">With Warnings</span>
            </div>
            <p className="text-2xl font-bold mt-2 text-orange-600">
              {stats.customers_with_warnings}
            </p>
            <p className="text-xs text-muted-foreground">
              {stats.customers_near_deregistration} near threshold
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-red-500" />
              <span className="text-sm font-medium">Deregistered</span>
            </div>
            <p className="text-2xl font-bold mt-2 text-red-600">
              {stats.deregistered_customers}
            </p>
            <p className="text-xs text-muted-foreground">
              {stats.recent_deregistrations} this week
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-blue-500" />
              <span className="text-sm font-medium">Pending</span>
            </div>
            <p className="text-2xl font-bold mt-2">{stats.pending_complaints}</p>
            <p className="text-xs text-muted-foreground">
              {stats.pending_disputes} disputes
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs for detailed views */}
      <Tabs defaultValue="employees" className="w-full">
        <TabsList>
          <TabsTrigger value="employees">Employees</TabsTrigger>
          <TabsTrigger value="customers">At-Risk Customers</TabsTrigger>
        </TabsList>

        <TabsContent value="employees" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Employee Reputation</CardTitle>
              <CardDescription>Monitor ratings, complaints, and status</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Employee</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Rating</TableHead>
                    <TableHead>Complaints</TableHead>
                    <TableHead>Compliments</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {employees.map((emp) => (
                    <TableRow key={emp.employee_id}>
                      <TableCell className="font-medium">{emp.email}</TableCell>
                      <TableCell className="capitalize">{emp.type}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Star className={`w-4 h-4 ${emp.rolling_avg_rating >= 4 ? 'text-green-500' : emp.rolling_avg_rating >= 2 ? 'text-yellow-500' : 'text-red-500'}`} />
                          <span>{emp.rolling_avg_rating.toFixed(1)}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={emp.complaint_count >= 2 ? 'destructive' : 'secondary'}>
                          {emp.complaint_count}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="bg-green-100 text-green-800">
                          {emp.compliment_count}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {emp.is_fired ? (
                          <Badge variant="destructive">Fired</Badge>
                        ) : emp.near_firing ? (
                          <Badge variant="destructive">At Risk</Badge>
                        ) : emp.near_demotion ? (
                          <Badge className="bg-yellow-100 text-yellow-800">Warning</Badge>
                        ) : emp.bonus_eligible ? (
                          <Badge className="bg-purple-100 text-purple-800">Bonus</Badge>
                        ) : (
                          <Badge className="bg-green-100 text-green-800">Good</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm">
                          <ChevronRight className="w-4 h-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="customers" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>At-Risk Customers</CardTitle>
              <CardDescription>Customers approaching warning thresholds</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Customer</TableHead>
                    <TableHead>Tier</TableHead>
                    <TableHead>Warnings</TableHead>
                    <TableHead>Threshold</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {customers.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                        No at-risk customers
                      </TableCell>
                    </TableRow>
                  ) : (
                    customers.map((cust) => (
                      <TableRow key={cust.customer_id}>
                        <TableCell className="font-medium">{cust.email}</TableCell>
                        <TableCell className="capitalize">{cust.customer_tier}</TableCell>
                        <TableCell>
                          <Badge variant={cust.near_threshold ? 'destructive' : 'secondary'}>
                            {cust.warning_count}
                          </Badge>
                        </TableCell>
                        <TableCell>{cust.threshold}</TableCell>
                        <TableCell>
                          {cust.is_blacklisted ? (
                            <Badge variant="destructive">Blacklisted</Badge>
                          ) : cust.near_threshold ? (
                            <Badge variant="destructive">Critical</Badge>
                          ) : cust.has_active_dispute ? (
                            <Badge className="bg-blue-100 text-blue-800">Disputed</Badge>
                          ) : (
                            <Badge className="bg-yellow-100 text-yellow-800">Warning</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm">
                            <ChevronRight className="w-4 h-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default ReputationDashboard;
