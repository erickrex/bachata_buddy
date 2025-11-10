/**
 * Container Component
 * 
 * A responsive container that centers content horizontally with max-width
 * and appropriate padding for different screen sizes.
 * 
 * @param {React.ReactNode} children - Content to be wrapped
 * @param {string} className - Additional CSS classes
 * @param {string} maxWidth - Maximum width variant (sm, md, lg, xl, 2xl, full)
 */
function Container({ children, className = '', maxWidth = 'xl' }) {
  const maxWidthClasses = {
    sm: 'max-w-screen-sm',   // 640px
    md: 'max-w-screen-md',   // 768px
    lg: 'max-w-screen-lg',   // 1024px
    xl: 'max-w-screen-xl',   // 1280px
    '2xl': 'max-w-screen-2xl', // 1536px
    full: 'max-w-full'
  };

  return (
    <div className={`
      ${maxWidthClasses[maxWidth] || maxWidthClasses.xl}
      mx-auto
      px-4 sm:px-6 lg:px-8
      ${className}
    `}>
      {children}
    </div>
  );
}

export default Container;
