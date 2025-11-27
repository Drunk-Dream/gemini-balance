<script lang="ts">
	import { theme } from '$lib/features/theme/theme';
	import Header from '$lib/layout/Header.svelte';
	import Sidebar from '$lib/layout/Sidebar.svelte';
	import '../app.css';
	import * as Sheet from '$lib/components/ui/sheet';

	let { children } = $props();

	let sidebarOpen = $state(false);

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	$effect(() => {
		// This ensures the theme is applied to the html element on initial load and changes
		document.documentElement.setAttribute('data-theme', $theme);
	});
</script>

<div class="bg-background flex h-screen w-full">
	<!-- Desktop Sidebar -->
	<div class="hidden h-full lg:block">
		<Sidebar sidebarOpen={false} toggleSidebar={() => {}} />
	</div>

	<!-- Mobile Sidebar (Sheet) -->
	<Sheet.Root bind:open={sidebarOpen}>
		<Sheet.Content side="left" class="w-72 border-r-0 p-0">
			<Sidebar {sidebarOpen} {toggleSidebar} />
		</Sheet.Content>
	</Sheet.Root>

	<div class="flex flex-1 flex-col overflow-hidden">
		<Header {toggleSidebar} />
		<!-- Main content -->
		<main class="flex-1 overflow-y-auto p-4">
			{@render children?.()}
		</main>
	</div>
</div>

<svelte:head>
	<!-- Font Awesome for icons -->
	<link
		rel="stylesheet"
		href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css"
		integrity="sha512-SnH5WK+bZxgPHs44uWIX+LLJAJ9/2PkPKZ5QiAj6Ta86w+fsb2TkcmfRyVX3pBnMFcV7oQPJkl9QevSCWr3W6A=="
		crossorigin="anonymous"
		referrerpolicy="no-referrer"
	/>
</svelte:head>
