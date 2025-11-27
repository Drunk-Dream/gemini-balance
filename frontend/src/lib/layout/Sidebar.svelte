<script lang="ts">
	import { authService } from '$lib/features/auth/service';
	import { isAuthenticated } from '$lib/features/auth/store';
	import { toggleTheme } from '$lib/features/theme/theme';
	import { navLinks } from '$lib/layout/navLinks';
	import NavLink from './NavLink.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Separator } from '$lib/components/ui/separator';
	import SignOut from 'phosphor-svelte/lib/SignOut';
	import Sun from 'phosphor-svelte/lib/Sun';
	import Moon from 'phosphor-svelte/lib/Moon';

	let { sidebarOpen, toggleSidebar } = $props();

	function handleLogout() {
		authService.logout();
		// Close sidebar after logout if it's open
		if (sidebarOpen) {
			toggleSidebar();
		}
	}
</script>

<div
	class="bg-sidebar text-sidebar-foreground border-sidebar-border flex min-h-full w-72 flex-col border-r p-4 shadow-lg"
>
	<div class="mb-4 px-4 text-2xl font-bold"><a href="/">Gemini Balance</a></div>
	<nav class="flex flex-col gap-2">
		{#if $isAuthenticated}
			{#each navLinks as link}
				<NavLink href={link.href} name={link.name} onClick={toggleSidebar} icon={link.icon} />
			{/each}
		{:else}
			<NavLink href="/login" name="登录" onClick={toggleSidebar} icon="fa-solid fa-sign-in-alt" />
		{/if}
	</nav>

	<Separator class="my-4" />

	<div class="mt-auto flex flex-col gap-2">
		{#if $isAuthenticated}
			<Button variant="ghost" size="lg" onclick={handleLogout} class="w-full justify-start">
				<SignOut class="mr-2 size-5" />
				登出
			</Button>
		{/if}

		<Button variant="ghost" size="lg" class="w-full justify-start" onclick={toggleTheme}>
			<Sun class="mr-2 size-5 dark:hidden" />
			<Moon class="mr-2 hidden size-5 dark:block" />
			<span class="dark:hidden">日间</span>
			<span class="hidden dark:block">夜间</span>
		</Button>
	</div>
</div>
