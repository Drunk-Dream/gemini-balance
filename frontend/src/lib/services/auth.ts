import { goto } from '$app/navigation';
import { authToken, isAuthenticated } from '$lib/stores';

export const authService = {
    logout: () => {
        authToken.set(null); // 清除令牌
        isAuthenticated.set(false); // 设置认证状态为未认证
        goto('/login'); // 重定向到登录页面
    }
    // 可以在这里添加其他认证相关的方法，例如 login
};
