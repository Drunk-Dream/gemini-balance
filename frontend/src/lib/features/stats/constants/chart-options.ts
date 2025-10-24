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

export function getDefaultChartOptions(): EChartsOption {
    const isBrowser = typeof window !== 'undefined';
    const getCssVar = (varName: string, fallback: string) =>
        isBrowser ? getComputedStyle(document.documentElement).getPropertyValue(varName) || fallback : fallback;

    const foregroundColor = getCssVar('--foreground', '#333');
    const mutedForegroundColor = getCssVar('--muted-foreground', '#333');
    const borderColor = getCssVar('--border-color', '#ccc');
    const mutedColor = getCssVar('--muted', '#f0f0f0');

	return {
		tooltip: {
			trigger: 'axis',
			axisPointer: {
				type: 'shadow'
			},
			backgroundColor: mutedColor,
			textStyle: {
				color: mutedForegroundColor
			},
			borderColor: borderColor
		},
		legend: {
			type: 'scroll',
			textStyle: {
				color: foregroundColor
			},
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
}
