import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import apiClient from '../lib/api-client';
import { User, LoginRequest, RegisterRequest, LoginResponse, ProfileResponse } from '../types/api';

interface WarningInfo {
  warnings_count: number;
  warning_message: string | null;
  is_near_threshold: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  warningInfo: WarningInfo | null;
  loading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
  dismissWarning: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [warningInfo, setWarningInfo] = useState<WarningInfo | null>(null);
  const [loading, setLoading] = useState(true);

  // Load user profile on mount if token exists
  useEffect(() => {
    if (token) {
      refreshProfile();
    } else {
      setLoading(false);
    }
  }, [token]);

  const refreshProfile = async () => {
    try {
      const response = await apiClient.get<ProfileResponse>('/account/profile');
      setUser(response.data.user);
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
    const profileResponse = await apiClient.get<ProfileResponse>('/account/profile', {
      headers: { Authorization: `Bearer ${access_token}` },
    });
    setUser(profileResponse.data.user);
  };

  const register = async (data: RegisterRequest) => {
    await apiClient.post('/auth/register', data);
    // After registration, automatically log in
    await login({ email: data.email, password: data.password });
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setWarningInfo(null);
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
        loading,
        login,
        register,
        logout,
        refreshProfile,
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
