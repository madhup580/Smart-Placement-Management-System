# UI/UX Components Usage Guide

## Overview
This document describes the new UI/UX components: Skeleton Loaders, Toast Notifications, Undo Actions, Keyboard Navigation, and Accessibility features.

## 1. Skeleton Loaders

### Basic Usage
```javascript
// Show skeleton loader
const container = document.getElementById('my-content');
SkeletonLoader.show(container, 'text', { lines: 3 });

// Hide skeleton and restore content
SkeletonLoader.hide(container);
```

### Types
- `text` - Text lines skeleton
- `circle` - Circular skeleton (for avatars)
- `rect` - Rectangle skeleton
- `card` - Card skeleton with header and content
- `table` - Table skeleton with rows and columns

### Example
```javascript
// Show skeleton while loading
const dashboardContainer = document.getElementById('dashboard-content');
SkeletonLoader.show(dashboardContainer, 'card');

// After data loads
fetch('/api/dashboard')
    .then(res => res.json())
    .then(data => {
        SkeletonLoader.hide(dashboardContainer);
        // Render data
    });
```

## 2. Toast Notifications

### Basic Usage
```javascript
// Success toast
toastManager.success('Operation completed successfully!');

// Error toast
toastManager.error('Something went wrong!');

// Warning toast
toastManager.warning('Please check your input');

// Info toast
toastManager.info('New update available');
```

### Advanced Usage
```javascript
// Toast with action button
toastManager.show('Item deleted', 'success', {
    action: 'Undo',
    onAction: () => {
        // Undo action
        restoreItem();
    },
    duration: 5000
});
```

## 3. Undo Actions

### Basic Usage
```javascript
// Register an action
undoManager.register(
    'Deleted item',
    () => {
        // Undo function
        restoreItem();
    },
    () => {
        // Redo function (optional)
        deleteItem();
    }
);
```

### Keyboard Shortcuts
- `Ctrl+Z` - Undo
- `Ctrl+Y` or `Ctrl+Shift+Z` - Redo

### Example
```javascript
function deleteItem(itemId) {
    const item = getItem(itemId);
    removeItem(itemId);
    
    // Register undo
    undoManager.register(
        `Deleted ${item.name}`,
        () => restoreItem(item),
        () => removeItem(itemId)
    );
}
```

## 4. Keyboard Navigation

### Register Shortcuts
```javascript
// Register custom shortcut
keyboardNav.register('Ctrl+S', (e) => {
    e.preventDefault();
    saveDocument();
}, {
    preventDefault: true,
    description: 'Save document'
});
```

### Default Shortcuts
- `Escape` - Close modals
- `Ctrl+Z` - Undo
- `Ctrl+Y` - Redo
- `Ctrl+Shift+Z` - Redo (alternative)
- `Ctrl+K` - Focus search

### Focus Trap
Modals automatically trap focus for keyboard navigation.

## 5. Accessibility

### Set ARIA Labels
```javascript
AccessibilityHelper.setLabel(button, 'Close dialog');
```

### Announce to Screen Readers
```javascript
AccessibilityHelper.announce('Page loaded successfully', 'polite');
```

### Make Elements Focusable
```javascript
AccessibilityHelper.makeFocusable(customButton, 0);
```

### Skip Links
Skip links are automatically added for main content navigation.

## Integration Examples

### Loading Dashboard with Skeleton
```javascript
async function loadDashboard() {
    const container = document.getElementById('dashboard');
    
    // Show skeleton
    SkeletonLoader.show(container, 'card');
    
    try {
        const data = await fetch('/api/dashboard').then(r => r.json());
        
        // Hide skeleton and render
        SkeletonLoader.hide(container);
        renderDashboard(data);
        
        // Show success toast
        toastManager.success('Dashboard loaded');
    } catch (error) {
        SkeletonLoader.hide(container);
        toastManager.error('Failed to load dashboard');
    }
}
```

### Delete with Undo
```javascript
function deleteQuestion(questionId) {
    const question = getQuestion(questionId);
    
    // Delete
    removeQuestion(questionId);
    
    // Register undo
    undoManager.register(
        `Deleted question: ${question.title}`,
        () => restoreQuestion(question),
        () => removeQuestion(questionId)
    );
    
    // Show toast with undo
    toastManager.success('Question deleted', {
        action: 'Undo',
        onAction: () => undoManager.undo()
    });
}
```

### Form Submission with Loading
```javascript
async function submitForm(formData) {
    const formContainer = document.getElementById('form-container');
    
    // Show skeleton
    SkeletonLoader.show(formContainer, 'text', { lines: 2 });
    
    try {
        const result = await fetch('/api/submit', {
            method: 'POST',
            body: formData
        });
        
        SkeletonLoader.hide(formContainer);
        toastManager.success('Form submitted successfully!');
        
        // Announce to screen readers
        AccessibilityHelper.announce('Form submitted successfully');
    } catch (error) {
        SkeletonLoader.hide(formContainer);
        toastManager.error('Submission failed');
    }
}
```

## Best Practices

1. **Always use skeleton loaders** for async operations longer than 200ms
2. **Use toast notifications** for non-critical feedback (success, info)
3. **Use modals** for critical actions requiring confirmation
4. **Register undo actions** for destructive operations
5. **Add ARIA labels** to all interactive elements
6. **Test keyboard navigation** - ensure all features are accessible via keyboard
7. **Respect reduced motion** - animations are automatically disabled for users who prefer reduced motion

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Accessibility features work with screen readers (NVDA, JAWS, VoiceOver)
- Keyboard navigation works in all browsers
- Reduced motion support for users with motion sensitivity
