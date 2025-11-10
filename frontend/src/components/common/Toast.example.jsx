/**
 * Toast Component Usage Examples
 * 
 * This file demonstrates how to use the Toast notification system.
 * DO NOT import this file in production code - it's for reference only.
 */

import { useToast } from '../../hooks/useToast';

// Example 1: Success Toast
function SuccessExample() {
  const { addToast } = useToast();
  
  const handleSave = () => {
    // ... save logic
    addToast('Choreography saved successfully!', 'success');
  };
  
  return <button onClick={handleSave}>Save</button>;
}

// Example 2: Error Toast
function ErrorExample() {
  const { addToast } = useToast();
  
  const handleSubmit = async () => {
    try {
      // ... API call
    } catch (error) {
      addToast(error.message || 'Something went wrong', 'error');
    }
  };
  
  return <button onClick={handleSubmit}>Submit</button>;
}

// Example 3: Warning Toast
function WarningExample() {
  const { addToast } = useToast();
  
  const handleDelete = () => {
    addToast('This action cannot be undone', 'warning');
    // ... delete logic
  };
  
  return <button onClick={handleDelete}>Delete</button>;
}

// Example 4: Info Toast
function InfoExample() {
  const { addToast } = useToast();
  
  const handleInfo = () => {
    addToast('Generation will take 2-3 minutes', 'info');
  };
  
  return <button onClick={handleInfo}>Start Generation</button>;
}

// Example 5: In API calls
async function apiCallExample() {
  const { addToast } = useToast();
  
  try {
    const response = await fetch('/api/collections/save/', {
      method: 'POST',
      body: JSON.stringify(data)
    });
    
    if (response.ok) {
      addToast('Collection saved!', 'success');
    } else {
      addToast('Failed to save collection', 'error');
    }
  } catch (error) {
    addToast('Network error. Please try again.', 'error');
  }
}

export { SuccessExample, ErrorExample, WarningExample, InfoExample };
