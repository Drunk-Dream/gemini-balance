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

<div class="w-full max-w-md rounded-lg bg-white p-6 shadow-md">
	<h1 class="mb-6 text-center text-2xl font-bold text-gray-800">登录</h1>

	<Notification message={errorMessage} type="error" />

	<form onsubmit={handleLogin}>
		<div class="mb-4">
			<label for="password" class="mb-2 block text-sm font-bold text-gray-700">密码:</label>
			<input
				type="password"
				id="password"
				bind:value={password}
				required
				class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
				placeholder="请输入密码"
			/>
		</div>
		<div class="flex items-center justify-between">
			<button
				type="submit"
				class="btn btn-primary"
				disabled={loading}
			>
				{loading ? '登录中...' : '登录'}
			</button>
		</div>
	</form>
</div>
