export interface ChartDataset {
	label: string;
	data: (number | null)[];
}

export interface ChartData {
	labels: string[];
	datasets: ChartDataset[];
}

export enum UsageStatsUnit {
	DAY = 'day',
	WEEK = 'week',
	MONTH = 'month'
}

export type DailyUsageHeatmapData = [string, number][];

export interface ModelSuccessRateStats {
	date: string; // ISO date string
	models: Record<string, number>;
}

export interface SuccessRateStatsResponse {
	stats: ModelSuccessRateStats[];
	models: string[];
}
