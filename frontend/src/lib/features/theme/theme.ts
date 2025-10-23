import { browser } from '$app/environment';
import { writable } from 'svelte/store';

type Theme = 'light' | 'dark';

const getSystemTheme = (): Theme => {
	if (browser && window.matchMedia('(prefers-color-scheme: dark)').matches) {
		return 'dark';
	}
	return 'light';
};

const initialTheme: Theme = browser
	? (localStorage.getItem('theme') as Theme) || getSystemTheme()
	: 'light';

export const theme = writable<Theme>(initialTheme);

theme.subscribe((value) => {
	if (browser) {
		localStorage.setItem('theme', value);
		document.documentElement.setAttribute('data-theme', value);
		if (value === 'dark') {
			document.documentElement.classList.add('dark');
		} else {
			document.documentElement.classList.remove('dark');
		}
	}
});
export const toggleTheme = () => {
	theme.update((currentTheme) => (currentTheme === 'light' ? 'dark' : 'light'));
};

// Listen for system theme changes
if (browser) {
	window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (event) => {
		theme.set(event.matches ? 'dark' : 'light');
	});
}
