import { goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { authToken, isAuthenticated } from '$lib/features/auth/store';

export const authService = {
	logout: () => {
		authToken.set(null); // 清除令牌
		isAuthenticated.set(false); // 设置认证状态为未认证
		goto(resolve('/login')); // 重定向到登录页面
	}
	// 可以在这里添加其他认证相关的方法，例如 login
};
