// ExamplePrompts Component
// Displays clickable example prompt cards to help users get started
// Shows when chat is empty, hides after first message

import { examplePrompts } from '../../data/examplePrompts';

function ExamplePrompts({ onSelectPrompt, disabled = false }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8">
      <div className="text-center mb-8">
        <div className="text-6xl mb-4">🤖</div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Start a Conversation
        </h2>
        <p className="text-gray-600 max-w-md">
          Tell me what kind of choreography you'd like to create. 
          I'll guide you through the process step by step.
        </p>
      </div>
      
      {/* Example Prompt Cards */}
      <div className="w-full max-w-2xl">
        <p className="text-sm font-medium text-gray-700 mb-3 text-center">
          💡 Try these examples:
        </p>
        <div className="space-y-2">
          {examplePrompts.map((prompt) => (
            <button
              key={prompt.id}
              onClick={() => onSelectPrompt(prompt.text)}
              disabled={disabled}
              className="
                w-full text-left px-4 py-3
                bg-gradient-to-r from-gray-50 to-white
                hover:from-purple-50 hover:to-pink-50
                border border-gray-200 hover:border-purple-300
                rounded-lg text-sm text-gray-700
                transition-all duration-200
                disabled:opacity-50 disabled:cursor-not-allowed
                focus:outline-none focus:ring-2 focus:ring-purple-500
                shadow-sm hover:shadow-md
                group
              "
              aria-label={`Use example prompt: ${prompt.text}`}
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl flex-shrink-0 group-hover:scale-110 transition-transform">
                  {prompt.icon}
                </span>
                <div className="flex-1">
                  <p className="text-gray-800 group-hover:text-purple-900">
                    "{prompt.text}"
                  </p>
                  <div className="flex gap-2 mt-1">
                    <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full">
                      {prompt.difficulty}
                    </span>
                    <span className="text-xs px-2 py-0.5 bg-pink-100 text-pink-700 rounded-full">
                      {prompt.style}
                    </span>
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default ExamplePrompts;
