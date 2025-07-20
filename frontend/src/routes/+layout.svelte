<script lang="ts">
	import '../app.css';
	import { page } from '$app/stores';

	let { children } = $props();

	const navLinks = [
		{ name: '密钥状态', href: '/' },
		{ name: '日志查看', href: '/logs' }
	];
</script>

<div class="flex h-screen bg-gray-100">
	<!-- Sidebar -->
	<aside class="w-64 bg-gray-800 text-white flex flex-col">
		<div class="p-4 text-2xl font-bold border-b border-gray-700">
			Gemini Balance
		</div>
		<nav class="flex-1 p-4">
			<ul>
				{#each navLinks as link}
					<li class="mb-2">
						<a
							href={link.href}
							class="block p-2 rounded-md hover:bg-gray-700 transition-colors duration-200 {
								$page.url.pathname === link.href ? 'bg-gray-700' : ''
							}"
						>
							{link.name}
						</a>
					</li>
				{/each}
			</ul>
		</nav>
	</aside>

	<!-- Main content -->
	<main class="flex-1 overflow-y-auto p-6">
		{@render children()}
	</main>
</div>
