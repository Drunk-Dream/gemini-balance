import type { EChartsOption } from 'echarts';
export interface ChartOption {
	value: string;
	label: string;
}

export const ALL_CHARTS: ChartOption[] = [
	{ value: 'dailyUsage', label: '每日使用' },
	{ value: 'usageRequestTrend', label: '请求次数' },
	{ value: 'usageTokensTrend', label: 'Token用量' },
	{ value: 'successRate', label: '请求成功率' },
	{ value: 'hourlySuccessRate', label: '请求成功率(按小时)' }
];

export const defaultChartOptions: EChartsOption = {
	tooltip: {
		trigger: 'axis',
		axisPointer: {
			type: 'shadow'
		}
	},
	legend: {
		type: 'scroll',
		backgroundColor: 'rgba(255, 255, 255, 0.5)',
		borderRadius: 12,
		padding: 10,
		bottom: 0
	},
	grid: {
		left: '3%',
		right: '4%',
		top: '5%',
		bottom: '15%',
		containLabel: true
	}
};
