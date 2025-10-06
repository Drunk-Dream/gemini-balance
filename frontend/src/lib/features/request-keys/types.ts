export interface KeyStatus {
	key_identifier: string;
	key_brief: string;
	status: 'active' | 'cooling_down' | 'in_use';
	cool_down_seconds_remaining: number;
	failure_count: number;
	cool_down_entry_count: number;
	current_cool_down_seconds: number;
}

export interface KeyStatusResponse {
	keys: KeyStatus[];
	total_keys_count: number;
	in_use_keys_count: number;
	cooled_down_keys_count: number;
	available_keys_count: number;
}