<script lang="ts">
	import CalendarBlank from 'phosphor-svelte/lib/CalendarBlank';
	import { DateFormatter, getLocalTimeZone } from '@internationalized/date';
	import { type DateRange } from 'bits-ui';
	import { cn } from '$lib/lib/utils';
	import { Button } from '$lib/components/ui/button';
	import { RangeCalendar } from '$lib/components/ui/range-calendar';
	import * as Popover from '$lib/components/ui/popover';

	let {
		value = $bindable(),
		limit,
		onValueChange = () => {}
	}: { value: DateRange; limit: DateRange; onValueChange?: (value: DateRange) => void } = $props();

	const df = new DateFormatter('zh-CN', {
		dateStyle: 'medium'
	});
</script>

<Popover.Root>
	<Popover.Trigger>
		{#snippet child({ props })}
			<Button
				variant="outline"
				class={cn(
					'w-full max-w-[360px] justify-start text-left font-normal',
					!value && 'text-muted-foreground'
				)}
				{...props}
			>
				<CalendarBlank class="mr-2 size-4" />
				{#if value && value.start}
					{#if value.end}
						{df.format(value.start.toDate(getLocalTimeZone()))} - {df.format(
							value.end.toDate(getLocalTimeZone())
						)}
					{:else}
						{df.format(value.start.toDate(getLocalTimeZone()))}
					{/if}
				{:else}
					<span>选择日期范围</span>
				{/if}
			</Button>
		{/snippet}
	</Popover.Trigger>
	<Popover.Content class="w-auto p-0" align="start">
		<RangeCalendar
			bind:value
			minValue={limit.start}
			maxValue={limit.end}
			numberOfMonths={2}
			onValueChange={(v: DateRange) => {
				value = v;
				onValueChange(v);
			}}
		/>
	</Popover.Content>
</Popover.Root>
