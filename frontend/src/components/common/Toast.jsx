import React from 'react';

const typeStyles = {
  success: 'bg-green-500 text-white',
  error: 'bg-red-500 text-white',
  warning: 'bg-yellow-500 text-white',
  info: 'bg-blue-500 text-white'
};

const typeIcons = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ'
};

const Toast = ({ message, type = 'info', onClose }) => {
  return (
    <div 
      className={`
        ${typeStyles[type]}
        px-4 py-3 rounded-lg shadow-lg
        flex items-center gap-3
        animate-slide-in
        min-w-[300px] max-w-md
      `}
      role="alert"
      aria-live="polite"
    >
      <span className="text-xl" aria-hidden="true">
        {typeIcons[type]}
      </span>
      <p className="flex-1 text-sm font-medium">
        {message}
      </p>
      <button
        onClick={onClose}
        className="text-white hover:opacity-75 transition-opacity focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-transparent rounded"
        aria-label="Close notification"
      >
        ✕
      </button>
    </div>
  );
};

export default Toast;
