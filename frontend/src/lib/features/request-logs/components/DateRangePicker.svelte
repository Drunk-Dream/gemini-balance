<script lang="ts">
	import { DateRangePicker, type DateRange } from 'bits-ui';
	import CalendarBlank from 'phosphor-svelte/lib/CalendarBlank';
	import CaretLeft from 'phosphor-svelte/lib/CaretLeft';
	import CaretRight from 'phosphor-svelte/lib/CaretRight';

	let {
		value,
		limit,
		onValueChange = () => {}
	}: { value: DateRange; limit: DateRange; onValueChange?: (value: DateRange) => void } = $props();
</script>

<DateRangePicker.Root
	weekdayFormat="short"
	fixedWeeks={true}
	class="flex w-full max-w-[360px] flex-col gap-1.5"
	minValue={limit.start}
	maxValue={limit.end}
	{value}
	{onValueChange}
>
	<DateRangePicker.Label class="block select-none text-sm font-medium"
		>选择日期范围</DateRangePicker.Label
	>
	<div
		class="input input-bordered focus-within:ring-primary hover:border-base-content/40 flex h-10 w-full select-none items-center px-2 py-3 text-sm tracking-[0.01em] transition-colors focus-within:outline-none focus-within:ring-1"
	>
		{#each ['start', 'end'] as const as type (type)}
			<DateRangePicker.Input {type}>
				{#snippet children({ segments })}
					{#each segments as { part, value }, i (part + i)}
						<div class="inline-block select-none">
							{#if part === 'literal'}
								<DateRangePicker.Segment {part} class="text-base-content/60 p-1">
									{value}
								</DateRangePicker.Segment>
							{:else}
								<DateRangePicker.Segment
									{part}
									class="focus-visible:ring-0! focus-visible:ring-offset-0! hover:bg-base-200 focus:bg-base-200 focus:text-base-content aria-[valuetext=Empty]:text-base-content/40 rounded-md px-1 py-1"
								>
									{value}
								</DateRangePicker.Segment>
							{/if}
						</div>
					{/each}
				{/snippet}
			</DateRangePicker.Input>
			{#if type === 'start'}
				<div aria-hidden="true" class="text-base-content/60 px-1"></div>
			{/if}
		{/each}
		<DateRangePicker.Trigger
			class="btn btn-ghost btn-square ml-auto inline-flex size-8 items-center justify-center rounded-md transition-all"
		>
			<CalendarBlank class="size-6" />
		</DateRangePicker.Trigger>
	</div>
	<DateRangePicker.Content sideOffset={6} class="z-50">
		<DateRangePicker.Calendar
			class="border-base-300 bg-base-100 mt-6 rounded-xl border p-4 shadow-lg"
		>
			{#snippet children({ months, weekdays })}
				<DateRangePicker.Header class="flex items-center justify-between">
					<DateRangePicker.PrevButton
						class="btn btn-ghost btn-square inline-flex size-10 items-center justify-center rounded-lg transition-all"
					>
						<CaretLeft class="size-6" />
					</DateRangePicker.PrevButton>
					<DateRangePicker.Heading class="text-[15px] font-medium" />
					<DateRangePicker.NextButton
						class="btn btn-ghost btn-square inline-flex size-10 items-center justify-center rounded-lg transition-all"
					>
						<CaretRight class="size-6" />
					</DateRangePicker.NextButton>
				</DateRangePicker.Header>
				<div class="flex flex-col space-y-4 pt-4 sm:flex-row sm:space-x-4 sm:space-y-0">
					{#each months as month (month.value)}
						<DateRangePicker.Grid class="w-full border-collapse select-none space-y-1">
							<DateRangePicker.GridHead>
								<DateRangePicker.GridRow class="mb-1 flex w-full justify-between">
									{#each weekdays as day (day)}
										<DateRangePicker.HeadCell class="text-base-content/60 w-10 text-xs font-normal">
											<div>{day.slice(0, 2)}</div>
										</DateRangePicker.HeadCell>
									{/each}
								</DateRangePicker.GridRow>
							</DateRangePicker.GridHead>
							<DateRangePicker.GridBody>
								{#each month.weeks as weekDates (weekDates)}
									<DateRangePicker.GridRow class="flex w-full">
										{#each weekDates as date (date)}
											<DateRangePicker.Cell
												{date}
												month={month.value}
												class="p-0! relative m-0 size-10 overflow-visible text-center text-sm focus-within:relative focus-within:z-20"
											>
												<DateRangePicker.Day
													class="focus-visible:ring-primary! data-selection-end:rounded-r-lg data-selection-start:rounded-l-lg data-highlighted:bg-base-200 data-selected:bg-primary/10 data-selection-end:bg-primary data-selection-start:bg-primary data-disabled:pointer-events-none data-disabled:text-base-content/30 data-highlighted:rounded-none data-outside-month:pointer-events-none data-selected:font-medium data-selected:text-primary data-selection-end:font-medium data-selection-end:text-primary-content data-selection-start:font-medium data-selection-start:text-primary-content data-selection-start:focus-visible:ring-2 data-selection-start:focus-visible:ring-offset-2! data-unavailable:line-through data-unavailable:text-base-content/40 data-selected:[&:not([data-selection-start])]:[&:not([data-selection-end])]:rounded-none data-selected:[&:not([data-selection-start])]:[&:not([data-selection-end])]:focus-visible:ring-0! data-selected:[&:not([data-selection-start])]:[&:not([data-selection-end])]:focus-visible:ring-offset-0! text-base-content hover:border-primary group relative inline-flex size-10 items-center justify-center whitespace-nowrap border border-transparent bg-transparent p-0 text-sm font-normal transition-all hover:rounded-lg"
												>
													<div
														class="group-data-selected:bg-base-100 group-data-today:block bg-primary absolute top-[5px] hidden size-1 rounded-full transition-all"
													></div>
													{date.day}
												</DateRangePicker.Day>
											</DateRangePicker.Cell>
										{/each}
									</DateRangePicker.GridRow>
								{/each}
							</DateRangePicker.GridBody>
						</DateRangePicker.Grid>
					{/each}
				</div>
			{/snippet}
		</DateRangePicker.Calendar>
	</DateRangePicker.Content>
</DateRangePicker.Root>
