module.exports = {
    content: [
        // ---- Templates globales ----
        "../../templates/**/*.html",

        // ---- Todos los templates dentro de app/templates/<app> ----
        "../../**/templates/**/*.html",

        // ---- Templates dentro de theme (si los usas) ----
        "./templates/**/*.html",

        // ---- JS si usas scripts con clases tailwind ----
        "../../static/**/*.js",
        "../../**/static/**/*.js",
    ],
    theme: {
        extend: {
            colors: {
                graphite: {
                    50:  '#f5f5f6',
                    100: '#e5e7eb',
                    200: '#d4d6d9',
                    300: '#a8abb0',
                    400: '#6f7277',
                    500: '#515458',
                    600: '#3b3d40',
                    700: '#2a2c2e',
                    800: '#1d1f21',
                    900: '#131415',
                }
            }
        }
    },
    plugins: [],
}
