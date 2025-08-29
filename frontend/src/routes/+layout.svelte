<script lang="ts">
    import Header from '$lib/components/layout/Header.svelte';
    import Sidebar from '$lib/components/layout/Sidebar.svelte';
    import '../app.css';

    let { children } = $props();

    let sidebarOpen = $state(false);
    let isMobile = $state(false);

    function toggleSidebar() {
        sidebarOpen = !sidebarOpen;
    }

    $effect(() => {
        const handleResize = () => {
            isMobile = window.innerWidth < 768;
            if (!isMobile) {
                sidebarOpen = false; // Close sidebar on desktop
            }
        };

        if (typeof window !== 'undefined') {
            handleResize(); // Initial check
            window.addEventListener('resize', handleResize);
            return () => window.removeEventListener('resize', handleResize);
        }
    });
</script>

<div class="flex h-screen bg-gray-100">
    <Header {toggleSidebar} />

    <Sidebar {sidebarOpen} {toggleSidebar} {isMobile} />

    <!-- Main content -->
    <main class="mt-16 flex-1 overflow-y-auto p-4 md:mt-0 md:p-6">
        {@render children()}
    </main>
</div>
