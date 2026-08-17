# Shared UI Component Library

This folder contains reusable UI components used throughout the IntelliView Orchestrator frontend.

---

## Components

### Button

Reusable button component.

Example:

```jsx
<Button>
  Save
</Button>
```

---

### Card

Reusable container component.

Example:

```jsx
<Card title="Dashboard">
  Dashboard Content
</Card>
```

---

### Input

Reusable text input.

Example:

```jsx
<Input
  value={value}
  onChange={setValue}
  placeholder="Search..."
/>
```

---

### Loader

Displays a loading spinner while data is loading.

Example:

```jsx
<Loader size="md" label="Loading..." />
```

Available sizes:

- sm
- md
- lg

---

### Table

Reusable table component for displaying data.

Example:

```jsx
<Table
  columns={columns}
  data={rows}
/>
```

---

### Dialog (Modal)

Reusable dialog/modal component.

Example:

```jsx
<Dialog open={open} onClose={closeDialog}>
  Modal Content
</Dialog>
```

---

## Purpose

These components are designed to:

- Reduce duplicate code
- Maintain a consistent UI
- Improve maintainability
- Be reusable across all pages

---

## Pages Using Components

These shared components are intended to be used across:

- Dashboard
- Candidates
- Sessions
- Workers
- Interview
- Analysis
- Settings