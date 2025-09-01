import { authToken } from '$lib/stores';
import { get } from 'svelte/store';

const API_BASE_URL = '/api';

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

		if (response.status === 401 || response.status === 403) {
			authToken.set(null);
			throw new Error('Unauthorized');
		}

		if (!response.ok) {
			const errorData = await response.json();
			throw new Error(errorData.detail || 'Something went wrong');
		}

		// 新增：如果响应是 "No Content"，我们不能调用 .json()，直接返回 null
		if (response.status === 204) {
			return null;
		}

		// 检查响应是否为空，如果为空则返回 null 或 undefined
		const data = await response.json();
		if (!data) {
			throw new Error('Empty response');
		}
		return data as T;
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
