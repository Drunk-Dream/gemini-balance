<script lang="ts">
	import CaretLeft from 'phosphor-svelte/lib/CaretLeft';
	import CaretRight from 'phosphor-svelte/lib/CaretRight';

	let {
		offset = $bindable(),
		periodText,
		disabled = false
	} = $props<{
		offset: number;
		periodText: string;
		disabled?: boolean;
	}>();
</script>

<div class="flex items-center space-x-2">
	<button
		class="btn btn-ghost btn-sm"
		onclick={() => (offset -= 1)}
		aria-label="上一时间段"
		{disabled}
	>
		<CaretLeft class="size-4" />
	</button>
	<span class="text-base-content/60 text-sm">{periodText}</span>
	<button
		class="btn btn-ghost btn-sm"
		onclick={() => (offset += 1)}
		aria-label="下一时间段"
		{disabled}
	>
		<CaretRight class="size-4" />
	</button>
</div>
