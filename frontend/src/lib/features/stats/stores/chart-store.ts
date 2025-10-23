import { writable } from 'svelte/store';
import { ALL_CHARTS } from '../constants/chart-options';

function createChartSelectionStore() {
	const initialValue =
		typeof localStorage !== 'undefined'
			? JSON.parse(localStorage.getItem('chartSelection') || 'null')
			: null;

	const finalInitialValue =
		initialValue && Array.isArray(initialValue)
			? initialValue
			: ALL_CHARTS.map((chart) => chart.value);

	const { subscribe, set } = writable<string[]>(finalInitialValue);

	return {
		subscribe,
		set: (value: string[]) => {
			if (typeof localStorage !== 'undefined') {
				localStorage.setItem('chartSelection', JSON.stringify(value));
			}
			set(value);
		}
	};
}

export const chartSelectionStore = createChartSelectionStore();
