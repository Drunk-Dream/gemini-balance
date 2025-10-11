<script lang="ts">
	let { toggleSidebar } = $props();
</script>

<div class="navbar bg-base-100 sticky top-0 z-10 min-h-8 lg:hidden">
	<div class="navbar-start">
		<button type="button" class="btn btn-ghost" onclick={toggleSidebar} aria-label="Toggle sidebar">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-5 w-5"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
				><path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M4 6h16M4 12h8m-8 6h16"
				></path></svg
			>
		</button>
	</div>
</div>
