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

<div class="bg-card w-full max-w-md rounded-lg p-6 shadow-md">
	<h1 class="text-card-foreground mb-6 text-center text-2xl font-bold">登录</h1>

	<Notification message={errorMessage} type="error" />

	<form onsubmit={handleLogin}>
		<div class="mb-4">
			<label for="password" class="text-muted-foreground mb-2 block text-sm font-bold">密码:</label>
			<input
				type="password"
				id="password"
				bind:value={password}
				required
				class="focus:shadow-outline text-muted-foreground w-full appearance-none rounded border px-3 py-2 leading-tight shadow focus:outline-none"
				placeholder="请输入密码"
			/>
		</div>
		<div class="flex items-center justify-between">
			<button type="submit" class="btn bg-primary text-primary-foreground" disabled={loading}>
				{loading ? '登录中...' : '登录'}
			</button>
		</div>
	</form>
</div>
