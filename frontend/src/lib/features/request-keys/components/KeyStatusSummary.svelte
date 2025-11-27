<script lang="ts">
	import type { KeyStatusResponse } from '$lib/features/request-keys/types';
	import * as Card from '$lib/components/ui/card';

	let { keyStatusResponse }: { keyStatusResponse: KeyStatusResponse } = $props();
</script>

<div class="mb-6 grid grid-cols-2 gap-2 lg:grid-cols-4 lg:gap-4">
	<Card.Root class="bg-green-500/10 shadow-md dark:bg-green-900/20">
		<Card.Content class="flex flex-col items-center justify-center p-6">
			<div class="text-sm font-medium text-green-600 dark:text-green-400">活跃</div>
			<div class="text-2xl font-bold text-green-700 dark:text-green-300">
				{keyStatusResponse.available_keys_count}
			</div>
		</Card.Content>
	</Card.Root>
	<Card.Root class="bg-blue-500/10 shadow-md dark:bg-blue-900/20">
		<Card.Content class="flex flex-col items-center justify-center p-6">
			<div class="text-sm font-medium text-blue-600 dark:text-blue-400">使用中</div>
			<div class="text-2xl font-bold text-blue-700 dark:text-blue-300">
				{keyStatusResponse.in_use_keys_count}
			</div>
		</Card.Content>
	</Card.Root>
	<Card.Root class="bg-yellow-500/10 shadow-md dark:bg-yellow-900/20">
		<Card.Content class="flex flex-col items-center justify-center p-6">
			<div class="text-sm font-medium text-yellow-600 dark:text-yellow-400">冷却中</div>
			<div class="text-2xl font-bold text-yellow-700 dark:text-yellow-300">
				{keyStatusResponse.cooled_down_keys_count}
			</div>
		</Card.Content>
	</Card.Root>
	<Card.Root class="bg-muted shadow-md">
		<Card.Content class="flex flex-col items-center justify-center p-6">
			<div class="text-muted-foreground text-sm font-medium">总数</div>
			<div class="text-foreground text-2xl font-bold">
				{keyStatusResponse.total_keys_count}
			</div>
		</Card.Content>
	</Card.Root>
</div>
