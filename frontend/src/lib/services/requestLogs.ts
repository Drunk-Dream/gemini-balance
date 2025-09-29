import { api } from '$lib/utils/api';
import { TZDate } from '@date-fns/tz';
import { format } from 'date-fns';

export interface RequestLog {
	id: number;
	request_id: string;
	request_time: string;
	key_identifier: string;
	auth_key_alias: string;
	model_name: string;
	is_success: boolean;
	prompt_tokens?: number;
	completion_tokens?: number;
	total_tokens?: number;
	error_type?: string;
	key_brief?: string;
}

interface RequestLogsResponse {
	logs: RequestLog[];
	total: number;
	key_identifiers?: string[];
	auth_key_aliases?: string[];
	model_names?: string[];
	request_time_range: [string, string] | null;
}

export interface GetRequestLogsParams {
	request_time_start: string;
	request_time_end: string;
	key_identifier?: string;
	auth_key_alias?: string;
	model_name?: string;
	is_success?: boolean;
	limit?: number;
	offset?: number;
}

export async function getRequestLogs(params: GetRequestLogsParams): Promise<RequestLogsResponse> {
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
	return format(new TZDate(date), "yyyy-MM-dd'T'HH:mm");
}
