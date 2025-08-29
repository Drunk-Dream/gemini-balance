import { authToken } from '$lib/stores';
import { get } from 'svelte/store';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function request<T>(
    method: string,
    path: string,
    data?: object | null,
    headers?: HeadersInit
): Promise<T | null> {
    const url = `${API_BASE_URL}${path}`;
    const token = get(authToken);

    const defaultHeaders: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(headers as Record<string, string>)
    };

    if (token) {
        defaultHeaders['Authorization'] = `Bearer ${token}`;
    }

    const config: RequestInit = {
        method,
        headers: defaultHeaders
    };

    if (data) {
        config.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, config);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Something went wrong');
        }

        // 检查响应是否为空，如果为空则返回 null 或 undefined
        const text = await response.text();
        return text ? JSON.parse(text) : null;
    } catch (error) {
        console.error('API request error:', error);
        throw error;
    }
}

export const api = {
    get: <T>(path: string, headers?: HeadersInit) => request<T>('GET', path, null, headers),
    post: <T>(path: string, data: object, headers?: HeadersInit) =>
        request<T>('POST', path, data, headers),
    put: <T>(path: string, data: object, headers?: HeadersInit) =>
        request<T>('PUT', path, data, headers),
    delete: <T>(path: string, headers?: HeadersInit) => request<T>('DELETE', path, null, headers)
};
