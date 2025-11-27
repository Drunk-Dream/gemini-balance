<script lang="ts">
	// 导入 Notification 组件
	import Notification from '$lib/components/Notification.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import * as Card from '$lib/components/ui/card';

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

<Card.Root class="w-full max-w-md">
	<Card.Header>
		<Card.Title class="text-center text-2xl">登录</Card.Title>
	</Card.Header>
	<Card.Content>
		<Notification message={errorMessage} type="error" />

		<form onsubmit={handleLogin} class="space-y-4">
			<div class="space-y-2">
				<Label for="password">密码</Label>
				<Input
					type="password"
					id="password"
					bind:value={password}
					required
					placeholder="请输入密码"
				/>
			</div>
			<Button type="submit" class="w-full" disabled={loading}>
				{loading ? '登录中...' : '登录'}
			</Button>
		</form>
	</Card.Content>
</Card.Root>
