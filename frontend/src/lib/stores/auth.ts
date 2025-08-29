import { browser } from '$app/environment';
import { writable } from 'svelte/store';

// 从 localStorage 初始化认证令牌
const initialAuthToken = browser ? localStorage.getItem('authToken') : null;
export const authToken = writable<string | null>(initialAuthToken);

// 根据令牌是否存在来判断认证状态
export const isAuthenticated = writable<boolean>(!!initialAuthToken);

// 订阅 authToken 的变化，并更新 localStorage 和 isAuthenticated
authToken.subscribe((token) => {
    if (browser) {
        if (token) {
            localStorage.setItem('authToken', token);
            isAuthenticated.set(true);
        } else {
            localStorage.removeItem('authToken');
            isAuthenticated.set(false);
        }
    }
});
