import { api } from '$lib/api';

export interface ChartDataset {
	label: string;
	data: number[];
}

export interface ChartData {
	labels: string[];
	datasets: ChartDataset[];
}

export async function getDailyUsageChart(timezone_str?: string): Promise<ChartData> {
	const queryParams = new URLSearchParams();
	if (timezone_str) {
		queryParams.append('timezone_str', timezone_str);
	}

	try {
		const response = await api.get<ChartData>(
			`/request_logs/daily_usage_chart?${queryParams.toString()}`
		);
		if (!response) {
			throw new Error('获取每日模型使用统计图表数据失败：API 返回空数据');
		}
		return response;
	} catch (error) {
		console.error('获取每日模型使用统计图表数据失败:', error);
		throw error;
	}
}
