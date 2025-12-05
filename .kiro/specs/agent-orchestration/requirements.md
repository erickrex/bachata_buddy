# Requirements Document: Agent Orchestration & Conversational Interface

## Introduction

This specification defines the complete rework of Path 2 ("Describe Choreography") in the Bachata Buddy application to include autonomous agent orchestration, conversational interface, and AI-powered parameter extraction. These features, proven successful in the Gradio MCP hackathon demo, will transform the natural language choreography generation workflow.

**Scope:**
- **Path 1 (Select Song)**: Remains unchanged - users select song and difficulty via forms
- **Path 2 (Describe Choreography)**: Complete rework with agent orchestration, natural language understanding, and reasoning display

The system will use OpenAI function calling for agent orchestration and OpenAI GPT-4o-mini for natural language understanding and parameter extraction.

## Glossary

- **Agent Service**: A backend service component that uses OpenAI function calling to orchestrate multi-step choreography generation workflows
- **Function Calling**: OpenAI's feature that allows the LLM to intelligently decide which functions/tools to call to accomplish a task
- **Tool/Function**: A Python function exposed to OpenAI that can be called during agent execution (e.g., analyze_music, search_moves)
- **Path 1**: The "Select Song" workflow where users choose from pre-defined songs and set difficulty via forms
- **Path 2**: The "Describe Choreography" workflow where users describe requirements in natural language
- **Parameter Extractor**: A component that uses OpenAI GPT-4o-mini to extract structured parameters from free-form text
- **Reasoning Panel**: A UI component that displays real-time agent decision-making steps and function calls
- **Backend API**: Django REST API that orchestrates choreography generation
- **Frontend Application**: React SPA that provides the user interface
- **Blueprint**: A structured JSON document specifying choreography sequence and timing
- **Choreography Task**: A database record representing an asynchronous choreography generation job
- **Chat Interface**: A conversational UI component for natural language interaction
- **HTTP Polling**: A technique where the Frontend Application periodically requests status updates from the Backend API

## Requirements

### Requirement 1: Natural Language Parameter Extraction

**User Story:** As a user, I want to describe my choreography needs in natural language, so that I don't have to fill out multiple form fields.

#### Acceptance Criteria

1. WHEN the Backend API receives free-form text describing choreography requirements THEN the Parameter Extractor SHALL extract structured parameters including difficulty, energy_level, style, and duration
2. WHEN the Parameter Extractor encounters ambiguous or incomplete text THEN the Parameter Extractor SHALL apply default values based on detected context
3. WHEN the Parameter Extractor encounters an extraction error THEN the Parameter Extractor SHALL execute keyword-based extraction as fallback
4. WHEN the Parameter Extractor produces extracted parameters THEN the Parameter Extractor SHALL validate each parameter against allowed option values
5. WHEN parameter extraction completes THEN the Backend API SHALL return the extracted parameters to the Frontend Application

### Requirement 2: Agent-Based Choreography Orchestration with Function Calling

**User Story:** As a system, I want to use OpenAI function calling to orchestrate choreography generation, so that the LLM can intelligently decide which tools to invoke based on the user's request.

#### Acceptance Criteria

1. WHEN the Backend API receives a Path 2 choreography generation request THEN the Agent Service SHALL define available functions (analyze_music, search_moves, generate_blueprint, assemble_video) for OpenAI to call
2. WHEN the Agent Service initializes a workflow THEN the Agent Service SHALL send the user request and function definitions to OpenAI GPT-4o-mini
3. WHEN OpenAI decides to call a function THEN the Agent Service SHALL execute the corresponding Python function and return results to OpenAI
4. WHEN the Agent Service executes a function THEN the Agent Service SHALL pass the function outputs as context for subsequent OpenAI decisions
5. WHEN the Agent Service encounters an error during function execution THEN the Agent Service SHALL capture the error details and return them to OpenAI for handling
6. WHEN OpenAI completes the workflow THEN the Agent Service SHALL return the final video URL and execution summary to the Backend API

### Requirement 3: Real-Time Agent Reasoning Display

**User Story:** As a user, I want to see what the AI agent is thinking and doing, so that I understand the choreography generation process and can trust the system.

#### Acceptance Criteria

1. WHEN the Agent Service creates an execution plan THEN the Backend API SHALL transmit the plan steps to the Frontend Application
2. WHEN the Agent Service executes a step THEN the Backend API SHALL transmit status updates containing step name, progress percentage, and status messages
3. WHEN the Agent Service invokes a service THEN the Backend API SHALL transmit service call information containing service name and parameter values
4. WHEN the Agent Service completes a step THEN the Backend API SHALL transmit the result summary to the Frontend Application
5. WHEN the Frontend Application receives status updates THEN the Reasoning Panel SHALL display the updates within 200 milliseconds

### Requirement 4: Conversational Chat Interface

**User Story:** As a user, I want to interact with the system through a chat interface, so that choreography generation feels natural and conversational.

#### Acceptance Criteria

1. WHEN a user navigates to the Path 2 page THEN the Frontend Application SHALL display the Chat Interface with at least three example prompts
2. WHEN a user submits a message in the Chat Interface THEN the Frontend Application SHALL transmit the message to the Backend API
3. WHEN the Backend API processes a choreography request THEN the Chat Interface SHALL display status updates in the conversation thread
4. WHEN the Agent Service completes choreography generation THEN the Chat Interface SHALL display the video player component with the generated video
5. WHEN a user initiates a new choreography request THEN the Chat Interface SHALL preserve the previous conversation messages

### Requirement 5: Path 1 Preservation

**User Story:** As an existing user, I want Path 1 (Select Song) to continue working exactly as before, so that my familiar workflow is not disrupted.

#### Acceptance Criteria

1. WHEN a user navigates to the Path 1 page THEN the Frontend Application SHALL display the existing song selection interface and parameter form
2. WHEN a user submits a request via Path 1 THEN the Backend API SHALL process the request using the existing non-agent workflow
3. WHEN the Backend API receives a Path 1 request THEN the Backend API SHALL bypass the Agent Service
4. WHEN developers execute Path 1 test suites THEN all existing Path 1 tests SHALL pass without modification
5. WHILE Path 2 implementation is modified THEN the Backend API SHALL maintain Path 1 code without changes

### Requirement 6: Backend Agent Service with Function Calling

**User Story:** As a backend system, I want a dedicated agent service that uses OpenAI function calling to orchestrate choreography generation, so that the workflow is maintainable and testable.

#### Acceptance Criteria

1. WHEN the Backend API starts THEN the Backend API SHALL initialize the Agent Service with music analyzer, vector search, blueprint generator, and video assembler dependencies
2. WHEN the Agent Service receives a choreography request THEN the Agent Service SHALL define tool schemas for OpenAI function calling (analyze_music, search_moves, generate_blueprint, assemble_video)
3. WHEN OpenAI requests a function call THEN the Agent Service SHALL execute the corresponding Python function and maintain conversation state
4. WHEN the Agent Service executes functions THEN the Agent Service SHALL update the Choreography Task database record with function call details and results
5. WHEN OpenAI completes the conversation THEN the Agent Service SHALL return the final workflow state containing results

### Requirement 7: OpenAI Integration for NLP

**User Story:** As a backend system, I want to use OpenAI GPT-4o-mini for parameter extraction, so that natural language understanding is accurate and cost-effective.

#### Acceptance Criteria

1. WHEN the Parameter Extractor processes a user request THEN the Parameter Extractor SHALL invoke OpenAI GPT-4o-mini API with structured extraction prompts
2. WHEN the Parameter Extractor invokes OpenAI API THEN the Parameter Extractor SHALL request JSON mode responses
3. WHEN the Parameter Extractor receives parameters from OpenAI THEN the Parameter Extractor SHALL validate each parameter against allowed value lists
4. WHEN the OpenAI API call fails THEN the Parameter Extractor SHALL execute keyword-based extraction as fallback
5. WHEN the Backend API starts with missing OpenAI API keys THEN the Backend API SHALL raise a configuration error

### Requirement 8: Real-Time Status Updates via HTTP Polling

**User Story:** As a user, I want to receive real-time updates during choreography generation, so that I can see progress as the agent works.

#### Acceptance Criteria

1. WHEN the Agent Service generates status updates THEN the Backend API SHALL store the updates in the Choreography Task database record
2. WHEN the Frontend Application polls for task status THEN the Backend API SHALL return the current agent status including step name and progress
3. WHEN the Frontend Application receives status updates THEN the Reasoning Panel SHALL display the updates within 200 milliseconds
4. WHEN the Agent Service completes a workflow step THEN the Backend API SHALL update the Choreography Task message field with step details
5. WHILE choreography generation is in progress THEN the Frontend Application SHALL poll the Backend API every 2 seconds

### Requirement 9: Agent Reasoning Persistence

**User Story:** As a user, I want to review the agent's reasoning steps after generation completes, so that I can understand how my choreography was created.

#### Acceptance Criteria

1. WHEN the Agent Service executes workflow steps THEN the Backend API SHALL update the Choreography Task message field with the current step description
2. WHEN the Agent Service completes a workflow step THEN the Backend API SHALL append the step summary to the Choreography Task stage field
3. WHEN choreography generation completes THEN the Backend API SHALL store the final agent summary in the Choreography Task result field
4. WHEN a user views a completed Choreography Task THEN the Frontend Application SHALL display the agent's reasoning steps from the stored fields
5. WHEN the Agent Service encounters an error THEN the Backend API SHALL store the error details in the Choreography Task error field

### Requirement 10: Path 2 Complete Rework

**User Story:** As a user of Path 2, I want a completely redesigned experience with agent orchestration and conversational interface, so that I can create choreography more naturally and understand the AI's decisions.

#### Acceptance Criteria

1. WHEN a user navigates to the Path 2 page THEN the Frontend Application SHALL display the new Chat Interface
2. WHEN a user submits a choreography request via Path 2 THEN the Backend API SHALL process the request using the Agent Service exclusively
3. WHEN the Backend API processes Path 2 requests THEN the Backend API SHALL transmit agent reasoning updates to the Frontend Application
4. WHEN the Agent Service completes choreography generation THEN the Frontend Application SHALL display the video player with an execution summary
5. WHEN developers deploy the Path 2 rework THEN the deployment SHALL remove all previous Path 2 implementation code

## Non-Functional Requirements

### Performance

1. THE Parameter Extractor SHALL complete parameter extraction within 2 seconds for 95% of requests
2. THE Agent Service SHALL complete execution planning within 1 second
3. THE Backend API SHALL transmit WebSocket updates with latency under 100 milliseconds
4. THE Backend API SHALL support at least 10 concurrent Agent Service executions

### Security

1. THE Backend API SHALL store OpenAI API keys in environment variables
2. THE Parameter Extractor SHALL sanitize user input before transmitting to OpenAI API
3. THE Backend API SHALL require authentication for WebSocket Connection establishment
4. THE Backend API SHALL restrict Execution Trace visibility to the Choreography Task owner

### Scalability

1. THE Agent Service SHALL maintain no persistent state to enable horizontal scaling
2. THE Backend API SHALL store Agent Service state in PostgreSQL database
3. THE Backend API SHALL support multiple concurrent agent executions without state conflicts

### Maintainability

1. THE Backend API SHALL implement Agent Service code in a dedicated service module
2. THE Agent Service SHALL have unit test coverage of at least 80 percent
3. THE Backend API SHALL log all Agent Service execution events
4. THE Backend API SHALL provide environment variables to enable or disable Agent Service features

## Success Criteria

1. Users can generate choreography using natural language descriptions
2. The agent reasoning display shows clear, understandable steps
3. Response time for parameter extraction is under 2 seconds
4. The system maintains 100% backward compatibility with existing workflows
5. Agent execution traces are stored and retrievable for debugging

## Out of Scope

The following features are explicitly out of scope for this specification:

1. **WebSocket Real-Time Updates** - Continue using existing HTTP polling mechanism (simpler, proven approach)
2. **MCP Protocol Implementation** - Direct service calls will be used instead of MCP servers
3. **Multi-Agent Collaboration** - Single agent only, no choreographer/critic/teacher agents
4. **RAG over Dance Knowledge** - No retrieval-augmented generation for answering "why" questions
5. **Voice Input** - Text-only interface
6. **Video Editing** - No post-generation editing capabilities
7. **Modal.com Integration** - Continue using existing Cloud Run Jobs for video assembly
8. **Demo Mode** - No pre-computed data caching
9. **Detailed Execution Traces** - Store only essential reasoning steps in existing database fields

## Dependencies

- **OpenAI API**: GPT-4o-mini for parameter extraction and function calling orchestration
- **OpenAI Function Calling**: Feature for intelligent tool/function orchestration
- **Existing Services**: Music analyzer, vector search, blueprint generator, video assembler
- **PostgreSQL**: Database for storing agent state and reasoning history

## Migration Strategy

1. **Phase 1**: Implement agent service in backend with parameter extraction
2. **Phase 2**: Add conversational chat interface to frontend
3. **Phase 3**: Integrate agent reasoning display with existing polling mechanism
4. **Phase 4**: Enable agent orchestration for Path 2 by default
5. **Phase 5**: Gather user feedback and iterate on conversational experience

## Testing Strategy

1. **Unit Tests**: Test agent nodes, parameter extraction, state management
2. **Integration Tests**: Test full agent workflow with mocked services
3. **End-to-End Tests**: Test conversational interface with real backend
4. **Performance Tests**: Measure parameter extraction and agent execution time
5. **Compatibility Tests**: Ensure existing workflows continue to function
