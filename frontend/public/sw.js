// This service worker exists solely to unregister any previous service workers
// that might have been accidentally registered or are stale.

self.addEventListener('install', () => {
    // Activate immediately
    self.skipWaiting();
});

self.addEventListener('activate', () => {
    // Unregister this service worker immediately after activation
    self.registration.unregister()
        .then(() => {
            console.log('ServiceWorker unregistered successfully.');
        })
        .catch((error) => {
            console.error('ServiceWorker unregistration failed:', error);
        });
});
