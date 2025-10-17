import { api } from '$lib/api';
import type {
	DailyUsageChartData,
	DailyUsageHeatmapData,
	SuccessRateStatsResponse,
	UsageStatsData
} from '$lib/features/stats/types';
import { UsageStatsUnit } from '$lib/features/stats/types';

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

export async function getDailyUsageHeatmap(
	type: 'requests' | 'tokens',
	timezone_str?: string
): Promise<DailyUsageHeatmapData> {
	const queryParams = new URLSearchParams();
	if (timezone_str) {
		queryParams.append('timezone_str', timezone_str);
	}
	queryParams.append('type', type);

	try {
		const response = await api.get<DailyUsageHeatmapData>(
			`/request_logs/daily_usage_heatmap?${queryParams.toString()}`
		);
		if (!response) {
			throw new Error('获取每日使用热力图数据失败：API 返回空数据');
		}
		return response;
	} catch (error) {
		console.error('获取每日使用热力图数据失败:', error);
		throw error;
	}
}

export async function getUsageStats(
	unit: UsageStatsUnit,
	offset: number,
	numPeriods: number,
	timezone_str: string,
	type: 'requests' | 'tokens'
): Promise<UsageStatsData> {
	const queryParams = new URLSearchParams();
	queryParams.append('unit', unit);
	queryParams.append('offset', offset.toString());
	queryParams.append('num_periods', numPeriods.toString());
	queryParams.append('timezone_str', timezone_str);
	queryParams.append('type', type);

	try {
		const response = await api.get<UsageStatsData>(
			`/request_logs/usage_stats?${queryParams.toString()}`
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

export async function getSuccessRateStats(
	days: number,
	timezone_str: string
): Promise<SuccessRateStatsResponse> {
	const queryParams = new URLSearchParams();
	queryParams.append('days', days.toString());
	queryParams.append('timezone_str', timezone_str);

	try {
		const response = await api.get<SuccessRateStatsResponse>(
			`/stats/success-rate?${queryParams.toString()}`
		);
		if (!response) {
			throw new Error('获取成功率统计数据失败：API 返回空数据');
		}
		return response;
	} catch (error) {
		console.error('获取成功率统计数据失败:', error);
		throw error;
	}
}
