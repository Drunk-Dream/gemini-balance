<script lang="ts">
	import * as Pagination from '$lib/components/ui/pagination';
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
		<Pagination.Content>
			<div class="text-muted-foreground mr-4 hidden text-sm md:block">
				Showing {range.start} - {range.end} of {totalItems}
			</div>
			<Pagination.Item>
				<Pagination.PrevButton>
					<CaretLeft class="size-4" />
				</Pagination.PrevButton>
			</Pagination.Item>
			{#each pages as page (page.key)}
				{#if page.type === 'ellipsis'}
					<Pagination.Item>
						<Pagination.Ellipsis />
					</Pagination.Item>
				{:else}
					<Pagination.Item>
						<Pagination.Link {page} isActive={currentPage === page.value}>
							{page.value}
						</Pagination.Link>
					</Pagination.Item>
				{/if}
			{/each}
			<Pagination.Item>
				<Pagination.NextButton>
					<CaretRight class="size-4" />
				</Pagination.NextButton>
			</Pagination.Item>
		</Pagination.Content>
	{/snippet}
</Pagination.Root>
