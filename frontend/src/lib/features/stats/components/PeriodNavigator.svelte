<script lang="ts">
	import CaretLeft from 'phosphor-svelte/lib/CaretLeft';
	import CaretRight from 'phosphor-svelte/lib/CaretRight';
	import { Button } from '$lib/components/ui/button';

	let {
		offset = $bindable(),
		periodText,
		disabled = [false, false]
	}: {
		offset: number;
		periodText: string;
		disabled?: [boolean, boolean];
	} = $props();
</script>

<div class="flex items-center space-x-2">
	<Button
		variant="ghost"
		onclick={() => (offset -= 1)}
		aria-label="上一时间段"
		disabled={disabled[0]}
	>
		<CaretLeft class="size-4" />
	</Button>
	<span class="text-muted-foreground text-sm">{periodText}</span>
	<Button
		variant="ghost"
		onclick={() => (offset += 1)}
		aria-label="下一时间段"
		disabled={disabled[1]}
	>
		<CaretRight class="size-4" />
	</Button>
</div>
