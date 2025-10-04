<script lang="ts">
	import { DateRangePicker, type DateRange } from 'bits-ui';
	import CalendarBlank from 'phosphor-svelte/lib/CalendarBlank';
	import CaretLeft from 'phosphor-svelte/lib/CaretLeft';
	import CaretRight from 'phosphor-svelte/lib/CaretRight';

	let {
		value,
		onValueChange = () => {}
	}: { value: DateRange; onValueChange?: (value: DateRange) => void } = $props();
</script>

<DateRangePicker.Root
	weekdayFormat="short"
	fixedWeeks={true}
	class="flex w-full max-w-[360px] flex-col gap-1.5"
	{value}
	{onValueChange}
>
	<DateRangePicker.Label class="block select-none text-sm font-medium"
		>选择日期范围</DateRangePicker.Label
	>
	<div
		class="flex h-10 w-full select-none items-center rounded-md border border-gray-300 bg-white px-2 py-3 text-sm tracking-[0.01em] text-gray-900 shadow-sm transition-colors focus-within:border-gray-500 focus-within:ring-1 focus-within:ring-gray-500 hover:border-gray-400"
	>
		{#each ['start', 'end'] as const as type (type)}
			<DateRangePicker.Input {type}>
				{#snippet children({ segments })}
					{#each segments as { part, value }, i (part + i)}
						<div class="inline-block select-none">
							{#if part === 'literal'}
								<DateRangePicker.Segment {part} class="p-1 text-gray-500">
									{value}
								</DateRangePicker.Segment>
							{:else}
								<DateRangePicker.Segment
									{part}
									class="focus-visible:ring-0! focus-visible:ring-offset-0! rounded-md px-1 py-1 hover:bg-gray-100 focus:bg-gray-100 focus:text-gray-900 aria-[valuetext=Empty]:text-gray-400"
								>
									{value}
								</DateRangePicker.Segment>
							{/if}
						</div>
					{/each}
				{/snippet}
			</DateRangePicker.Input>
			{#if type === 'start'}
				<div aria-hidden="true" class="text-muted-foreground px-1"></div>
			{/if}
		{/each}
		<DateRangePicker.Trigger
			class="ml-auto inline-flex size-8 items-center justify-center rounded-md text-gray-500 transition-all hover:bg-gray-100 active:bg-gray-200"
		>
			<CalendarBlank class="size-6" />
		</DateRangePicker.Trigger>
	</div>
	<DateRangePicker.Content sideOffset={6} class="z-50">
		<DateRangePicker.Calendar class="mt-6 rounded-xl border border-gray-200 bg-white p-4 shadow-lg">
			{#snippet children({ months, weekdays })}
				<DateRangePicker.Header class="flex items-center justify-between">
					<DateRangePicker.PrevButton
						class="inline-flex size-10 items-center justify-center rounded-lg bg-white transition-all hover:bg-gray-100 active:scale-[0.98]"
					>
						<CaretLeft class="size-6" />
					</DateRangePicker.PrevButton>
					<DateRangePicker.Heading class="text-[15px] font-medium" />
					<DateRangePicker.NextButton
						class="inline-flex size-10 items-center justify-center rounded-lg bg-white transition-all hover:bg-gray-100 active:scale-[0.98]"
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
										<DateRangePicker.HeadCell class="w-10 text-xs font-normal text-gray-500">
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
													class="focus-visible:ring-gray-500! data-selection-end:rounded-lg data-selection-start:rounded-lg data-highlighted:bg-gray-100 data-selected:bg-gray-200 data-selection-end:bg-gray-600 data-selection-start:bg-gray-600 data-disabled:pointer-events-none data-disabled:text-gray-300 data-highlighted:rounded-none data-outside-month:pointer-events-none data-selected:font-medium data-selected:text-white data-selection-end:font-medium data-selection-end:text-white data-selection-start:font-medium data-selection-start:text-white data-selection-start:focus-visible:ring-2 data-selection-start:focus-visible:ring-offset-2! data-unavailable:line-through data-unavailable:text-gray-400 data-selected:[&:not([data-selection-start])]:[&:not([data-selection-end])]:rounded-none data-selected:[&:not([data-selection-start])]:[&:not([data-selection-end])]:focus-visible:ring-0! data-selected:[&:not([data-selection-start])]:[&:not([data-selection-end])]:focus-visible:ring-offset-0! group relative inline-flex size-10 items-center justify-center whitespace-nowrap rounded-lg border border-transparent bg-transparent p-0 text-sm font-normal text-gray-900 transition-all hover:border-gray-500"
												>
													<div
														class="group-data-selected:bg-white group-data-today:block absolute top-[5px] hidden size-1 rounded-full bg-gray-900 transition-all"
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
