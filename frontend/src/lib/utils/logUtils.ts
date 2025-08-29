export function colorizeLog(logLine: string): string {
	const patterns = [
		{ regex: /(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})/, class: 'text-gray-400' }, // Timestamp
		{ regex: /\b(INFO)\b/, class: 'font-bold text-emerald-400' }, // Log Level INFO
		{ regex: /\b(ERROR)\b/, class: 'font-bold text-red-400' }, // Log Level ERROR
		{ regex: /\b(WARNING)\b/, class: 'font-bold text-amber-400' }, // Log Level WARNING
		{ regex: /\b(CRITICAL)\b/, class: 'font-bold text-amber-400' }, // Log Level CRITICAL
		{ regex: /\b(DEBUG)\b/, class: 'font-bold text-blue-400' }, // Log Level DEBUG
		{ regex: /\b(true)\b/gi, class: 'text-green-400' }, // Boolean true
		{ regex: /\b(false)\b/gi, class: 'text-red-400' }, // Boolean false
		{ regex: /(key_sha256_[a-zA-Z0-9]{8})\b/g, class: 'text-violet-400' }, // Key suffix
		{ regex: /\b(gemini-[\w.-]+|gpt-[\w.-]+)\b/g, class: 'text-pink-400' } // Model name
	];

	let coloredLogLine = logLine;
	for (const pattern of patterns) {
		coloredLogLine = coloredLogLine.replace(
			pattern.regex,
			`<span class="${pattern.class}">$&</span>`
		);
	}
	return coloredLogLine;
}
