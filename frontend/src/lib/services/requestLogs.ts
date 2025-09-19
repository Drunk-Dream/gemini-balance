import { api } from '$lib/utils/api';

interface RequestLog {
	id: number;
	request_id: string;
	request_time: string;
	key_identifier: string;
	auth_key_alias?: string;
	model_name?: string;
	is_success: boolean;
}

interface RequestLogsResponse {
	logs: RequestLog[];
	total: number;
}

export interface GetRequestLogsParams {
	request_time_start?: string;
	request_time_end?: string;
	key_identifier?: string;
	auth_key_alias?: string;
	model_name?: string;
	is_success?: boolean;
	limit?: number;
	offset?: number;
}

export async function getRequestLogs(
	params: GetRequestLogsParams = {}
): Promise<RequestLogsResponse> {
	const queryParams = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value !== undefined && value !== null) {
			queryParams.append(key, String(value));
		}
	}

	try {
		const response = await api.get<RequestLogsResponse>(`/request_logs?${queryParams.toString()}`);
		if (!response) {
			throw new Error('获取请求日志失败：API 返回空数据');
		}
		return response;
	} catch (error) {
		console.error('获取请求日志失败:', error);
		throw error;
	}
}

// 辅助函数：将 Date 对象格式化为 YYYY-MM-DDTHH:mm 格式的本地时间字符串
export function formatToLocalDateTimeString(date: Date): string {
	const year = date.getFullYear();
	const month = (date.getMonth() + 1).toString().padStart(2, '0');
	const day = date.getDate().toString().padStart(2, '0');
	const hours = date.getHours().toString().padStart(2, '0');
	const minutes = date.getMinutes().toString().padStart(2, '0');
	return `${year}-${month}-${day}T${hours}:${minutes}`;
}
