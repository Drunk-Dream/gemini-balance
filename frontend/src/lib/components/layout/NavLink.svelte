<script lang="ts">
    import { page } from '$app/stores';

    let { href, name, onClick } = $props();

    const isActive = $derived($page.url.pathname === href);
</script>

<li class="mb-2">
    <a
        {href}
        class="block rounded-md p-2 transition-colors duration-200 hover:bg-gray-700 {isActive
            ? 'bg-gray-700'
            : ''}"
        onclick={onClick}
    >
        {name}
    </a>
</li>
