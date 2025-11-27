<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import List from 'phosphor-svelte/lib/List';

	let { toggleSidebar } = $props();
</script>

<div class="bg-background sticky top-0 z-10 flex min-h-12 items-center px-4 shadow-sm lg:hidden">
	<div class="flex-1"></div>
	<div>
		<Button variant="ghost" size="icon" onclick={toggleSidebar} aria-label="Toggle sidebar">
			<List class="size-6" />
		</Button>
	</div>
</div>
