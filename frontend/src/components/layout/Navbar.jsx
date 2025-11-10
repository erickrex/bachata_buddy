import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';

function Navbar() {
  const { isAuthenticated, user, logout } = useAuth();
  const { addToast } = useToast();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isGenerateDropdownOpen, setIsGenerateDropdownOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  // Helper to check if a path is active
  const isActive = (path) => location.pathname === path;

  // Get user initials for avatar
  const getUserInitials = () => {
    if (!user?.username) return '?';
    return user.username.charAt(0).toUpperCase();
  };

  const handleLogout = () => {
    logout();
    addToast('You have been logged out successfully', 'info');
    setIsUserMenuOpen(false);
    setIsMobileMenuOpen(false);
  };

  return (
    <nav className="sticky top-0 z-50 bg-white shadow-sm">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="text-xl font-bold text-primary-600 hover:text-primary-700 transition-colors">
            🎵 Bachata Buddy
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center gap-6">
            {isAuthenticated ? (
              <>
                {/* Generate Dropdown */}
                <div className="relative">
                  <button
                    onClick={() => setIsGenerateDropdownOpen(!isGenerateDropdownOpen)}
                    onBlur={() => setTimeout(() => setIsGenerateDropdownOpen(false), 200)}
                    className={`flex items-center gap-1 px-3 py-2 rounded-lg transition-colors ${
                      isActive('/select-song') || isActive('/describe-choreo')
                        ? 'text-primary-600 bg-primary-50'
                        : 'text-gray-700 hover:text-primary-600 hover:bg-gray-50'
                    }`}
                  >
                    Generate
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  
                  {isGenerateDropdownOpen && (
                    <div className="absolute top-full left-0 mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1">
                      <Link
                        to="/select-song"
                        className="block px-4 py-2 text-gray-700 hover:bg-primary-50 hover:text-primary-600 transition-colors"
                        onClick={() => setIsGenerateDropdownOpen(false)}
                      >
                        🎵 Select Song
                      </Link>
                      <Link
                        to="/describe-choreo"
                        className="block px-4 py-2 text-gray-700 hover:bg-primary-50 hover:text-primary-600 transition-colors"
                        onClick={() => setIsGenerateDropdownOpen(false)}
                      >
                        ✨ Describe Choreo
                      </Link>
                    </div>
                  )}
                </div>

                {/* My Collections */}
                <Link
                  to="/collections"
                  className={`px-3 py-2 rounded-lg transition-colors ${
                    isActive('/collections')
                      ? 'text-primary-600 bg-primary-50'
                      : 'text-gray-700 hover:text-primary-600 hover:bg-gray-50'
                  }`}
                >
                  My Collections
                </Link>

                {/* User Menu */}
                <div className="relative">
                  <button
                    onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                    onBlur={() => setTimeout(() => setIsUserMenuOpen(false), 200)}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors"
                    aria-label="User menu"
                  >
                    <div className="w-8 h-8 rounded-full bg-gradient-to-r from-primary-500 to-secondary-500 flex items-center justify-center text-white font-semibold">
                      {getUserInitials()}
                    </div>
                    <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>

                  {isUserMenuOpen && (
                    <div className="absolute top-full right-0 mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1">
                      <div className="px-4 py-2 border-b border-gray-200">
                        <p className="text-sm font-semibold text-gray-900">{user?.username}</p>
                        <p className="text-xs text-gray-500">{user?.email}</p>
                      </div>
                      <Link
                        to="/profile"
                        className="block px-4 py-2 text-gray-700 hover:bg-primary-50 hover:text-primary-600 transition-colors"
                        onClick={() => setIsUserMenuOpen(false)}
                      >
                        👤 Profile
                      </Link>
                      <Link
                        to="/preferences"
                        className="block px-4 py-2 text-gray-700 hover:bg-primary-50 hover:text-primary-600 transition-colors"
                        onClick={() => setIsUserMenuOpen(false)}
                      >
                        ⚙️ Preferences
                      </Link>
                      <button
                        onClick={handleLogout}
                        className="w-full text-left px-4 py-2 text-gray-700 hover:bg-red-50 hover:text-red-600 transition-colors"
                      >
                        🚪 Logout
                      </button>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <>
                {/* Login/Sign Up for anonymous users */}
                <Link
                  to="/login"
                  className="text-gray-700 hover:text-primary-600 transition-colors"
                >
                  Login
                </Link>
                <Link
                  to="/register"
                  className="bg-gradient-to-r from-primary-500 to-secondary-500 text-white px-4 py-2 rounded-lg hover:from-primary-600 hover:to-secondary-600 transition-all"
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>

          {/* Mobile Menu Button - 44x44px touch target */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="lg:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="Toggle mobile menu"
            aria-expanded={isMobileMenuOpen}
          >
            {isMobileMenuOpen ? (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>

        {/* Mobile Menu with slide-in animation */}
        <div
          className={`lg:hidden overflow-hidden transition-all duration-300 ease-in-out ${
            isMobileMenuOpen ? 'max-h-screen opacity-100' : 'max-h-0 opacity-0'
          }`}
        >
          <div className="border-t border-gray-200 py-4 space-y-2">
            {isAuthenticated ? (
              <>
                {/* User Info */}
                <div className="px-4 py-2 border-b border-gray-200 mb-2">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-r from-primary-500 to-secondary-500 flex items-center justify-center text-white font-semibold">
                      {getUserInitials()}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-900">{user?.username}</p>
                      <p className="text-xs text-gray-500">{user?.email}</p>
                    </div>
                  </div>
                </div>

                {/* Generate Section */}
                <div className="px-4 py-2">
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Generate</p>
                  <Link
                    to="/select-song"
                    className={`block px-3 py-2 rounded-lg transition-colors min-h-[44px] flex items-center ${
                      isActive('/select-song')
                        ? 'text-primary-600 bg-primary-50'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    🎵 Select Song
                  </Link>
                  <Link
                    to="/describe-choreo"
                    className={`block px-3 py-2 rounded-lg transition-colors min-h-[44px] flex items-center ${
                      isActive('/describe-choreo')
                        ? 'text-primary-600 bg-primary-50'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    ✨ Describe Choreo
                  </Link>
                </div>

                {/* Main Navigation */}
                <Link
                  to="/collections"
                  className={`block px-4 py-2 rounded-lg transition-colors min-h-[44px] flex items-center ${
                    isActive('/collections')
                      ? 'text-primary-600 bg-primary-50'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  My Collections
                </Link>

                {/* User Menu */}
                <div className="border-t border-gray-200 mt-2 pt-2">
                  <Link
                    to="/profile"
                    className="block px-4 py-2 text-gray-700 hover:bg-gray-50 rounded-lg transition-colors min-h-[44px] flex items-center"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    👤 Profile
                  </Link>
                  <Link
                    to="/preferences"
                    className="block px-4 py-2 text-gray-700 hover:bg-gray-50 rounded-lg transition-colors min-h-[44px] flex items-center"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    ⚙️ Preferences
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors min-h-[44px] flex items-center"
                  >
                    🚪 Logout
                  </button>
                </div>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="block px-4 py-2 text-gray-700 hover:bg-gray-50 rounded-lg transition-colors min-h-[44px] flex items-center"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Login
                </Link>
                <Link
                  to="/register"
                  className="block mx-4 px-4 py-2 bg-gradient-to-r from-primary-500 to-secondary-500 text-white text-center rounded-lg hover:from-primary-600 hover:to-secondary-600 transition-all min-h-[44px] flex items-center justify-center"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
