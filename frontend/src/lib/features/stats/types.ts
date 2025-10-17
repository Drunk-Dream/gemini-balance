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

export type DailyUsageHeatmapData = [string, number][];

export interface DailyModelSuccessRate {
	successful_requests: number;
	total_requests: number;
}

export interface ModelSuccessRateStats {
	date: string; // ISO date string
	models: Record<string, DailyModelSuccessRate>;
}

export interface SuccessRateStatsResponse {
	stats: ModelSuccessRateStats[];
	models: string[];
}
