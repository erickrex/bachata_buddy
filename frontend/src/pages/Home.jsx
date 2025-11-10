import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { api } from '../utils/api';
import Container from '../components/layout/Container';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import Spinner from '../components/common/Spinner';
import { formatDate, formatDuration } from '../utils/format';

function Home() {
  const { isAuthenticated, user } = useAuth();
  const [recentCollections, setRecentCollections] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Load recent collections for authenticated users
  useEffect(() => {
    if (isAuthenticated) {
      loadRecentCollections();
    }
  }, [isAuthenticated]);

  const loadRecentCollections = async () => {
    setIsLoading(true);
    try {
      const response = await api.collections.getAll({ page: 1, page_size: 3 });
      setRecentCollections(response.results || []);
    } catch (error) {
      console.error('Failed to load recent collections:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-purple-50 to-white">
      <Container className="py-12">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-4">
            Welcome to <span className="text-purple-600">Bachata Buddy</span> 💃🕺
          </h1>
          <p className="text-xl md:text-2xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Your AI-powered choreography generator for creating custom bachata dance routines
          </p>
          {isAuthenticated && user && (
            <p className="text-lg text-gray-700 mb-8">
              Hey <span className="font-semibold text-purple-600">{user.username}</span>! Ready to create something amazing?
            </p>
          )}
        </div>

        {/* Feature Highlights */}
        <div className="grid md:grid-cols-2 gap-8 mb-16">
          {/* Path 1: Select Song */}
          <Card className="p-8 hover:shadow-xl transition-shadow">
            <div className="text-center">
              <div className="text-6xl mb-4">🎵</div>
              <h2 className="text-2xl font-bold text-gray-900 mb-3">
                Select a Song
              </h2>
              <p className="text-gray-600 mb-6">
                Choose from our curated library of bachata songs and customize your choreography with difficulty, energy level, and style preferences.
              </p>
              <ul className="text-left text-gray-700 mb-6 space-y-2">
                <li className="flex items-start">
                  <span className="text-purple-600 mr-2">✓</span>
                  <span>Browse songs by genre, BPM, and artist</span>
                </li>
                <li className="flex items-start">
                  <span className="text-purple-600 mr-2">✓</span>
                  <span>Customize difficulty and style</span>
                </li>
                <li className="flex items-start">
                  <span className="text-purple-600 mr-2">✓</span>
                  <span>Perfect for specific music preferences</span>
                </li>
              </ul>
              <Link to="/select-song">
                <Button className="w-full">
                  🎵 Select a Song
                </Button>
              </Link>
            </div>
          </Card>

          {/* Path 2: Describe Choreography */}
          <Card className="p-8 hover:shadow-xl transition-shadow">
            <div className="text-center">
              <div className="text-6xl mb-4">✨</div>
              <h2 className="text-2xl font-bold text-gray-900 mb-3">
                Describe Your Vision
              </h2>
              <p className="text-gray-600 mb-6">
                Use natural language to describe your ideal choreography. Our AI will understand your vision and generate the perfect routine.
              </p>
              <ul className="text-left text-gray-700 mb-6 space-y-2">
                <li className="flex items-start">
                  <span className="text-purple-600 mr-2">✓</span>
                  <span>Describe in your own words</span>
                </li>
                <li className="flex items-start">
                  <span className="text-purple-600 mr-2">✓</span>
                  <span>AI-powered parameter extraction</span>
                </li>
                <li className="flex items-start">
                  <span className="text-purple-600 mr-2">✓</span>
                  <span>No technical knowledge required</span>
                </li>
              </ul>
              <Link to="/describe-choreo">
                <Button className="w-full">
                  ✨ Describe Choreography
                </Button>
              </Link>
            </div>
          </Card>
        </div>

        {/* Additional Features */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-16">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-8">
            What You'll Get
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="text-5xl mb-3">🎬</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Custom Video
              </h3>
              <p className="text-gray-600">
                High-quality choreography video generated specifically for your chosen song and preferences
              </p>
            </div>
            <div className="text-center">
              <div className="text-5xl mb-3">🔁</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Loop Controls
              </h3>
              <p className="text-gray-600">
                Practice specific sections with adjustable loop segments and playback speed controls
              </p>
            </div>
            <div className="text-center">
              <div className="text-5xl mb-3">💾</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Save & Organize
              </h3>
              <p className="text-gray-600">
                Build your personal collection of choreographies for easy access anytime
              </p>
            </div>
          </div>
        </div>

        {/* Recent Collections (Authenticated Users Only) */}
        {isAuthenticated && (
          <div className="mb-16">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-3xl font-bold text-gray-900">
                Your Recent Choreographies
              </h2>
              <Link to="/collections">
                <Button variant="secondary" size="sm">
                  View All →
                </Button>
              </Link>
            </div>

            {isLoading ? (
              <div className="flex justify-center py-12">
                <Spinner size="lg" />
              </div>
            ) : recentCollections.length > 0 ? (
              <div className="grid md:grid-cols-3 gap-6">
                {recentCollections.map((collection) => (
                  <Link key={collection.id} to={`/video/${collection.task_id}`}>
                    <Card hover className="p-6">
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        🎬 {collection.title}
                      </h3>
                      <p className="text-sm text-gray-600 mb-3">
                        {formatDate(collection.created_at)}
                      </p>
                      <div className="flex items-center justify-between text-sm text-gray-700">
                        <span className="capitalize">{collection.difficulty}</span>
                        <span>{formatDuration(collection.duration)}</span>
                      </div>
                      {collection.song_title && (
                        <p className="text-sm text-gray-500 mt-2">
                          🎵 {collection.song_title}
                        </p>
                      )}
                    </Card>
                  </Link>
                ))}
              </div>
            ) : (
              <Card className="p-12 text-center">
                <div className="text-6xl mb-4">🎭</div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  No Choreographies Yet
                </h3>
                <p className="text-gray-600 mb-6">
                  Start creating your first choreography to see it here!
                </p>
                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                  <Link to="/select-song" className="w-full sm:w-auto">
                    <Button className="w-full">Select a Song</Button>
                  </Link>
                  <Link to="/describe-choreo" className="w-full sm:w-auto">
                    <Button variant="secondary" className="w-full">Describe Choreography</Button>
                  </Link>
                </div>
              </Card>
            )}
          </div>
        )}

        {/* Call to Action for Non-Authenticated Users */}
        {!isAuthenticated && (
          <div className="bg-gradient-to-r from-purple-600 to-pink-600 rounded-2xl shadow-xl p-12 text-center text-white">
            <h2 className="text-3xl font-bold mb-4">
              Ready to Start Dancing?
            </h2>
            <p className="text-xl mb-8 opacity-90">
              Sign up now to save your choreographies and build your personal collection
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/register" className="w-full sm:w-auto">
                <Button className="bg-white text-purple-600 hover:bg-gray-100 w-full">
                  Sign Up Free
                </Button>
              </Link>
              <Link to="/login" className="w-full sm:w-auto">
                <Button variant="secondary" className="border-white text-white hover:bg-white hover:text-purple-600 w-full">
                  Log In
                </Button>
              </Link>
            </div>
          </div>
        )}
      </Container>
    </div>
  );
}

export default Home;
