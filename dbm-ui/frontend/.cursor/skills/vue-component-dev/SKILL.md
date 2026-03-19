---
name: vue-component-dev
description: >-
  创建组件，新建组件，生成组件
---

# Vue Component Development

## Component File Structure

Components live under `src/components/<component-name>/Index.vue`. Use kebab-case for directory names.

```
src/components/
  my-component/
    Index.vue          # Main component entry
    components/        # Sub-components (optional)
      SubPart.vue
```

## SFC Section Order

```vue
<template>
  <!-- template -->
</template>

<script setup lang="ts">
  // script
</script>

<style lang="less" scoped>
  /* styles */
</style>
```

## Script Setup Order

Inside `<script setup lang="ts">`, follow this strict order:

1. External imports (npm packages)
2. Internal imports (path aliases, see import order below)
3. `defineOptions({ name: 'ComponentName' })` (if needed)
4. `defineProps` with interface + `withDefaults`
5. `defineEmits` with type alias
6. `defineModel` (if needed)
7. `defineSlots` (if needed)
8. Composables (`useI18n`, `useRouter`, etc.)
9. Refs and reactive state
10. Computed properties
11. Watchers
12. Methods / functions
13. Lifecycle hooks (`onMounted`, `onBeforeUnmount`, etc.)
14. `defineExpose` (if needed)

## Props Pattern

```typescript
interface Props {
  title?: string;
  count?: number;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  count: 0,
  disabled: false,
});
```

## Emits Pattern

```typescript
type Emits = (e: 'change', value: string) => void;

const emit = defineEmits<Emits>();
```

Multiple events:

```typescript
type Emits = {
  (e: 'change', value: string): void;
  (e: 'update', id: number): void;
};
```

## Import Order

Enforced by ESLint. Follow this sequence:

1. npm packages (`vue`, `lodash`, `tippy.js`)
2. `@blueking/*`
3. `@services/*`
4. `@hooks`
5. `@router`
6. `@stores`
7. `@common/*`
8. `@components/*`
9. `@views/*`
10. `@utils`
11. `@helper/*`
12. `@types`
13. `@locales/*`
14. `@styles/*`
15. `@images/*`
16. Relative imports (parent first, then current directory)

## Template Attribute Order

1. `v-for`
2. `v-if / v-else-if / v-else / v-show`
3. `id`
4. `ref / key`
5. `v-slot`
6. `v-model`
7. Other `v-*` directives
8. Static attributes / dynamic bindings
9. `@event` listeners

## Style Conventions

- Use `lang="less"` (or `postcss` for global utility components)
- Add `scoped` unless styles must leak intentionally
- Class names: kebab-case, prefixed with `dbm-` or component-specific prefix
- Avoid `!important`; use specificity or BEM nesting

## Auto-imported APIs

The project auto-imports Vue APIs (`ref`, `computed`, `watch`, `onMounted`, etc.) — no need to import them explicitly.
Only import non-auto-imported items.

## Checklist

Before finishing a component:

- [ ] Props use `interface` + `withDefaults`
- [ ] Emits use `type` alias
- [ ] No `any` types — use `unknown` or concrete types
- [ ] Import order follows project convention
- [ ] Template attributes follow prescribed order
- [ ] Styles use `lang="less"` with scoped (unless intentional)
- [ ] Comments in Chinese where needed
- [ ] Error handling for async operations (try-catch)
- [ ] Cleanup in `onBeforeUnmount` (tippy, observers, timers, etc.)
