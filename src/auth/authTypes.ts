export interface SherpaAccount {
  id: string;
  email: string;
  name: string;
}

export interface AuthenticatedSherpaAccount extends SherpaAccount {
  token: string;
}
