# React Best Practices (Quick Reference)

## Core Principle
**UI = f(state)** — When state changes, UI updates. Data flows DOWN (props), events flow UP (callbacks).

## State Management
- **Keep state local** — Only lift up if multiple components need it
- **Never mutate** — Always use setState: `setState([...array, item])` not `array.push(item)`
- **Derive, don't store** — Compute on render: `const total = items.reduce(...)`
- **Structure state** — Group related state: `{ user: { name, email }, errors: { name, email } }`

## useEffect Rules
- **Include dependencies** — Any external variable must be in `[dependencies]`
- **Prevent loops** — Don't create objects/functions in render that are in dependencies
- **Clean up** — Return cleanup function for listeners: `return () => removeEventListener()`
- **Data fetching** — Use `isMounted` flag to prevent state updates after unmount

```javascript
useEffect(() => {
  let isMounted = true;
  fetchData().then(data => {
    if (isMounted) setData(data);
  });
  return () => { isMounted = false; };
}, [dependency]);
```

## Components
- **Break into pieces** — One component = one responsibility
- **Explicit props** — Type props, document them, don't use `props.any`
- **Props are read-only** — Never modify props in child, use callbacks to notify parent
- **All UI states** — Show loading → error → empty → success

```javascript
if (loading) return <Spinner />;
if (error) return <Error msg={error} />;
if (!data) return <Empty />;
return <Success data={data} />;
```

## Common Mistakes ❌
- ❌ State mutation: `state.x = 5`
- ❌ Missing deps: `useEffect(() => fetch(id), [])`
- ❌ Index as key: `map((item, i) => <Item key={i} />)`
- ❌ Derived state: `const [total, setTotal] = useState(0)` (compute instead)
- ❌ Object deps causing loops: Define outside render or use useMemo
- ❌ Race conditions: Don't handle `isMounted` in fetches
- ❌ setState in render: Causes infinite loops

## Optimization (Use Sparingly)
- **React.memo** — Only for expensive components with stable props
- **useCallback** — Only when passing callbacks to React.memo children
- **useMemo** — Only for expensive computations

Default: Don't optimize. Only if you see performance problems.

## Forms (Controlled Components)
```javascript
const [form, setForm] = useState({ email: '', password: '' });

const handleChange = (e) => {
  setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
};

const handleSubmit = (e) => {
  e.preventDefault();
  // submit form
};
```

## TypeScript
```typescript
interface ButtonProps {
  children: React.ReactNode;
  onClick: (e: React.MouseEvent<HTMLButtonElement>) => void;
  disabled?: boolean;
}

function Button({ children, onClick, disabled }: ButtonProps) { }
```

## Pre-Implementation Checklist
- [ ] Where does state live?
- [ ] What are all UI states? (loading, error, empty, success)
- [ ] Proper dependency arrays?
- [ ] Cleanup functions where needed?
- [ ] Props typed and documented?
- [ ] Broken into smaller components?

## Pre-Submission Checklist
- [ ] No console errors?
- [ ] All states working?
- [ ] Mobile responsive?
- [ ] Can explain why structured this way?
- [ ] Semantic HTML & accessible?
- [ ] No unnecessary memoization?