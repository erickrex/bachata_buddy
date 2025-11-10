// Select Component
// Reusable dropdown select with label and error handling

function Select({ 
  label, 
  value, 
  onChange, 
  options = [],
  error = null,
  required = false,
  disabled = false,
  placeholder = 'Select an option',
  className = '',
  id,
  ...props 
}) {
  const selectId = id || `select-${label?.toLowerCase().replace(/\s+/g, '-')}`;
  
  const selectClasses = `
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
          htmlFor={selectId}
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      
      <select
        id={selectId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        disabled={disabled}
        className={selectClasses}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? `${selectId}-error` : undefined}
        {...props}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option 
            key={option.value} 
            value={option.value}
          >
            {option.label}
          </option>
        ))}
      </select>
      
      {error && (
        <p 
          id={`${selectId}-error`}
          className="mt-1 text-sm text-red-600"
          role="alert"
        >
          {error}
        </p>
      )}
    </div>
  );
}

export default Select;
