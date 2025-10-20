export interface ChartDataset {
	label: string;
	data: (number | null)[];
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

export interface ModelSuccessRateStats {
	date: string; // ISO date string
	models: Record<string, number>;
}

export interface SuccessRateStatsResponse {
	stats: ModelSuccessRateStats[];
	models: string[];
}
export interface HourlySuccessRateChartData {
	labels: string[]; // e.g., ["00", "01", ..., "23"]
	datasets: ChartDataset[];
}
