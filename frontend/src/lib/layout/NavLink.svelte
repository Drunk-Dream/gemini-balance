<script lang="ts">
	import { page } from '$app/state';

	let {
		href,
		name,
		onClick,
		icon
	}: {
		href: string;
		name: string;
		onClick: () => void;
		icon: string; // Add icon prop
	} = $props();

	const isActive = $derived(page.url.pathname === href);
</script>

<li>
	<a
		{href}
		class="flex items-center gap-2 text-lg font-semibold {isActive
			? 'bg-base-300 border-base-content/20 border'
			: ''}"
		onclick={onClick}
	>
		<i class="{icon} w-6 text-lg"></i>
		{name}
	</a>
</li>
