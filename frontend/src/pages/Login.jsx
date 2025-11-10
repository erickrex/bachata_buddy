import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { validateLoginForm } from '../utils/validation';
import Button from '../components/common/Button';
import Input from '../components/common/Input';

function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const { addToast } = useToast();
  
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [rememberMe, setRememberMe] = useState(false);
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
    const validation = validateLoginForm(formData);
    if (!validation.isValid) {
      setErrors(validation.errors);
      return;
    }
    
    setIsLoading(true);
    setServerError('');
    
    try {
      await login(formData.username, formData.password);
      
      // Store remember me preference if needed
      if (rememberMe) {
        localStorage.setItem('rememberMe', 'true');
      }
      
      // Show success toast
      addToast('Welcome back! Login successful.', 'success');
      
      // Redirect to home page on successful login
      navigate('/');
    } catch (error) {
      console.error('Login failed:', error);
      setServerError(error.message || 'Login failed. Please check your credentials and try again.');
      addToast('Login failed. Please check your credentials.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center bg-gray-50 px-4 py-12">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900">Welcome Back</h1>
          <p className="mt-2 text-gray-600">
            Sign in to your Bachata Buddy account
          </p>
        </div>

        {/* Login Form */}
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
              placeholder="Enter your username"
              required
              disabled={isLoading}
              autoComplete="username"
            />

            {/* Password Input */}
            <Input
              label="Password"
              type="password"
              value={formData.password}
              onChange={(value) => handleChange('password', value)}
              error={errors.password}
              placeholder="Enter your password"
              required
              disabled={isLoading}
              autoComplete="current-password"
            />

            {/* Remember Me Checkbox */}
            <div className="flex items-center">
              <input
                id="remember-me"
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                disabled={isLoading}
                className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
              />
              <label 
                htmlFor="remember-me" 
                className="ml-2 block text-sm text-gray-700"
              >
                Remember me
              </label>
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              disabled={isLoading}
              className="w-full"
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>

          {/* Registration Link */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Don't have an account?{' '}
              <Link 
                to="/register" 
                className="font-medium text-purple-600 hover:text-purple-500"
              >
                Sign up here
              </Link>
            </p>
          </div>
        </div>

        {/* Additional Info */}
        <p className="text-center text-xs text-gray-500">
          By signing in, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>
    </div>
  );
}

export default Login;
