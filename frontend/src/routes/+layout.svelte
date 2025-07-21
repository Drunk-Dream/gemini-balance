<script lang="ts">
	import { page } from '$app/stores';
	import { quintOut } from 'svelte/easing';
	import { slide } from 'svelte/transition';
	import '../app.css';

	let { children } = $props();

	const navLinks = [
		{ name: '密钥状态', href: '/' },
		{ name: '日志查看', href: '/logs' }
	];

	let sidebarOpen = $state(false);

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}
</script>

<div class="flex h-screen bg-gray-100">
	<!-- Mobile Header and Hamburger Menu -->
	<header
		class="fixed left-0 right-0 top-0 z-20 flex items-center justify-between bg-gray-800 p-4 text-white md:hidden"
	>
		<div class="text-xl font-bold">Gemini Balance</div>
		<button
			onclick={toggleSidebar}
			class="text-white focus:outline-none"
			aria-label="Toggle sidebar"
		>
			<svg
				class="h-6 w-6"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M4 6h16M4 12h16M4 18h16"
				></path>
			</svg>
		</button>
	</header>

	<!-- Sidebar -->
	{#if sidebarOpen}
		<div
			transition:slide={{ axis: 'x', duration: 300, easing: quintOut }}
			class="fixed inset-y-0 left-0 z-30 flex w-64 flex-col bg-gray-800 text-white md:hidden"
		>
			<div class="border-b border-gray-700 p-4 text-2xl font-bold">Gemini Balance</div>
			<nav class="flex-1 p-4">
				<ul>
					{#each navLinks as link}
						<li class="mb-2">
							<a
								href={link.href}
								class="block rounded-md p-2 transition-colors duration-200 hover:bg-gray-700 {$page
									.url.pathname === link.href
									? 'bg-gray-700'
									: ''}"
								onclick={toggleSidebar}
							>
								{link.name}
							</a>
						</li>
					{/each}
				</ul>
			</nav>
		</div>
	{/if}

	<!-- Overlay for mobile sidebar -->
	{#if sidebarOpen}
		<div
			class="fixed inset-0 z-20 bg-black opacity-50 md:hidden"
			onclick={toggleSidebar}
			role="button"
			tabindex="0"
			aria-label="Close sidebar"
		></div>
	{/if}

	<!-- Desktop Sidebar -->
	<aside class="hidden w-64 flex-shrink-0 flex-col bg-gray-800 text-white md:flex">
		<div class="border-b border-gray-700 p-4 text-2xl font-bold">Gemini Balance</div>
		<nav class="flex-1 p-4">
			<ul>
				{#each navLinks as link}
					<li class="mb-2">
						<a
							href={link.href}
							class="block rounded-md p-2 transition-colors duration-200 hover:bg-gray-700 {$page
								.url.pathname === link.href
								? 'bg-gray-700'
								: ''}"
						>
							{link.name}
						</a>
					</li>
				{/each}
			</ul>
		</nav>
	</aside>

	<!-- Main content -->
	<main class="mt-16 flex-1 overflow-y-auto p-4 md:mt-0 md:p-6">
		{@render children()}
	</main>
</div>
