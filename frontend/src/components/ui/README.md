# UI Component Library

Shared, reusable React components for the IntelliView Orchestrator dashboard.
All components are typed, accessible, and use the project's design tokens from `tailwind.config.ts`.

## Import

```js
import { Button, Input, Table, Thead, Tbody, Tr, Th, Td, Shimmer, Spinner, PageLoader } from "@/components/ui";
```

---

## Button

A versatile button with variant, size, loading, and icon support.

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `variant` | `"primary" \| "secondary" \| "ghost" \| "danger"` | `"secondary"` | Visual style |
| `size` | `"sm" \| "md" \| "lg"` | `"md"` | Height and padding |
| `loading` | `boolean` | `false` | Shows a spinner and disables the button |
| `icon` | `ReactNode` | — | Leading icon element |
| `disabled` | `boolean` | `false` | Native disabled state |
| `className` | `string` | — | Extra Tailwind classes |

```jsx
import { Button } from "@/components/ui";
import { Plus } from "lucide-react";

// Primary action
<Button variant="primary" icon={<Plus size={14} />}>New session</Button>

// Loading state
<Button variant="primary" loading>Saving…</Button>

// Danger / destructive
<Button variant="danger">Delete worker</Button>

// Ghost / icon-only
<Button variant="ghost" icon={<Keyboard size={14} />} aria-label="Shortcuts" />
```

---

## Input

A labelled text input with error, hint, and leading-icon support.

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `label` | `string` | — | Label rendered above the input |
| `error` | `string` | — | Error message (turns border red) |
| `hint` | `string` | — | Helper text below the input |
| `icon` | `ReactNode` | — | Leading icon (e.g. from lucide-react) |
| `className` | `string` | — | Extra classes on the outer wrapper |
| `inputClassName` | `string` | — | Extra classes on the `<input>` element |
| All native `<input>` props | | | `type`, `value`, `onChange`, `placeholder`, etc. |

```jsx
import { Input, SearchInput } from "@/components/ui";
import { Mail } from "lucide-react";

// Labelled input with icon
<Input
  label="Email"
  type="email"
  placeholder="you@example.com"
  icon={<Mail size={14} />}
/>

// Error state
<Input label="API Token" error="Token is invalid" />

// Pre-built search input
<SearchInput value={q} onChange={setQ} placeholder="Filter sessions…" />
```

---

## Card

A panel with an optional header (title, description, action slot) and body.

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `title` | `string` | — | Card heading |
| `description` | `string` | — | Sub-heading below the title |
| `action` | `ReactNode` | — | Trailing slot in the header (e.g. a Button) |
| `footer` | `ReactNode` | — | Footer slot below the body |
| `className` | `string` | — | Extra classes on the `<section>` |

```jsx
import Card from "@/components/Card";
import { Button } from "@/components/ui";

<Card
  title="Active Sessions"
  description="In-flight interviews across the cluster."
  action={<Button size="sm">Refresh</Button>}
>
  {/* body */}
</Card>
```

---

## Table

Composable table primitives. Use `Table` as the root, then compose with `Thead`, `Tbody`, `Tr`, `Th`, and `Td`.

```jsx
import { Table, Thead, Tbody, Tr, Th, Td } from "@/components/ui";

<Table>
  <Thead>
    <Tr>
      <Th>Worker ID</Th>
      <Th>Status</Th>
      <Th>Load</Th>
    </Tr>
  </Thead>
  <Tbody>
    {workers.map((w) => (
      <Tr key={w.id} onClick={() => navigate(w.id)}>
        <Td className="font-mono text-xs">{w.id}</Td>
        <Td><StatusBadge status={w.status} /></Td>
        <Td>{w.active}/{w.capacity}</Td>
      </Tr>
    ))}
  </Tbody>
</Table>
```

`Tr` automatically becomes `cursor-pointer` when an `onClick` prop is passed.

---

## Modal (Dialog)

An animated, focus-trapped, accessible modal.

| Prop | Type | Description |
|------|------|-------------|
| `open` | `boolean` | Controls visibility |
| `onOpenChange` | `(open: boolean) => void` | Called on backdrop click or Escape |

Use `DialogContent` and `DialogTitle` as children.

```jsx
import { Dialog, DialogContent, DialogTitle } from "@/components/Dialog";
import { Button } from "@/components/ui";

const [open, setOpen] = useState(false);

<Button variant="primary" onClick={() => setOpen(true)}>Open</Button>

<Dialog open={open} onOpenChange={setOpen}>
  <DialogContent onClose={() => setOpen(false)} className="max-w-md">
    <div className="p-6">
      <DialogTitle>Confirm deletion</DialogTitle>
      <p className="mt-2 text-sm text-muted">This cannot be undone.</p>
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
        <Button variant="danger">Delete</Button>
      </div>
    </div>
  </DialogContent>
</Dialog>
```

---

## Loader

Three loading primitives.

### Shimmer
Animated skeleton placeholder for content that's loading.

```jsx
import { Shimmer } from "@/components/ui";

// Size via className
<Shimmer className="h-8 w-32" />
<Shimmer className="h-4 w-full" />
```

### Spinner
Circular animated SVG indicator.

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `size` | `"sm" \| "md" \| "lg"` | `"md"` | Pixel size (14 / 20 / 32) |
| `className` | `string` | — | e.g. `"text-accent"` for color |

```jsx
import { Spinner } from "@/components/ui";

<Spinner />
<Spinner size="lg" className="text-accent" />
```

### PageLoader
Full-panel centered spinner, ideal for Suspense boundaries.

```jsx
import { PageLoader } from "@/components/ui";

<PageLoader />
```
