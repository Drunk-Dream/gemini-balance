<script lang="ts">
	// 导入 Notification 组件
	import Notification from '$lib/components/Notification.svelte';
	let {
		password = $bindable(),
		handleLogin,
		loading,
		errorMessage
	}: {
		password: string;
		handleLogin: () => Promise<void>;
		loading: boolean;
		errorMessage: string | null;
	} = $props();
</script>

<div class="bg-base-300 w-full max-w-md rounded-lg p-6 shadow-md">
	<h1 class="text-base-content/80 mb-6 text-center text-2xl font-bold">登录</h1>

	<Notification message={errorMessage} type="error" />

	<form onsubmit={handleLogin}>
		<div class="mb-4">
			<label for="password" class="text-base-content/70 mb-2 block text-sm font-bold">密码:</label>
			<input
				type="password"
				id="password"
				bind:value={password}
				required
				class="focus:shadow-outline text-base-content/70 w-full appearance-none rounded border px-3 py-2 leading-tight shadow focus:outline-none"
				placeholder="请输入密码"
			/>
		</div>
		<div class="flex items-center justify-between">
			<button type="submit" class="btn btn-primary" disabled={loading}>
				{loading ? '登录中...' : '登录'}
			</button>
		</div>
	</form>
</div>
