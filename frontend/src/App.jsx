import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import { useAuth } from './hooks/useAuth';
import ErrorBoundary from './components/ErrorBoundary';

// Layout
import Navbar from './components/layout/Navbar';
import Footer from './components/layout/Footer';
import Spinner from './components/common/Spinner';

// Pages
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import SelectSong from './pages/SelectSong';
import DescribeChoreo from './pages/DescribeChoreo';
import Progress from './pages/Progress';
import VideoResult from './pages/VideoResult';
import Collections from './pages/Collections';
import Profile from './pages/Profile';
import Preferences from './pages/Preferences';

// Protected Route wrapper
function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner size="lg" />
      </div>
    );
  }
  
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <div className="min-h-screen flex flex-col">
              <Navbar />
              <main className="flex-1">
                <Routes>
                  {/* Public routes */}
                  <Route path="/" element={<Home />} />
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />
                  
                  {/* Protected routes */}
                  <Route 
                    path="/select-song" 
                    element={
                      <ProtectedRoute>
                        <SelectSong />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/describe-choreo" 
                    element={
                      <ProtectedRoute>
                        <DescribeChoreo />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/progress/:taskId" 
                    element={
                      <ProtectedRoute>
                        <Progress />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/video/:taskId" 
                    element={
                      <ProtectedRoute>
                        <VideoResult />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/collections" 
                    element={
                      <ProtectedRoute>
                        <Collections />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/profile" 
                    element={
                      <ProtectedRoute>
                        <Profile />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/preferences" 
                    element={
                      <ProtectedRoute>
                        <Preferences />
                      </ProtectedRoute>
                    } 
                  />
                  
                  {/* 404 - Redirect to home */}
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </main>
              <Footer />
            </div>
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
