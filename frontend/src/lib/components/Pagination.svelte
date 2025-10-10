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

<Pagination.Root count={totalItems} {perPage} siblingCount={1} bind:page={currentPage}>
	{#snippet children({ pages, range })}
		<div class="flex flex-col items-center justify-center md:flex-row md:gap-4">
			<p class="text-base-content/70 text-sm">
				Showing {range.start} - {range.end} of {totalItems}
			</p>
			<div class="join">
				<Pagination.PrevButton class="join-item btn btn-sm md:btn-md">
					<CaretLeft class="size-4" />
				</Pagination.PrevButton>

				{#each pages as page (page.key)}
					{#if page.type === 'ellipsis'}
						<button class="join-item btn btn-disabled btn-sm md:btn-md select-none">...</button>
					{:else}
						<Pagination.Page {page} class="join-item btn btn-sm md:btn-md data-selected:btn-active">
							{page.value}
						</Pagination.Page>
					{/if}
				{/each}
				<Pagination.NextButton class="join-item btn btn-sm md:btn-md">
					<CaretRight class="size-4" />
				</Pagination.NextButton>
			</div>
		</div>
	{/snippet}
</Pagination.Root>
