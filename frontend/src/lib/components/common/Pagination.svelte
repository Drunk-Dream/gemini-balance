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

	let totalPages = Math.ceil(totalItems / perPage);
	// Function to handle page changes from bits-ui and call the external goToPage prop
	function handlePageChange(page: number) {
		if (page >= 1 && page <= totalPages) {
			currentPage = page;
		}
	}
</script>

<Pagination.Root
	count={totalItems}
	{perPage}
	siblingCount={2}
	bind:page={currentPage}
	onPageChange={handlePageChange}
>
	{#snippet children({ pages, range })}
		<div class="mt-4 flex flex-col items-center justify-between space-y-4 md:flex-row md:space-y-0">
			<Pagination.PrevButton
				class="flex cursor-pointer items-center rounded bg-blue-500 px-4 py-2 text-white disabled:opacity-50"
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
							class="data-selected:bg-blue-700 data-selected:text-white cursor-pointer rounded bg-blue-500 px-3 py-1 text-white"
						>
							{page.value}
						</Pagination.Page>
					{/if}
				{/each}
			</div>

			<div class="flex items-center space-x-2 text-sm md:text-base">
				<span class="whitespace-nowrap"
					>第 <input
						type="number"
						min="1"
						max={totalPages}
						value={currentPage}
						onchange={(e) => handlePageChange(parseInt((e.target as HTMLInputElement).value))}
						class="h-6 w-16 rounded border px-3 py-1 text-center text-sm md:w-20 md:text-base"
					/>
					/ {totalPages} 页 (共 {totalItems} 条)</span
				>
			</div>

			<Pagination.NextButton
				class="flex cursor-pointer items-center rounded bg-blue-500 px-4 py-2 text-white disabled:opacity-50"
			>
				<CaretRight class="size-6" />
			</Pagination.NextButton>
		</div>
	{/snippet}
</Pagination.Root>
