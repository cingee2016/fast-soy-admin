declare namespace Api {
  /**
   * namespace Auth
   *
   * backend api module: "auth"
   */
  namespace Auth {
    interface LoginToken {
      token: string;
      refreshToken: string;
      /** Only present on /auth/login response; true when user must change password before continuing */
      mustChangePassword?: boolean;
    }

    interface UserInfo {
      userId: string;
      userName: string;
      nickName: string;
      userGender: Api.SystemManage.UserGender | null;
      userEmail: string | null;
      userPhone: string | null;
      roles: string[];
      buttons: string[];
      /** Whether the current session is an impersonation */
      impersonating?: boolean;
      /** The original admin user id who initiated impersonation */
      impersonatorId?: string;
    }

    /** update password params */
    interface UpdatePasswordParams {
      oldPassword: string;
      newPassword: string;
    }

    /** update current user's profile params */
    interface UpdateProfileParams {
      nickName: string | null;
      userGender: Api.SystemManage.UserGender | null;
      userEmail: string | null;
      userPhone: string | null;
    }
  }
}
