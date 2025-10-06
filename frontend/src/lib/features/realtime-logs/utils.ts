import { TZDate } from '@date-fns/tz';
import { format, parse } from 'date-fns';

export function colorizeLog(logLine: string): string {
	// 首先处理时间戳
	const timestampRegex = /(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}Z)/;
	const match = logLine.match(timestampRegex);

	if (match && match[1]) {
		const utcTimestampStr = match[1];
		try {
			const date = parse(utcTimestampStr, 'yyyy-MM-dd HH:mm:ss,SSSXXX', new Date());
			const tzDate = new TZDate(date, Intl.DateTimeFormat().resolvedOptions().timeZone);
			const localTimestampStr = format(tzDate, 'yyyy-MM-dd HH:mm:ss,SSS');
			logLine = logLine.replace(match[0], localTimestampStr);
		} catch (e) {
			console.error('Error parsing or formatting timestamp:', e);
			// 如果解析失败，保留原始时间戳但移除 'Z'
			logLine = logLine.replace(match[0], match[1].slice(0, -1)); // 移除末尾的 'Z'
		}
	}

	const patterns = [
		{ regex: /(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})/, class: 'text-gray-400' }, // Timestamp
		{ regex: /\b(INFO)\b/, class: 'font-bold text-emerald-400' }, // Log Level INFO
		{ regex: /\b(ERROR)\b/, class: 'font-bold text-red-400' }, // Log Level ERROR
		{ regex: /\b(WARNING)\b/, class: 'font-bold text-amber-400' }, // Log Level WARNING
		{ regex: /\b(CRITICAL)\b/, class: 'font-bold text-red-600' }, // Log Level CRITICAL
		{ regex: /\b(DEBUG)\b/, class: 'font-bold text-blue-400' }, // Log Level DEBUG
		{ regex: /\b(true)\b/gi, class: 'text-green-400' }, // Boolean true
		{ regex: /\b(false)\b/gi, class: 'text-red-400' }, // Boolean false
		{ regex: /(AI\w{2}\.{3}\w{4})\b/g, class: 'text-violet-400' }, // Key suffix
		{ regex: /\[Request ID: ([a-fA-F0-9]{8})\]/g, class: 'text-orange-400' }, // Request ID
		{ regex: /\b(OpenAI|Gemini)\b/g, class: 'text-purple-400' }, // OpenAI or Gemini keyword
		{ regex: /\b(gemini-[\w.-]+|gpt-[\w.-]+)\b/g, class: 'text-pink-400' }, // Model name
		{ regex: /'(.*?)'/g, class: 'text-cyan-400' }, // Quoted strings
		{ regex: /\b(\w+_error)\b/g, class: 'text-red-300' } // Any word ending with _error
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
