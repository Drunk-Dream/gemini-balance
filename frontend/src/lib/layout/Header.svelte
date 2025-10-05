<script lang="ts">
    let { toggleSidebar } = $props();
</script>

<header
    class="fixed left-0 right-0 top-0 z-20 flex items-center justify-between bg-gray-800 p-4 text-white md:hidden"
>
    <div class="text-xl font-bold">Gemini Balance</div>
    <button
        onclick={toggleSidebar}
        class="text-white focus:outline-none"
        aria-label="Toggle sidebar"
    >
        <svg
            class="h-6 w-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
        >
            <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 6h16M4 12h16M4 18h16"
            ></path>
        </svg>
    </button>
</header>
