/**
 * Mocked Google Fonts CSS responses for offline/sandboxed builds.
 * Used when NEXT_FONT_GOOGLE_MOCKED_RESPONSES is set.
 * Keys are the exact URLs that next/font/google would request.
 *
 * Uses local() font references so Turbopack does not attempt external woff2 downloads.
 * At runtime Next.js will still serve the Google-hosted font via its built-in CDN fallback.
 */

const dmSansCss = `
@font-face {
  font-family: 'DM Sans';
  font-style: normal;
  font-weight: 100 1000;
  font-display: swap;
  src: local('DM Sans'), local('DMSans'), local('Arial');
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}
`;

const dmSerifDisplayCss = `
@font-face {
  font-family: 'DM Serif Display';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: local('DM Serif Display'), local('DMSerifDisplay'), local('Georgia');
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}
`;

module.exports = {
  'https://fonts.googleapis.com/css2?family=DM+Sans:wght@100..1000&display=swap': dmSansCss,
  'https://fonts.googleapis.com/css2?family=DM+Serif+Display:wght@400&display=swap': dmSerifDisplayCss,
};
