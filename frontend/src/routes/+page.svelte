<script lang="ts">
	import Container from '$lib/components/Container.svelte';

	const navLinks = [
		{
			name: '请求密钥',
			href: '/request-keys',
			description: '管理用于请求上游大模型 API 的服务密钥。'
		},
		{ name: '认证密钥', href: '/auth-keys', description: '管理用户访问此服务的个人 API 密钥。' },
		{ name: '实时日志', href: '/realtime-logs', description: '查看实时的 API 请求日志流。' },
		{ name: '请求日志', href: '/request-logs', description: '查询和检索详细的 API 请求历史日志。' },
		{ name: '统计看板', href: '/stats', description: '查看 API 使用情况的统计数据和图表。' }
	];
</script>

<Container header="欢迎使用 Gemini Balance">
	<p class="mb-12 text-center text-lg text-gray-600">一个高效、安全的 API 请求转发服务</p>
	<div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
		{#each navLinks as link}
			<a
				href={link.href}
				class="group block transform rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-1 hover:shadow-xl"
			>
				<h2 class="mb-2 text-2xl font-bold text-gray-900 group-hover:text-blue-600">{link.name}</h2>
				<p class="text-gray-600">{link.description}</p>
			</a>
		{/each}
	</div>
</Container>
