window.onload = function () {
    // Extract API version from the URL (e.g., "/api/v1/docs" -> "v1")
    const pathParts = window.location.pathname.split("/");
    const version = pathParts.length >= 3 ? pathParts[2] : "v1";  // Default to v1 if missing

    // Construct the OpenAPI URL dynamically
    const openapiUrl = `/api/${version}/openapi.json`;

    setTimeout(() => {
        fetch(openapiUrl)  // Load the correct OpenAPI schema
            .then(response => response.json())
            .then(spec => {
                spec.host = window.location.host;
                spec.schemes = [window.location.protocol.replace(':', '')];

                spec.info.description = 'To perform authenticated requests, do not use "Authorize" but login via the web UI first.';

                window.ui = SwaggerUIBundle({
                    spec: spec,
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
                    requestInterceptor: request => {
                        // Add custom bearer token so that the user is retrieved from the session
                        // (if logged in)
                        request.headers['Authorization'] = "Bearer swagger-ui";
                        return request;
                    },
                });
            })
            .catch(error => console.error(`Error loading OpenAPI spec for ${version}:`, error));
    }, 1000);
};
