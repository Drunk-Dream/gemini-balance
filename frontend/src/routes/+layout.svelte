<script lang="ts">
	import { theme } from '$lib/features/theme/theme';
	import Header from '$lib/layout/Header.svelte';
	import Sidebar from '$lib/layout/Sidebar.svelte';
	import '../app.css';

	let { children } = $props();

	let sidebarOpen = $state(false); // sidebarOpen will be controlled by the drawer-toggle checkbox

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	$effect(() => {
		// This ensures the theme is applied to the html element on initial load and changes
		document.documentElement.setAttribute('data-theme', $theme);
	});
</script>

<div class="drawer lg:drawer-open">
	<input id="my-drawer-2" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />
	<div class="drawer-content flex flex-col">
		<Header {toggleSidebar} />
		<!-- Main content -->
		<main class="flex-1 overflow-y-auto p-4 lg:p-6">
			{@render children?.()}
		</main>
	</div>
	<div class="drawer-side border-r border-base-300 shadow-base-200">
		<label for="my-drawer-2" aria-label="close sidebar" class="drawer-overlay"></label>
		<Sidebar {sidebarOpen} {toggleSidebar} />
	</div>
</div>

<svelte:head>
	<!-- Font Awesome for icons -->
	<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css" integrity="sha512-SnH5WK+bZxgPHs44uWIX+LLJAJ9/2PkPKZ5QiAj6Ta86w+fsb2TkcmfRyVX3pBnMFcV7oQPJkl9QevSCWr3W6A==" crossorigin="anonymous" referrerpolicy="no-referrer" />
</svelte:head>
