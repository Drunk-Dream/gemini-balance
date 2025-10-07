import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		proxy: {
			'/api': {
				target: 'http://localhost:8090',
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api/, '/api')
			}
		}
	},
	build: {
		chunkSizeWarningLimit: 600
	}
});
