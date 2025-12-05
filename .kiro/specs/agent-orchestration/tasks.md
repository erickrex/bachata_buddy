# Implementation Plan: Agent Orchestration with OpenAI Function Calling

## Overview

This implementation plan covers the complete rework of Path 2 ("Describe Choreography") using OpenAI function calling for agent orchestration. The plan is structured to build incrementally, with each task building on previous work.

## Task List

- [x] 1. Set up project dependencies and configuration
  - Set up pyproject.toml with OpenAI SDK
  - Configure environment variables for OpenAI API key
  - Add UV package manager configuration
  - _Requirements: 7.5_

- [x] 1.1 Initialize pyproject.toml with dependencies
  - Create or update pyproject.toml in backend directory
  - Add openai>=1.0.0 dependency
  - Configure UV tool settings
  - _Requirements: 7.5_

- [x] 1.2 Add OpenAI API key configuration
  - Add OPENAI_API_KEY to .env.example
  - Update Django settings to load OpenAI API key
  - Add validation for missing API key at startup
  - _Requirements: 7.5_

- [x] 2. Implement Parameter Extractor service
  - Create ParameterExtractor class with OpenAI integration
  - Implement parameter extraction with JSON mode
  - Add keyword-based fallback extraction
  - Add parameter validation
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 7.1, 7.2, 7.3, 7.4_

- [x] 2.1 Create ParameterExtractor class
  - Create bachata_buddy/backend/services/parameter_extractor.py
  - Initialize OpenAI client in constructor
  - Define extraction prompt template
  - _Requirements: 1.1, 7.1_

- [x] 2.2 Implement OpenAI parameter extraction
  - Implement extract_parameters() method using GPT-4o-mini
  - Use JSON mode for structured output
  - Parse and validate OpenAI response
  - _Requirements: 1.1, 7.1, 7.2_

- [x] 2.3 Add keyword-based fallback extraction
  - Implement _fallback_keyword_extraction() method
  - Use regex/keyword matching for parameters
  - Apply default values for missing parameters
  - _Requirements: 1.2, 1.3, 7.4_

- [x] 2.4 Implement parameter validation
  - Implement _validate_parameters() method
  - Validate difficulty, energy_level, style against allowed values
  - Apply defaults for invalid values
  - _Requirements: 1.4, 7.3_

- [x] 2.5 Write property test for parameter extraction
  - **Property 1: Parameter extraction completeness**
  - **Validates: Requirements 1.1, 1.4**
  - Generate random natural language requests
  - Verify all required keys present in output
  - Verify values are from allowed lists

- [x] 2.6 Write property test for default parameter application
  - **Property 2: Default parameter application**
  - **Validates: Requirements 1.2**
  - Generate incomplete/ambiguous requests
  - Verify defaults are applied correctly
  - Verify output is always complete and valid

- [x] 2.7 Write property test for parameter validation
  - **Property 5: Parameter validation**
  - **Validates: Requirements 7.3**
  - Generate random parameter dictionaries
  - Verify validation catches invalid values
  - Verify valid values pass through unchanged

- [x] 3. Implement Agent Service with OpenAI function calling
  - Create AgentService class with OpenAI client
  - Define tool/function schemas for choreography services
  - Implement function execution dispatcher
  - Implement orchestration loop with function calling
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 3.1 Create AgentService class structure
  - Create bachata_buddy/backend/services/agent_service.py
  - Initialize with OpenAI client and service dependencies
  - Define class attributes for task tracking
  - _Requirements: 6.1_

- [x] 3.2 Define OpenAI function/tool schemas
  - Implement _define_tools() method
  - Define analyze_music tool schema
  - Define search_moves tool schema
  - Define generate_blueprint tool schema
  - Define assemble_video tool schema
  - _Requirements: 2.2, 6.2_

- [x] 3.3 Implement function execution dispatcher
  - Implement _execute_function() method
  - Route function calls to appropriate service methods
  - Handle function arguments parsing
  - Return structured results to OpenAI
  - _Requirements: 2.3, 6.3_

- [x] 3.4 Implement service wrapper functions
  - Implement _analyze_music() wrapper
  - Implement _search_moves() wrapper
  - Implement _generate_blueprint() wrapper
  - Implement _assemble_video() wrapper
  - Update task status after each function call
  - _Requirements: 2.3, 6.4_

- [x] 3.5 Implement OpenAI orchestration loop
  - Implement create_workflow() method
  - Initialize conversation with system prompt
  - Implement function calling loop
  - Handle tool_calls from OpenAI responses
  - Add function results back to conversation
  - Detect workflow completion
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 6.2, 6.3, 6.5_

- [x] 3.6 Add error handling and logging
  - Wrap function execution in try/catch
  - Log all function calls and results
  - Update task status on errors
  - Handle OpenAI API errors gracefully
  - _Requirements: 2.5_

- [x] 3.7 Write property test for workflow data flow
  - **Property 4: Workflow data flow**
  - **Validates: Requirements 2.4**
  - Mock OpenAI to request specific function sequence
  - Verify each function receives outputs from previous
  - Verify data continuity throughout workflow

- [x] 3.8 Write property test for workflow state persistence
  - **Property 7: Workflow state persistence**
  - **Validates: Requirements 6.3**
  - Execute workflow with random data
  - Verify conversation state maintained across function calls
  - Verify data added in one step available to subsequent steps

- [x] 4. Implement task status tracking
  - Add _update_task_status() method to AgentService
  - Update ChoreographyTask on each function call
  - Store function call details in message field
  - Track progress percentage
  - _Requirements: 3.2, 3.4, 8.1, 8.2, 8.4, 9.1, 9.2_

- [x] 4.1 Implement task status update method
  - Create _update_task_status() in AgentService
  - Update task.stage, task.message, task.progress
  - Save to database
  - _Requirements: 8.1, 8.4, 9.1, 9.2_

- [x] 4.2 Add progress calculation
  - Implement _calculate_progress() helper
  - Map function names to progress percentages
  - Return appropriate progress for each stage
  - _Requirements: 3.2, 8.2_

- [x] 4.3 Write property test for task status updates
  - **Property 6: Task status updates**
  - **Validates: Requirements 3.2, 8.1, 8.4, 9.1, 9.2**
  - Execute workflow steps
  - Verify task record updated after each step
  - Verify stage, message, and progress fields populated

- [x] 5. Create Django API endpoint for Path 2
  - Add POST /api/choreography/describe endpoint
  - Create DescribeChoreographySerializer
  - Initialize and execute AgentService
  - Return task_id and poll_url
  - _Requirements: 4.2, 10.2_

- [x] 5.1 Create serializer for describe endpoint
  - Create DescribeChoreographySerializer
  - Add user_request field with validation
  - Validate min/max length
  - Sanitize input
  - _Requirements: 4.2_

- [x] 5.2 Implement describe_choreography view
  - Add describe_choreography() view function
  - Require authentication
  - Create ChoreographyTask record
  - Initialize AgentService
  - Execute workflow asynchronously
  - Return 202 with task_id
  - _Requirements: 4.2, 10.2_

- [x] 5.3 Add URL routing for new endpoint
  - Add URL pattern for /api/choreography/describe
  - Update API documentation
  - _Requirements: 4.2_

- [x] 5.4 Write property test for Path 1 agent bypass
  - **Property 8: Path 1 agent bypass**
  - **Validates: Requirements 5.2, 5.3**
  - Submit requests via Path 1 endpoint
  - Verify AgentService is NOT invoked
  - Verify existing workflow executes unchanged

- [x] 6. Implement service initialization and dependency injection
  - Create get_agent_service() factory function
  - Initialize all service dependencies
  - Configure singleton pattern
  - _Requirements: 6.1_

- [x] 6.1 Create agent service factory
  - Implement get_agent_service() in services/__init__.py
  - Initialize ParameterExtractor
  - Initialize existing services (MusicAnalyzer, VectorSearch, etc.)
  - Create AgentService with all dependencies
  - Use singleton pattern
  - _Requirements: 6.1_

- [x] 6.2 Add agent service configuration
  - Add AGENT_ENABLED feature flag to settings
  - Add AGENT_TIMEOUT configuration
  - Validate OpenAI API key at startup
  - _Requirements: 6.1, 7.5_

- [x] 7. Checkpoint - Backend integration testing
  - Ensure all tests pass, ask the user if questions arise

- [x] 8. Implement Chat Interface (Frontend)
  - Create Chat Interface component
  - Add message display
  - Add input field with submit
  - Integrate with API endpoint
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 8.1 Create ChatMessages component
  - Create frontend/src/components/agent/ChatMessages.jsx
  - Display user and assistant messages
  - Style message bubbles
  - Auto-scroll to latest message
  - _Requirements: 4.3, 4.5_

- [x] 8.2 Create ChatInput component
  - Create frontend/src/components/agent/ChatInput.jsx
  - Add textarea for user input
  - Add submit button
  - Disable during generation
  - Handle Enter key submission
  - _Requirements: 4.2_

- [x] 8.3 Update DescribeChoreo page with Chat Interface
  - Update frontend/src/pages/DescribeChoreo.jsx
  - Add ChatMessages and ChatInput components
  - Implement message state management
  - Add example prompts
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 8.4 Integrate with describe API endpoint
  - Implement handleSubmit() to call /api/choreography/describe
  - Store task_id from response
  - Add user message to chat
  - Start polling for status
  - _Requirements: 4.2, 4.3_

- [x] 9. Implement Reasoning Panel (Frontend)
  - Create ReasoningPanel component
  - Display agent function calls in real-time
  - Show progress indicators
  - Style with icons for each function
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 9.1 Create ReasoningPanel component
  - Create frontend/src/components/agent/ReasoningPanel.jsx
  - Display current agent status
  - Show function call history
  - Add progress bar
  - _Requirements: 3.2, 3.3, 3.4, 3.5_

- [x] 9.2 Create ReasoningStep component
  - Create frontend/src/components/agent/ReasoningStep.jsx
  - Display step icon based on function name
  - Show step message
  - Add timestamp
  - Style completed vs in-progress steps
  - _Requirements: 3.3, 3.4_

- [x] 9.3 Integrate ReasoningPanel with polling
  - Add ReasoningPanel to DescribeChoreo page
  - Update panel when task status changes
  - Display function calls from task.message
  - Show progress from task.progress
  - _Requirements: 3.1, 3.2, 3.5_

- [x] 10. Implement HTTP polling for status updates
  - Use existing polling mechanism
  - Poll every 2 seconds during generation
  - Update chat and reasoning panel
  - Display video when complete
  - _Requirements: 8.2, 8.3, 8.5_

- [x] 10.1 Add usePolling hook integration
  - Use existing usePolling hook
  - Poll /api/choreography/tasks/{task_id}
  - Poll every 2 seconds while generating
  - Stop polling when complete or failed
  - _Requirements: 8.2, 8.5_

- [x] 10.2 Update UI on status changes
  - Add assistant messages to chat from task.message
  - Update reasoning panel with new steps
  - Show video player when task.status === 'completed'
  - Show error message if task.status === 'failed'
  - _Requirements: 8.3, 8.4_

- [x] 11. Add example prompts to Chat Interface
  - Create example prompt suggestions
  - Display prominently on empty chat
  - Populate input on click
  - _Requirements: 4.1_

- [x] 11.1 Create example prompts data
  - Define 3-5 example prompts
  - Include variety of difficulty/style combinations
  - Make prompts conversational and natural
  - _Requirements: 4.1_

- [x] 11.2 Display example prompts
  - Show examples when chat is empty
  - Style as clickable cards
  - Populate input field on click
  - Hide after first message
  - _Requirements: 4.1_

- [x] 12. Checkpoint - Frontend integration testing
  - Ensure all tests pass, ask the user if questions arise

- [x] 13. End-to-end integration and testing
  - Test complete workflow from chat to video
  - Verify reasoning display updates
  - Test error handling
  - Verify Path 1 still works
  - _Requirements: All_

- [x] 13.1 Test happy path workflow
  - Submit natural language request
  - Verify parameter extraction
  - Verify function calls execute in order
  - Verify reasoning panel updates
  - Verify video displays on completion
  - _Requirements: All_

- [x] 13.2 Test error scenarios
  - Test with invalid OpenAI API key
  - Test with service failures
  - Test with malformed user input
  - Verify error messages display correctly
  - _Requirements: 2.5, 7.4_

- [x] 13.3 Verify Path 1 unchanged
  - Run existing Path 1 tests
  - Manually test Path 1 workflow
  - Verify no regressions
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 14. Documentation and deployment preparation
  - Update README with OpenAI setup instructions
  - Document environment variables
  - Add API documentation for new endpoint
  - Create deployment checklist

- [x] 14.1 Update documentation
  - Add OpenAI API key setup to README
  - Document new /api/choreography/describe endpoint
  - Add example requests and responses
  - Document function calling architecture

- [x] 14.2 Create deployment checklist
  - List required environment variables
  - Document database migration steps (if any)
  - Add monitoring recommendations
  - Create rollback plan

- [x] 15. Final checkpoint - Production readiness
  - Ensure all tests pass, ask the user if questions arise
  - Verify all documentation complete
  - Confirm deployment checklist ready

## Notes

- All Python code must use `uv run` for execution
- All dependencies must be in pyproject.toml
- OpenAI function calling is the core orchestration mechanism
- No MCP servers should be implemented in the project
- Path 1 must remain completely unchanged
- Use existing HTTP polling (no WebSockets)
- All property tests are required for comprehensive correctness validation
