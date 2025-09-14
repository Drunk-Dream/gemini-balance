import { api } from '$lib/utils/api';

interface RequestLog {
	id: string;
	request_time: string;
	response_time: string;
	request_duration_ms: number;
	key_identifier: string;
	auth_key_alias: string;
	model_name: string;
	prompt_tokens: number;
	completion_tokens: number;
	total_tokens: number;
	is_success: boolean;
	status_code: number;
	error_message: string | null;
	request_id: string;
}

interface GetRequestLogsParams {
	request_time_start?: string;
	request_time_end?: string;
	key_identifier?: string;
	auth_key_alias?: string;
	model_name?: string;
	is_success?: boolean;
	limit?: number;
	offset?: number;
}

export async function getRequestLogs(params: GetRequestLogsParams = {}): Promise<RequestLog[]> {
	const queryParams = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value !== undefined && value !== null) {
			queryParams.append(key, String(value));
		}
	}

	try {
		const response = await api.get<RequestLog[]>(`/request_logs?${queryParams.toString()}`);
		return response || [];
	} catch (error) {
		console.error('获取请求日志失败:', error);
		throw error;
	}
}
