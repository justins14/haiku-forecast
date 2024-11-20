<script lang="ts">
	import '../app.css';
	let { children } = $props();
</script>

{@render children()}

<style>
    :global(body) {
        background-color: #FBE9D0;
        margin: 0;
        min-height: 100vh;
    }
</style>
