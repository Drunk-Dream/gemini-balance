<script lang="ts">
	import { Pagination } from 'bits-ui';
	import CaretLeft from 'phosphor-svelte/lib/CaretLeft';
	import CaretRight from 'phosphor-svelte/lib/CaretRight';

	let {
		currentPage = $bindable(),
		perPage,
		totalItems
	}: {
		currentPage: number;
		perPage: number;
		totalItems: number;
	} = $props();
</script>

<Pagination.Root count={totalItems} {perPage} siblingCount={2} bind:page={currentPage}>
	{#snippet children({ pages, range })}
		<div class="mt-4 flex flex-col items-center justify-between space-y-4 md:flex-row md:space-y-0">
			<Pagination.PrevButton
				class="flex cursor-pointer items-center rounded bg-gray-600 px-4 py-2 text-white hover:bg-gray-700 disabled:opacity-50"
			>
				<CaretLeft class="size-6" />
			</Pagination.PrevButton>

			<div class="flex flex-wrap items-center justify-center space-x-1">
				{#each pages as page (page.key)}
					{#if page.type === 'ellipsis'}
						<span class="px-2 py-1">...</span>
					{:else}
						<Pagination.Page
							{page}
							class="data-selected:bg-gray-800 data-selected:text-white cursor-pointer rounded bg-gray-600 px-3 py-1 text-white hover:bg-gray-700"
						>
							{page.value}
						</Pagination.Page>
					{/if}
				{/each}
			</div>

			<p class="text-sm text-gray-700 dark:text-gray-300">
				{range.start} - {range.end} of {totalItems}
			</p>

			<Pagination.NextButton
				class="flex cursor-pointer items-center rounded bg-gray-600 px-4 py-2 text-white hover:bg-gray-700 disabled:opacity-50"
			>
				<CaretRight class="size-6" />
			</Pagination.NextButton>
		</div>
	{/snippet}
</Pagination.Root>
