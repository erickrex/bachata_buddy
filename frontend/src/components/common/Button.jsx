// Button Component
// Reusable button with variants and sizes

const variantStyles = {
  primary: 'bg-purple-600 hover:bg-purple-700 text-white',
  secondary: 'bg-gray-200 hover:bg-gray-300 text-gray-800',
  danger: 'bg-red-600 hover:bg-red-700 text-white',
  ghost: 'bg-transparent hover:bg-gray-100 text-gray-700'
};

const sizeStyles = {
  sm: 'px-3 py-1.5 text-sm min-h-[44px]',
  md: 'px-4 py-2 text-base min-h-[44px]',
  lg: 'px-6 py-3 text-lg min-h-[48px]'
};

function Button({ 
  children, 
  variant = 'primary', 
  size = 'md', 
  disabled = false,
  type = 'button',
  className = '',
  onClick,
  ...props 
}) {
  const baseStyles = 'rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';
  
  const classes = `${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`;
  
  return (
    <button
      type={type}
      className={classes}
      disabled={disabled}
      onClick={onClick}
      {...props}
    >
      {children}
    </button>
  );
}

export default Button;
