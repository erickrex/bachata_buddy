// Modal Component
// Accessible modal dialog with focus trap and backdrop

import { useEffect, useRef } from 'react';

function Modal({ 
  isOpen, 
  onClose, 
  children, 
  title,
  className = '',
  closeOnBackdrop = true,
  closeOnEsc = true,
  ...props 
}) {
  const modalRef = useRef(null);
  const previousActiveElement = useRef(null);
  
  // Handle ESC key press
  useEffect(() => {
    if (!isOpen || !closeOnEsc) return;
    
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, closeOnEsc, onClose]);
  
  // Prevent body scroll when modal is open
  useEffect(() => {
    if (!isOpen) return;
    
    // Save current scroll position
    const scrollY = window.scrollY;
    document.body.style.position = 'fixed';
    document.body.style.top = `-${scrollY}px`;
    document.body.style.width = '100%';
    
    return () => {
      // Restore scroll position
      document.body.style.position = '';
      document.body.style.top = '';
      document.body.style.width = '';
      window.scrollTo(0, scrollY);
    };
  }, [isOpen]);
  
  // Focus trap implementation
  useEffect(() => {
    if (!isOpen || !modalRef.current) return;
    
    // Store the element that had focus before modal opened
    previousActiveElement.current = document.activeElement;
    
    // Get all focusable elements
    const focusableElements = modalRef.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    // Focus first element
    firstElement?.focus();
    
    // Handle tab key for focus trap
    const handleTab = (e) => {
      if (e.key !== 'Tab') return;
      
      if (e.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };
    
    document.addEventListener('keydown', handleTab);
    
    // Cleanup: restore focus to previous element
    return () => {
      document.removeEventListener('keydown', handleTab);
      previousActiveElement.current?.focus();
    };
  }, [isOpen]);
  
  // Handle backdrop click
  const handleBackdropClick = (e) => {
    if (closeOnBackdrop && e.target === e.currentTarget) {
      onClose();
    }
  };
  
  if (!isOpen) return null;
  
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50 animate-fade-in"
      onClick={handleBackdropClick}
      role="presentation"
    >
      <div
        ref={modalRef}
        className={`bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto ${className}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? 'modal-title' : undefined}
        {...props}
      >
        <div className="p-6">
          {/* Header with close button */}
          <div className="flex items-start justify-between mb-4">
            {title && (
              <h2 
                id="modal-title"
                className="text-xl font-bold text-gray-900"
              >
                {title}
              </h2>
            )}
            <button
              onClick={onClose}
              className="ml-auto text-gray-400 hover:text-gray-600 transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500 rounded"
              aria-label="Close modal"
            >
              <svg 
                className="w-6 h-6" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M6 18L18 6M6 6l12 12" 
                />
              </svg>
            </button>
          </div>
          
          {/* Modal content */}
          <div>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Modal;
