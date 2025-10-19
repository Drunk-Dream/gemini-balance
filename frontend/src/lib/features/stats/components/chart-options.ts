
import type { EChartsOption } from 'echarts';

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
