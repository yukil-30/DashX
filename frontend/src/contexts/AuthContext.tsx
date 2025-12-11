import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import toast from 'react-hot-toast';
import apiClient from '../lib/api-client';
import { User, LoginRequest, RegisterRequest, LoginResponse, ProfileResponse, ComplaintListResponse } from '../types/api';

interface WarningInfo {
  warnings_count: number;
  warning_message: string | null;
  is_near_threshold: boolean;
}

interface ComplaintInfo {
  pendingComplaintsAgainstMe: number;
  pendingComplimentsAgainstMe: number;
  pendingComplaintsFiled: number;
  pendingComplimentsFiled: number;
  totalAgainstMe: number;
  totalFiled: number;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  warningInfo: WarningInfo | null;
  complaintInfo: ComplaintInfo | null;
  loading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
  refreshComplaintInfo: () => Promise<ComplaintInfo | null>;
  dismissWarning: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [warningInfo, setWarningInfo] = useState<WarningInfo | null>(null);
  const [complaintInfo, setComplaintInfo] = useState<ComplaintInfo | null>(null);
  const [loading, setLoading] = useState(true);

  // Load user profile on mount if token exists
  useEffect(() => {
    if (token) {
      refreshProfile();
    } else {
      setLoading(false);
    }
  }, [token]);

  const refreshComplaintInfo = async () => {
    try {
      const [againstResponse, filedResponse] = await Promise.all([
        apiClient.get<ComplaintListResponse>('/complaints/my/against'),
        apiClient.get<ComplaintListResponse>('/complaints/my/filed'),
      ]);

      // Count pending complaints vs compliments separately
      const pendingAgainst = againstResponse.data.complaints.filter(c => c.status === 'pending');
      const pendingFiled = filedResponse.data.complaints.filter(c => c.status === 'pending');

      const info: ComplaintInfo = {
        pendingComplaintsAgainstMe: pendingAgainst.filter(c => c.type === 'complaint').length,
        pendingComplimentsAgainstMe: pendingAgainst.filter(c => c.type === 'compliment').length,
        pendingComplaintsFiled: pendingFiled.filter(c => c.type === 'complaint').length,
        pendingComplimentsFiled: pendingFiled.filter(c => c.type === 'compliment').length,
        totalAgainstMe: againstResponse.data.total,
        totalFiled: filedResponse.data.total,
      };

      setComplaintInfo(info);
      return info;
    } catch (error) {
      console.error('Failed to fetch complaint info:', error);
      return null;
    }
  };

  const showComplaintNotifications = (info: ComplaintInfo) => {
    interface NotificationItem {
      message: string;
      type: 'complaint' | 'compliment';
    }
    const notifications: NotificationItem[] = [];

    // Complaints against the user (negative - warning style)
    if (info.pendingComplaintsAgainstMe > 0) {
      const plural = info.pendingComplaintsAgainstMe === 1 ? 'complaint' : 'complaints';
      notifications.push({
        message: `You have ${info.pendingComplaintsAgainstMe} pending ${plural} against you`,
        type: 'complaint',
      });
    }

    // Compliments for the user (positive - success style)
    if (info.pendingComplimentsAgainstMe > 0) {
      const plural = info.pendingComplimentsAgainstMe === 1 ? 'compliment' : 'compliments';
      notifications.push({
        message: `You have ${info.pendingComplimentsAgainstMe} pending ${plural} for you! 🎉`,
        type: 'compliment',
      });
    }

    // Filed complaints awaiting resolution
    if (info.pendingComplaintsFiled > 0) {
      const plural = info.pendingComplaintsFiled === 1 ? 'complaint' : 'complaints';
      notifications.push({
        message: `You have ${info.pendingComplaintsFiled} filed ${plural} awaiting resolution`,
        type: 'complaint',
      });
    }

    // Filed compliments awaiting resolution
    if (info.pendingComplimentsFiled > 0) {
      const plural = info.pendingComplimentsFiled === 1 ? 'compliment' : 'compliments';
      notifications.push({
        message: `You have ${info.pendingComplimentsFiled} filed ${plural} awaiting resolution`,
        type: 'compliment',
      });
    }

    if (notifications.length > 0) {
      // Show each notification with a slight delay for better UX
      notifications.forEach((notification, index) => {
        setTimeout(() => {
          const isCompliment = notification.type === 'compliment';
          toast(notification.message, {
            icon: isCompliment ? '🌟' : '⚠️',
            duration: 6000,
            style: isCompliment
              ? {
                  background: '#D1FAE5',
                  color: '#065F46',
                  border: '1px solid #10B981',
                }
              : {
                  background: '#FEF3C7',
                  color: '#92400E',
                  border: '1px solid #F59E0B',
                },
          });
        }, index * 500);
      });
    }
  };

  const refreshProfile = async () => {
    try {
      const response = await apiClient.get<any>('/profiles/me');
      const profile = response.data;
      
      // Construct user object from profile response
      setUser({
        ID: profile.account_id,
        email: profile.email,
        type: profile.account_type,
        warnings: profile.warnings,
        balance: profile.balance ?? 0,
        wage: profile.wage ?? null,
        restaurantID: profile.restaurantID ?? null,
        customer_tier: profile.customer_tier ?? profile.customerTier ?? null,
      });
      
      // Update warning info based on warnings count
      const warningsCritical = profile.account_type === 'vip' ? profile.warnings >= 2 : profile.warnings >= 3;
      setWarningInfo({
        warnings_count: profile.warnings,
        warning_message: profile.warnings > 0 ? `You have ${profile.warnings} warning(s)` : null,
        is_near_threshold: warningsCritical,
      });
    } catch (error) {
      console.error('Failed to fetch profile:', error);
      // If profile fetch fails, clear auth
      setToken(null);
      setUser(null);
      localStorage.removeItem('token');
    } finally {
      setLoading(false);
    }
  };

  const login = async (credentials: LoginRequest) => {
    const response = await apiClient.post<LoginResponse>('/auth/login', credentials);
    const { access_token, warning_info } = response.data;
    
    setToken(access_token);
    localStorage.setItem('token', access_token);
    
    if (warning_info) {
      setWarningInfo(warning_info);
    }
    
    // Fetch user profile
    const profileResponse = await apiClient.get<ProfileResponse>('/auth/me', {
      headers: { Authorization: `Bearer ${access_token}` },
    });
    setUser(profileResponse.data.user);

    // Fetch and display complaint notifications after login
    try {
      const complaintInfoResult = await refreshComplaintInfo();
      if (complaintInfoResult) {
        // Show notifications with a slight delay so they appear after the "Welcome back" toast
        setTimeout(() => {
          showComplaintNotifications(complaintInfoResult);
        }, 1000);
      }
    } catch (error) {
      console.error('Failed to fetch complaint info on login:', error);
    }
  };

  const register = async (data: RegisterRequest) => {
    // Create registration (manager approval required). Do not auto-login.
    await apiClient.post('/auth/register', data);
    return;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setWarningInfo(null);
    setComplaintInfo(null);
    localStorage.removeItem('token');
  };

  const dismissWarning = () => {
    setWarningInfo(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        warningInfo,
        complaintInfo,
        loading,
        login,
        register,
        logout,
        refreshProfile,
        refreshComplaintInfo,
        dismissWarning,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
