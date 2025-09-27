export interface KeyStatus {
	key_identifier: string;
	key_brief: string;
	status: 'active' | 'cooling_down' | 'in_use';
	cool_down_seconds_remaining: number;
	daily_usage: { [model: string]: number };
	failure_count: number;
	cool_down_entry_count: number;
	current_cool_down_seconds: number;
}
