<script lang="ts">
	import { authService } from '$lib/features/auth/service';
	import { isAuthenticated } from '$lib/features/auth/store';
	import { toggleTheme } from '$lib/features/theme/theme';
	import { navLinks } from '$lib/layout/navLinks';
	import NavLink from './NavLink.svelte';

	let { sidebarOpen, toggleSidebar } = $props();

	function handleLogout() {
		authService.logout();
		// Close sidebar after logout if it's open
		if (sidebarOpen) {
			toggleSidebar();
		}
	}
</script>

<ul class="menu bg-base-200 text-base-content flex min-h-full w-72 flex-col p-4">
	<li class="menu-title mb-4 text-2xl font-bold"><a href="/">Gemini Balance</a></li>
	{#each navLinks as link}
		<NavLink href={link.href} name={link.name} onClick={toggleSidebar} icon={link.icon} />
	{/each}

	<div class="divider my-4"></div>

	<li class="mt-auto">
		{#if $isAuthenticated}
			<button onclick={handleLogout} class="btn btn-ghost w-full justify-start">
				<i class="fa-solid fa-right-from-bracket text-lg w-6"></i>
				登出
			</button>
		{/if}
	</li>
	<li>
		<label class="swap swap-rotate btn btn-ghost w-full justify-start">
			<input type="checkbox" onchange={toggleTheme} />
			<div class="swap-off">
				<i class="fa-solid fa-sun text-lg w-6"></i>
				<span>主题</span>
			</div>
			<div class="swap-on">
				<i class="fa-solid fa-moon text-lg w-6"></i>
				<span>主题</span>
			</div>
		</label>
	</li>
</ul>
