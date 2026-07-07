export interface APIResponse<T> {
  success: boolean;
  message: string;
  data: T;
  meta: Record<string, any>;
  errors: string[];
}

export interface TenantTheme {
  primary_color: string;
  secondary_color: string;
  logo_url?: string;
  favicon_url?: string;
  custom_css?: string;
}

export interface TenantConfig {
  theme: TenantTheme;
  custom_domain?: string;
  active_modules: string[];
  feature_flags: Record<string, boolean>;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  config: TenantConfig;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Permission {
  name: string;
  description: string;
  module: string;
}

export interface Role {
  id: string;
  name: string;
  description?: string;
  permissions: string[];
  is_system: boolean;
  tenant_id?: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  tenant_id: string;
  role_id: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
  tenant?: Tenant;
  role?: Role;
}

export interface AuthToken {
  expires_in: number;
  token_type: string;
}
