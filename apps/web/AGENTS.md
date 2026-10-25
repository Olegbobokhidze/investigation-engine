# Frontend (apps/web) — agent guide

React 19, TypeScript (strict), Vite, Tailwind CSS 4, TanStack Query, React Router, MSW.
Run commands from the repo root via `make web-*`, or from this folder via `pnpm …`.

## Layout

```
src/
├── app/            router, layout, QueryClient — wiring only
├── features/<name>/
│   ├── types.ts    API contract types for this feature
│   ├── api.ts      request functions + TanStack Query hooks
│   ├── <Name>Page.tsx
│   └── components/ components used only by this feature
├── shared/         api client, config, hooks, ui/ (reusable components)
├── mocks/          MSW handlers + fixtures that mirror the backend
└── styles/index.css  design tokens (@theme)
```

A feature may import from `shared/`; `shared/` never imports from a feature.

## Rules

- **Design tokens only.** Colors, font sizes and radii come from `styles/index.css`; the
  default Tailwind palette and type scale are disabled on purpose. Arbitrary values
  (`w-[…]`) are for one-off layout, never for color or type.
- **`className` props are for layout** (margin, flex, width). Size and tone are explicit props
  (`size="md"`, `tone="danger"`) — there is no `tailwind-merge`, so overriding a component's
  own classes is unreliable.
- **Data fetching** goes through hooks in `features/*/api.ts`; components never call
  `fetch` or `apiRequest` directly. Mutations that change a list invalidate its query keys.
- **Errors** surface as `ApiError` and render with `ErrorNotice`; show the API's message.
- **Accessibility:** real `<button>`/`<a>`/`<label>`, `aria-label` on icon-only buttons
  (`IconButton` requires `label`), visible focus via the `focus-ring` utility.
- **No native browser dialogs** (`alert`, `confirm`, `prompt`) — use `ConfirmDialog`.
- **Mocks mirror the backend.** When the contract changes, update `types.ts`, the MSW
  handlers and the fixtures together.
- **Components:** function declarations with named exports, props interface `<Name>Props`
  above the component, one exported component per file.
- **Tests:** Vitest + Testing Library; query by role or label, not by class or test id.
