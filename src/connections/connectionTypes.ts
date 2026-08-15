export interface Permission {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  connection?: string;
  configured?: boolean;
  profile?: {
    email?: string;
    name?: string;
    picture?: string;
  };
}

export interface PermissionSection {
  id: string;
  title: string;
  permissions: Permission[];
}
