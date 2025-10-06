<script lang="ts">
	import { authService } from '$lib/features/auth/service';
	import { isAuthenticated } from '$lib/features/auth/store';
	import { navLinks } from "$lib/layout/navLinks";
	import { quintOut } from 'svelte/easing';
	import { slide } from 'svelte/transition';
	import NavLink from './NavLink.svelte';

	let { sidebarOpen, toggleSidebar, isMobile } = $props();

	function handleLogout() {
		authService.logout();
		if (isMobile) {
			toggleSidebar();
		}
	}
</script>

{#if sidebarOpen || !isMobile}
	<aside
		class="flex-shrink-0 flex-col bg-gray-800 text-white {isMobile
			? 'fixed inset-y-0 left-0 z-30 flex w-64'
			: 'hidden w-64 md:flex'}"
		transition:slide={{ axis: 'x', duration: 300, easing: quintOut }}
	>
		<div class="border-b border-gray-700 p-4 text-2xl font-bold">Gemini Balance</div>
		<nav class="flex-1 p-4">
			<ul>
				{#each navLinks as link}
					<NavLink
						href={link.href}
						name={link.name}
						onClick={isMobile ? toggleSidebar : undefined}
					/>
				{/each}
				{#if $isAuthenticated}
					<li class="mb-2">
						<button
							onclick={handleLogout}
							class="block w-full cursor-pointer rounded-md p-2 text-left transition-colors duration-200 hover:bg-gray-700"
						>
							登出
						</button>
					</li>
				{/if}
			</ul>
		</nav>
	</aside>
{/if}

{#if sidebarOpen && isMobile}
	<button
		type="button"
		class="fixed inset-0 z-20 bg-black opacity-50 md:hidden"
		onclick={toggleSidebar}
		aria-label="Close sidebar"
	></button>
{/if}
