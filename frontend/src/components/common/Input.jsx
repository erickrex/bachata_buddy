// Input Component
// Reusable text input with label and error handling
// 
// XSS Protection: React automatically escapes all values rendered in JSX,
// preventing XSS attacks. The 'value' prop is safely escaped by React.
// Additional validation is performed in validation.js utilities.

function Input({ 
  label, 
  type = 'text', 
  value, 
  onChange, 
  error = null,
  placeholder = '',
  required = false,
  disabled = false,
  className = '',
  id,
  ...props 
}) {
  const inputId = id || `input-${label?.toLowerCase().replace(/\s+/g, '-')}`;
  
  const inputClasses = `
    w-full px-4 py-2 border rounded-lg min-h-[44px]
    focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent
    disabled:bg-gray-100 disabled:cursor-not-allowed
    ${error ? 'border-red-500' : 'border-gray-300'}
    ${className}
  `.trim();
  
  return (
    <div className="w-full">
      {label && (
        <label 
          htmlFor={inputId}
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      
      <input
        id={inputId}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        className={inputClasses}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? `${inputId}-error` : undefined}
        {...props}
      />
      
      {error && (
        <p 
          id={`${inputId}-error`}
          className="mt-1 text-sm text-red-600"
          role="alert"
        >
          {error}
        </p>
      )}
    </div>
  );
}

export default Input;
