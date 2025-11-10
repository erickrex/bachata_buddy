// Card Component
// Reusable card container with shadow and border

function Card({ 
  children, 
  className = '', 
  hover = false,
  onClick,
  ...props 
}) {
  const baseClasses = 'bg-white rounded-xl shadow-sm border border-gray-200';
  const hoverClasses = hover ? 'hover:shadow-lg transition-shadow duration-200 cursor-pointer' : '';
  const clickableClasses = onClick ? 'cursor-pointer' : '';
  
  const classes = `${baseClasses} ${hoverClasses} ${clickableClasses} ${className}`.trim();
  
  return (
    <div 
      className={classes}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick(e);
        }
      } : undefined}
      {...props}
    >
      {children}
    </div>
  );
}

export default Card;
