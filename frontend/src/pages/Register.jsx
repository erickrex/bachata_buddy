import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { validateRegistrationForm, getPasswordStrength } from '../utils/validation';
import Button from '../components/common/Button';
import Input from '../components/common/Input';

function Register() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const { addToast } = useToast();
  
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [serverError, setServerError] = useState('');

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
    // Clear server error when user makes changes
    if (serverError) {
      setServerError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate form
    const validation = validateRegistrationForm(formData);
    if (!validation.isValid) {
      setErrors(validation.errors);
      return;
    }
    
    setIsLoading(true);
    setServerError('');
    
    try {
      await register(formData.username, formData.email, formData.password);
      
      // Show success toast
      addToast('Account created successfully! Welcome to Bachata Buddy!', 'success');
      
      // Auto-login successful, redirect to home page
      navigate('/');
    } catch (error) {
      console.error('Registration failed:', error);
      
      // Parse error message for specific field errors
      const errorMessage = error.message || 'Registration failed. Please try again.';
      
      // Check if error message contains field-specific errors
      if (errorMessage.toLowerCase().includes('username')) {
        setErrors(prev => ({ ...prev, username: errorMessage }));
      } else if (errorMessage.toLowerCase().includes('email')) {
        setErrors(prev => ({ ...prev, email: errorMessage }));
      } else {
        setServerError(errorMessage);
      }
      
      addToast('Registration failed. Please check your information.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Get password strength for display
  const passwordStrength = getPasswordStrength(formData.password);
  
  // Color mapping for password strength indicator
  const strengthColors = {
    red: 'bg-red-500',
    orange: 'bg-orange-500',
    yellow: 'bg-yellow-500',
    lime: 'bg-lime-500',
    green: 'bg-green-500',
    emerald: 'bg-emerald-500',
    gray: 'bg-gray-300'
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center bg-gray-50 px-4 py-12">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900">Create Account</h1>
          <p className="mt-2 text-gray-600">
            Join Bachata Buddy and start creating choreographies
          </p>
        </div>

        {/* Registration Form */}
        <div className="bg-white rounded-lg shadow-md p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Server Error Message */}
            {serverError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-sm text-red-800">{serverError}</p>
              </div>
            )}

            {/* Username Input */}
            <Input
              label="Username"
              type="text"
              value={formData.username}
              onChange={(value) => handleChange('username', value)}
              error={errors.username}
              placeholder="Choose a username"
              required
              disabled={isLoading}
              autoComplete="username"
            />

            {/* Email Input */}
            <Input
              label="Email"
              type="email"
              value={formData.email}
              onChange={(value) => handleChange('email', value)}
              error={errors.email}
              placeholder="Enter your email"
              required
              disabled={isLoading}
              autoComplete="email"
            />

            {/* Password Input */}
            <div>
              <Input
                label="Password"
                type="password"
                value={formData.password}
                onChange={(value) => handleChange('password', value)}
                error={errors.password}
                placeholder="Create a password"
                required
                disabled={isLoading}
                autoComplete="new-password"
              />
              
              {/* Password Strength Indicator */}
              {formData.password && (
                <div className="mt-2">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-600">Password Strength:</span>
                    <span className={`text-xs font-medium text-${passwordStrength.color}-600`}>
                      {passwordStrength.label}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full transition-all duration-300 ${strengthColors[passwordStrength.color]}`}
                      style={{ width: `${(passwordStrength.strength / 5) * 100}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Use 8+ characters with a mix of letters, numbers & symbols
                  </p>
                </div>
              )}
            </div>

            {/* Confirm Password Input */}
            <Input
              label="Confirm Password"
              type="password"
              value={formData.confirmPassword}
              onChange={(value) => handleChange('confirmPassword', value)}
              error={errors.confirmPassword}
              placeholder="Confirm your password"
              required
              disabled={isLoading}
              autoComplete="new-password"
            />

            {/* Submit Button */}
            <Button
              type="submit"
              disabled={isLoading}
              className="w-full"
            >
              {isLoading ? 'Creating Account...' : 'Create Account'}
            </Button>
          </form>

          {/* Login Link */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Already have an account?{' '}
              <Link 
                to="/login" 
                className="font-medium text-purple-600 hover:text-purple-500"
              >
                Sign in here
              </Link>
            </p>
          </div>
        </div>

        {/* Additional Info */}
        <p className="text-center text-xs text-gray-500">
          By creating an account, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>
    </div>
  );
}

export default Register;
