{{flutter_js}}
{{flutter_build_config}}

// Custom bootstrap (docs.flutter.dev/platform-integration/web/initialization): identical to
// the default, plus removing the loading message from index.html once the app is running.
_flutter.loader.load({
  onEntrypointLoaded: async function (engineInitializer) {
    const appRunner = await engineInitializer.initializeEngine();
    await appRunner.runApp();
    document.getElementById("loading")?.remove();
  },
});
