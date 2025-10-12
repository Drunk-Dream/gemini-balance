import { api } from '$lib/api';

export interface ChartDataset {
	label: string;
	data: number[];
}

export interface DailyUsageChartData {
	labels: string[];
	datasets: ChartDataset[];
}

export enum UsageStatsUnit {
	DAY = 'day',
	WEEK = 'week',
	MONTH = 'month'
}

export interface UsageStatsData {
	labels: string[];
	datasets: ChartDataset[];
	start_date: string;
	end_date: string;
}

export async function getDailyUsageChart(timezone_str?: string): Promise<DailyUsageChartData> {
	const queryParams = new URLSearchParams();
	if (timezone_str) {
		queryParams.append('timezone_str', timezone_str);
	}

	try {
		const response = await api.get<DailyUsageChartData>(
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

export async function getUsageStats(
	unit: UsageStatsUnit,
	offset: number,
	numPeriods: number,
	timezone_str: string,
	data_type: 'request_count' | 'token_count'
): Promise<UsageStatsData> {
	const queryParams = new URLSearchParams();
	queryParams.append('unit', unit);
	queryParams.append('offset', offset.toString());
	queryParams.append('num_periods', numPeriods.toString());
	queryParams.append('timezone_str', timezone_str);

	const path_mapping: { [key in 'request_count' | 'token_count']: string } = {
		request_count: '/request_logs/usage_stats',
		token_count: '/request_logs/token_usage_stats'
	};
	try {
		const response = await api.get<UsageStatsData>(
			`${path_mapping[data_type]}?${queryParams.toString()}`
		);
		if (!response) {
			throw new Error('获取模型使用统计趋势图表数据失败：API 返回空数据');
		}
		return response;
	} catch (error) {
		console.error('获取模型使用统计趋势图表数据失败:', error);
		throw error;
	}
}
