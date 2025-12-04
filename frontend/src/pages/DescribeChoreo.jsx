// DescribeChoreo Page
// Natural language choreography description interface (Path 2)
// Chat-based interface with agent orchestration

import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Container from '../components/layout/Container';
import ChatMessages from '../components/agent/ChatMessages';
import ChatInput from '../components/agent/ChatInput';
import ReasoningPanel from '../components/agent/ReasoningPanel';
import VideoPlayer from '../components/video/VideoPlayer';
import ExamplePrompts from '../components/agent/ExamplePrompts';
import { api } from '../utils/api';
import { useToast } from '../hooks/useToast';
import { usePolling } from '../hooks/usePolling';

function DescribeChoreo() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [taskId, setTaskId] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [videoUrl, setVideoUrl] = useState(null);
  const lastMessageRef = useRef('');
  
  // Poll for task status updates every 2 seconds
  const { data: taskStatus } = usePolling(
    () => taskId ? api.tasks.getStatus(taskId) : null,
    2000,
    taskId && isGenerating
  );
  
  // Update messages when task status changes
  useEffect(() => {
    if (!taskStatus) return;
    
    // Update assistant message if it changed
    if (taskStatus.message && taskStatus.message !== lastMessageRef.current) {
      lastMessageRef.current = taskStatus.message;
      
      setMessages(prev => {
        // Check if last message is from assistant
        const lastMessage = prev[prev.length - 1];
        if (lastMessage && lastMessage.role === 'assistant') {
          // Update last assistant message
          return [
            ...prev.slice(0, -1),
            {
              role: 'assistant',
              content: taskStatus.message,
              timestamp: new Date().toISOString()
            }
          ];
        } else {
          // Add new assistant message
          return [
            ...prev,
            {
              role: 'assistant',
              content: taskStatus.message,
              timestamp: new Date().toISOString()
            }
          ];
        }
      });
    }
    
    // Check if task is complete
    if (taskStatus.status === 'completed' && isGenerating) {
      setIsGenerating(false);
      
      // Check if this is mock mode
      const isMockMode = taskStatus.result?.mock === true;
      
      if (isMockMode) {
        addToast('Blueprint generated! Run job container for actual video.', 'info');
      } else {
        addToast('Choreography generated successfully!', 'success');
      }
      
      // Extract video URL from result
      if (taskStatus.result && taskStatus.result.video_url) {
        setVideoUrl(taskStatus.result.video_url);
        
        // Add completion message
        const completionMessage = isMockMode 
          ? '✅ Blueprint generated! The video will be available after running the job container.'
          : '✅ Your choreography is ready!';
        
        setMessages(prev => [
          ...prev,
          {
            role: 'system',
            content: completionMessage,
            timestamp: new Date().toISOString()
          }
        ]);
      } else {
        // Fallback: navigate to video page if no URL in result
        setTimeout(() => {
          navigate(`/video/${taskId}`);
        }, 1500);
      }
    }
    
    // Check if task failed
    if (taskStatus.status === 'failed' && isGenerating) {
      setIsGenerating(false);
      const errorMsg = taskStatus.error || 'Generation failed';
      addToast(errorMsg, 'error');
      
      setMessages(prev => [
        ...prev,
        {
          role: 'system',
          content: `❌ Error: ${errorMsg}`,
          timestamp: new Date().toISOString()
        }
      ]);
    }
  }, [taskStatus, navigate, addToast, isGenerating]);
  
  // Handle message submission
  const handleSubmit = async () => {
    if (!input.trim() || isGenerating) return;
    
    const userMessage = input.trim();
    setInput('');
    
    // Add user message to chat
    setMessages(prev => [
      ...prev,
      {
        role: 'user',
        content: userMessage,
        timestamp: new Date().toISOString()
      }
    ]);
    
    setIsGenerating(true);
    
    try {
      // Call describe endpoint
      const response = await api.choreography.describe(userMessage);
      
      setTaskId(response.task_id);
      
      // Log task ID for easy access in development
      console.log('🎬 Task created! Run this command to generate video:');
      console.log(`   cd backend && uv run python run_local_job.py ${response.task_id}`);
      
      // Add initial assistant message
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: response.message || 'Starting choreography generation...',
          timestamp: new Date().toISOString()
        }
      ]);
      
      addToast('Generation started!', 'success');
      
    } catch (err) {
      setIsGenerating(false);
      const errorMessage = err.message || 'Failed to start generation';
      addToast(errorMessage, 'error');
      
      setMessages(prev => [
        ...prev,
        {
          role: 'system',
          content: `❌ Error: ${errorMessage}`,
          timestamp: new Date().toISOString()
        }
      ]);
    }
  };
  
  // Handle example prompt click
  const handleExampleClick = (promptText) => {
    setInput(promptText);
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50 py-12">
      <Container maxWidth="lg">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-3">
            💬 Chat with AI Choreographer
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Describe the choreography you want in natural language. 
            Our AI agent will understand your request and create a custom routine for you.
          </p>
        </div>
        
        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chat Interface - Takes 2 columns on large screens */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-2xl shadow-lg overflow-hidden" style={{ height: '600px' }}>
              <div className="flex flex-col h-full">
                {/* Messages Area */}
                {messages.length === 0 ? (
                  <ExamplePrompts 
                    onSelectPrompt={handleExampleClick}
                    disabled={isGenerating}
                  />
                ) : (
                  <ChatMessages messages={messages} />
                )}
                
                {/* Input Area */}
                <ChatInput
                  value={input}
                  onChange={setInput}
                  onSubmit={handleSubmit}
                  disabled={isGenerating}
                  placeholder="Describe the choreography you want to create..."
                />
              </div>
            </div>
          </div>
          
          {/* Reasoning Panel - Takes 1 column on large screens */}
          <div className="lg:col-span-1">
            <div style={{ position: 'sticky', top: '1.5rem' }}>
              <ReasoningPanel taskStatus={taskStatus} taskId={taskId} />
            </div>
          </div>
        </div>
        
        {/* Video Player Section */}
        {videoUrl && (
          <div className="mt-8">
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <span>🎬</span>
                <span>Your Choreography</span>
              </h2>
              <VideoPlayer 
                videoUrl={videoUrl} 
                taskId={taskId}
                onSave={() => navigate(`/video/${taskId}`)}
              />
            </div>
          </div>
        )}
        
        {/* Info Section */}
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-xl p-6">
          <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
            <span>💡</span>
            Tips for Better Results
          </h3>
          <ul className="space-y-2 text-sm text-blue-800">
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">•</span>
              <span>Mention the <strong>difficulty level</strong> (beginner, intermediate, or advanced)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">•</span>
              <span>Describe the <strong>style</strong> (romantic, energetic, sensual, playful, or modern)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">•</span>
              <span>Specify the <strong>energy level</strong> (low, medium, or high)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">•</span>
              <span>Watch the <strong>Agent Reasoning</strong> panel to see how the AI works</span>
            </li>
          </ul>
        </div>
      </Container>
    </div>
  );
}

export default DescribeChoreo;
