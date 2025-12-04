"""
Agent Service with OpenAI Function Calling

Orchestrates choreography generation using OpenAI function calling.
The LLM intelligently decides which functions to call and in what order
based on the user's natural language request.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)


class AgentServiceError(Exception):
    """Raised when agent service encounters an error."""
    pass


class AgentService:
    """
    Orchestrates choreography generation using OpenAI function calling.
    
    This service uses OpenAI's function calling feature to create an intelligent,
    adaptive workflow. The LLM decides which functions to call based on the
    user's request, enabling natural language choreography generation.
    """
    
    def __init__(
        self,
        openai_api_key: str,
        parameter_extractor,
        music_analyzer,
        vector_search,
        blueprint_generator,
        jobs_service
    ):
        """
        Initialize Agent Service with OpenAI client and service dependencies.
        
        Args:
            openai_api_key: OpenAI API key for function calling
            parameter_extractor: ParameterExtractor instance
            music_analyzer: MusicAnalyzer instance
            vector_search: VectorSearchService instance
            blueprint_generator: BlueprintGenerator instance
            jobs_service: JobsService instance
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.parameter_extractor = parameter_extractor
        self.music_analyzer = music_analyzer
        self.vector_search = vector_search
        self.blueprint_generator = blueprint_generator
        self.jobs_service = jobs_service
        
        # Task tracking attributes
        self.task_id = None
        self.user_id = None
        self.conversation_messages = []
        
        logger.info("AgentService initialized with OpenAI function calling")
    
    def create_workflow(
        self,
        task_id: str,
        user_request: str,
        user_id: int,
        song_path: str = None
    ):
        """
        Create and execute OpenAI function calling workflow for choreography generation.
        
        This method initializes a conversation with OpenAI, defines available tools,
        and orchestrates the workflow by executing functions as requested by the LLM.
        
        Args:
            task_id: Choreography task ID
            user_request: Natural language choreography request
            user_id: User ID
            song_path: Path to the selected song audio file (optional but recommended)
        
        Returns:
            ChoreographyTask with final status
        
        Raises:
            AgentServiceError: If workflow execution fails
        """
        # Initialize task tracking
        self.task_id = task_id
        self.user_id = user_id
        self.song_path = song_path  # Store for use in tool functions
        self.last_music_features = None  # Store music features for use in subsequent calls
        self.last_moves = None  # Store moves for use in subsequent calls
        self.last_blueprint = None  # Store blueprint for use in subsequent calls
        
        logger.info(
            f"Starting agent workflow for task {task_id}",
            extra={
                'task_id': task_id,
                'user_id': user_id,
                'user_request': user_request[:100],
                'song_path': song_path
            }
        )
        
        # Import here to avoid circular dependency
        from apps.choreography.models import ChoreographyTask
        
        try:
            # Get task from database
            task = ChoreographyTask.objects.get(task_id=task_id)
            
            # Update initial status
            stage = "initializing"
            self._update_task_status(
                task_id=task_id,
                message="Initializing agent workflow...",
                stage=stage,
                progress=self._calculate_progress(stage)
            )
            
            # Define available tools
            tools = self._define_tools()
            
            # Build system prompt with song path if available
            song_info = ""
            if song_path:
                song_info = f"\n\nIMPORTANT: A song has been pre-selected for this choreography. Use this exact path for analyze_music: '{song_path}'"
            
            # Initialize conversation with system prompt
            self.conversation_messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a choreography generation assistant. Use the available tools to create "
                        "a bachata choreography based on the user's request. Follow these steps:\n"
                        "1. Extract parameters from the user request (difficulty, energy_level, style)\n"
                        "2. Analyze the music using analyze_music\n"
                        "3. Search for matching moves using search_moves\n"
                        "4. Generate a blueprint using generate_blueprint\n"
                        "5. Assemble the video using assemble_video\n\n"
                        "Always call functions in this order and pass data between them appropriately."
                        f"{song_info}"
                    )
                },
                {
                    "role": "user",
                    "content": user_request
                }
            ]
            
            # Orchestration loop
            max_iterations = 10  # Prevent infinite loops
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                logger.debug(f"Orchestration loop iteration {iteration}")
                
                # Call OpenAI with current conversation state
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=self.conversation_messages,
                        tools=tools,
                        tool_choice="auto",
                        temperature=0.3
                    )
                except Exception as openai_error:
                    logger.error(
                        f"OpenAI API call failed: {openai_error}",
                        extra={
                            'task_id': task_id,
                            'iteration': iteration,
                            'error': str(openai_error)
                        },
                        exc_info=True
                    )
                    
                    # Update task with error
                    task.status = 'failed'
                    task.error = f"OpenAI API error: {str(openai_error)}"
                    task.message = "Failed to communicate with AI orchestration service"
                    task.save()
                    
                    raise AgentServiceError(f"OpenAI API error: {openai_error}") from openai_error
                
                message = response.choices[0].message
                
                # Add assistant message to conversation
                self.conversation_messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": message.tool_calls if hasattr(message, 'tool_calls') else None
                })
                
                # Check if OpenAI wants to call functions
                if message.tool_calls:
                    logger.info(f"OpenAI requested {len(message.tool_calls)} function calls")
                    
                    # Execute each requested function
                    for tool_call in message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        logger.info(
                            f"Executing tool: {function_name}",
                            extra={
                                'task_id': task_id,
                                'function_name': function_name,
                                'iteration': iteration
                            }
                        )
                        
                        # Execute function with error handling
                        try:
                            function_result = self._execute_function(function_name, function_args)
                            
                            # Log successful execution
                            logger.info(
                                f"Function {function_name} completed successfully",
                                extra={
                                    'task_id': task_id,
                                    'function_name': function_name,
                                    'result_status': function_result.get('status', 'unknown')
                                }
                            )
                            
                        except Exception as e:
                            # Log error
                            logger.error(
                                f"Function {function_name} failed: {e}",
                                extra={
                                    'task_id': task_id,
                                    'function_name': function_name,
                                    'error': str(e)
                                },
                                exc_info=True
                            )
                            
                            # Update task with error
                            self._update_task_status(
                                task_id=task_id,
                                message=f"Error in {function_name}: {str(e)}",
                                stage=function_name,
                                progress=task.progress
                            )
                            
                            # Return error result to OpenAI
                            function_result = {
                                'error': str(e),
                                'status': 'failed',
                                'function': function_name
                            }
                        
                        # Add function result to conversation
                        self.conversation_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(function_result)
                        })
                else:
                    # No more function calls - workflow complete
                    logger.info("Workflow complete - no more function calls requested")
                    
                    # Update final status - this will also set status to 'completed'
                    stage = "completed"
                    self._update_task_status(
                        task_id=task_id,
                        message="Choreography generation complete",
                        stage=stage,
                        progress=self._calculate_progress(stage)
                    )
                    
                    break
            
            if iteration >= max_iterations:
                logger.warning(f"Workflow reached max iterations ({max_iterations})")
                stage = "completed"
                self._update_task_status(
                    task_id=task_id,
                    message="Workflow reached maximum iterations",
                    stage=stage,
                    progress=self._calculate_progress(stage)
                )
            
            return task
            
        except ChoreographyTask.DoesNotExist:
            logger.error(f"Task {task_id} not found")
            raise AgentServiceError(f"Task {task_id} not found")
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            
            # Update task with error
            try:
                task = ChoreographyTask.objects.get(task_id=task_id)
                task.status = 'failed'
                task.error = str(e)
                task.message = f"Workflow failed: {str(e)}"
                task.save()
            except Exception as update_error:
                logger.error(f"Failed to update task with error: {update_error}")
            
            raise AgentServiceError(f"Workflow execution failed: {e}") from e
    
    def _define_tools(self) -> List[Dict]:
        """
        Define function/tool schemas for OpenAI function calling.
        
        These tools represent the available functions that OpenAI can call
        to orchestrate the choreography generation workflow.
        
        Returns:
            List of tool definition dictionaries
        """
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "analyze_music",
                    "description": "Analyze music features from the selected song including tempo, beats, energy profile, and musical sections",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "song_path": {
                                "type": "string",
                                "description": "Path to the audio file (e.g., 'songs/Angel.mp3')"
                            }
                        },
                        "required": ["song_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_moves",
                    "description": "Search for dance moves matching the music features and user parameters. Music features from the previous analyze_music call are automatically used if not provided.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "music_features": {
                                "type": "object",
                                "description": "Music analysis results from analyze_music function (optional - uses stored features if not provided)"
                            },
                            "difficulty": {
                                "type": "string",
                                "enum": ["beginner", "intermediate", "advanced"],
                                "description": "Difficulty level for the choreography"
                            },
                            "energy_level": {
                                "type": "string",
                                "enum": ["low", "medium", "high"],
                                "description": "Energy level for the choreography"
                            },
                            "style": {
                                "type": "string",
                                "enum": ["traditional", "modern", "romantic", "sensual"],
                                "description": "Style preference for the choreography"
                            }
                        },
                        "required": ["difficulty", "energy_level", "style"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_blueprint",
                    "description": "Generate choreography blueprint from selected moves and music features. Uses stored moves and music features from previous calls if not provided.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "moves": {
                                "type": "array",
                                "description": "List of selected dance moves (optional - uses stored moves from search_moves if not provided)",
                                "items": {
                                    "type": "object"
                                }
                            },
                            "music_features": {
                                "type": "object",
                                "description": "Music analysis results (optional - uses stored features from analyze_music if not provided)"
                            },
                            "difficulty": {
                                "type": "string",
                                "description": "Difficulty level"
                            },
                            "energy_level": {
                                "type": "string",
                                "description": "Energy level"
                            },
                            "style": {
                                "type": "string",
                                "description": "Style preference"
                            }
                        },
                        "required": ["difficulty", "energy_level", "style"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "assemble_video",
                    "description": "Trigger video assembly job to create the final choreography video. Uses stored blueprint from previous generate_blueprint call if not provided.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "blueprint": {
                                "type": "object",
                                "description": "Choreography blueprint (optional - uses stored blueprint from generate_blueprint if not provided)"
                            }
                        },
                        "required": []
                    }
                }
            }
        ]
        
        logger.debug(f"Defined {len(tools)} tools for OpenAI function calling")
        return tools
    
    def _execute_function(self, function_name: str, arguments: Dict) -> Dict:
        """
        Execute a function requested by OpenAI.
        
        Routes function calls to appropriate service methods and returns
        structured results to OpenAI for continued orchestration.
        
        Args:
            function_name: Name of the function to execute
            arguments: Function arguments as dictionary
        
        Returns:
            Function result as dictionary
        
        Raises:
            AgentServiceError: If function execution fails
        """
        logger.info(
            f"Executing function: {function_name}",
            extra={
                'function_name': function_name,
                'task_id': self.task_id,
                'arguments_keys': list(arguments.keys())
            }
        )
        
        try:
            if function_name == "analyze_music":
                return self._analyze_music(arguments['song_path'])
            
            elif function_name == "search_moves":
                return self._search_moves(
                    music_features=arguments.get('music_features'),
                    difficulty=arguments.get('difficulty', 'intermediate'),
                    energy_level=arguments.get('energy_level', 'medium'),
                    style=arguments.get('style', 'modern')
                )
            
            elif function_name == "generate_blueprint":
                return self._generate_blueprint(
                    moves=arguments.get('moves'),
                    music_features=arguments.get('music_features'),
                    difficulty=arguments.get('difficulty', 'intermediate'),
                    energy_level=arguments.get('energy_level', 'medium'),
                    style=arguments.get('style', 'modern')
                )
            
            elif function_name == "assemble_video":
                return self._assemble_video(blueprint=arguments.get('blueprint'))
            
            else:
                error_msg = f"Unknown function: {function_name}"
                logger.error(error_msg)
                raise AgentServiceError(error_msg)
                
        except KeyError as e:
            error_msg = f"Missing required argument for {function_name}: {e}"
            logger.error(error_msg)
            raise AgentServiceError(error_msg) from e
        except Exception as e:
            error_msg = f"Function {function_name} execution failed: {e}"
            logger.error(error_msg, exc_info=True)
            raise AgentServiceError(error_msg) from e
    
    def _analyze_music(self, song_path: str) -> Dict:
        """
        Tool: Analyze music features from audio file.
        
        Args:
            song_path: Path to audio file
        
        Returns:
            Dictionary with music features
        """
        import os
        
        logger.info(f"Analyzing music: {song_path}")
        
        try:
            # Convert relative path to absolute path
            if not os.path.isabs(song_path):
                # Prepend data directory
                data_dir = os.environ.get('DATA_DIR', '/app/data')
                song_path = os.path.join(data_dir, song_path)
            
            logger.info(f"Full audio path: {song_path}")
            
            if not os.path.exists(song_path):
                raise FileNotFoundError(f"Audio file not found: {song_path}")
            
            # Call music analyzer service
            music_features = self.music_analyzer.analyze_audio(song_path)
            
            # Update task status
            stage = "analyze_music"
            self._update_task_status(
                task_id=self.task_id,
                message=f"Music analyzed: {music_features.tempo:.1f} BPM, {music_features.duration:.1f}s",
                stage=stage,
                progress=self._calculate_progress(stage)
            )
            
            # Convert to serializable format
            result = {
                'tempo': music_features.tempo,
                'duration': music_features.duration,
                'beat_positions': music_features.beat_positions[:20],  # Limit for JSON size
                'audio_embedding': music_features.audio_embedding,
                'sections': [
                    {
                        'start_time': s.start_time,
                        'end_time': s.end_time,
                        'section_type': s.section_type,
                        'energy_level': s.energy_level
                    }
                    for s in music_features.sections
                ]
            }
            
            logger.info(f"Music analysis complete: {music_features.tempo:.1f} BPM")
            
            # Store for use in subsequent calls
            self.last_music_features = result
            
            return {'music_features': result, 'status': 'success'}
            
        except Exception as e:
            logger.error(f"Music analysis failed: {e}", exc_info=True)
            return {'error': str(e), 'status': 'failed'}
    
    def _search_moves(
        self,
        music_features: Dict = None,
        difficulty: str = 'intermediate',
        energy_level: str = 'medium',
        style: str = 'modern'
    ) -> Dict:
        """
        Tool: Search for matching dance moves.
        
        Args:
            music_features: Music analysis results (optional, uses stored features if not provided)
            difficulty: Difficulty level
            energy_level: Energy level
            style: Style preference
        
        Returns:
            Dictionary with matching moves
        """
        logger.info(f"Searching moves: difficulty={difficulty}, energy={energy_level}, style={style}")
        
        # Use stored music features if not provided
        if music_features is None:
            if self.last_music_features is not None:
                music_features = self.last_music_features
                logger.info("Using stored music features from previous analyze_music call")
            else:
                logger.warning("No music features available, using default search")
                # Return a fallback search without audio embedding
                return self._search_moves_without_audio(difficulty, energy_level, style)
        
        try:
            # Create query embedding from music features
            import numpy as np
            from services.vector_search_service import VectorSearchService
            
            audio_embedding = np.array(music_features['audio_embedding'], dtype=np.float32)
            query_embedding = VectorSearchService.combine_embeddings_weighted(
                pose_embedding=None,
                audio_embedding=audio_embedding,
                text_embedding=None
            )
            
            # Search for matching moves
            filters = {
                'difficulty': difficulty,
                'energy_level': energy_level,
                'style': style
            }
            
            results = self.vector_search.search_similar_moves(
                query_embedding=query_embedding,
                filters=filters,
                top_k=20
            )
            
            # Update task status
            stage = "search_moves"
            self._update_task_status(
                task_id=self.task_id,
                message=f"Found {len(results)} matching moves",
                stage=stage,
                progress=self._calculate_progress(stage)
            )
            
            # Convert to serializable format
            moves = [result.to_dict() for result in results]
            
            logger.info(f"Move search complete: {len(moves)} moves found")
            
            # Store for use in subsequent calls
            self.last_moves = moves
            
            return {'moves': moves, 'count': len(moves), 'status': 'success'}
            
        except Exception as e:
            logger.error(f"Move search failed: {e}", exc_info=True)
            return {'error': str(e), 'status': 'failed'}
    
    def _search_moves_without_audio(
        self,
        difficulty: str,
        energy_level: str,
        style: str
    ) -> Dict:
        """
        Fallback search for moves without audio embedding.
        
        Uses only metadata filters to find matching moves.
        """
        logger.info(f"Fallback move search: difficulty={difficulty}, energy={energy_level}, style={style}")
        
        try:
            # Search with filters only, no embedding
            filters = {
                'difficulty': difficulty,
                'energy_level': energy_level,
                'style': style
            }
            
            # Create a random query embedding as fallback
            import numpy as np
            from services.vector_search_service import VectorSearchService
            
            # Use zero embedding - will rely on filters
            query_embedding = np.zeros(
                VectorSearchService.POSE_EMBEDDING_DIM + 
                VectorSearchService.AUDIO_EMBEDDING_DIM + 
                VectorSearchService.TEXT_EMBEDDING_DIM,
                dtype=np.float32
            )
            
            results = self.vector_search.search_similar_moves(
                query_embedding=query_embedding,
                filters=filters,
                top_k=20
            )
            
            # Update task status
            stage = "search_moves"
            self._update_task_status(
                task_id=self.task_id,
                message=f"Found {len(results)} matching moves (fallback search)",
                stage=stage,
                progress=self._calculate_progress(stage)
            )
            
            moves = [result.to_dict() for result in results]
            
            logger.info(f"Fallback move search complete: {len(moves)} moves found")
            
            # Store for use in subsequent calls
            self.last_moves = moves
            
            return {'moves': moves, 'count': len(moves), 'status': 'success'}
            
        except Exception as e:
            logger.error(f"Fallback move search failed: {e}", exc_info=True)
            return {'error': str(e), 'status': 'failed'}
    
    def _generate_blueprint(
        self,
        moves: List[Dict] = None,
        music_features: Dict = None,
        difficulty: str = 'intermediate',
        energy_level: str = 'medium',
        style: str = 'modern'
    ) -> Dict:
        """
        Tool: Generate choreography blueprint.
        
        Args:
            moves: List of selected moves (optional - uses stored moves if not provided)
            music_features: Music analysis results (optional - uses stored features if not provided)
            difficulty: Difficulty level
            energy_level: Energy level
            style: Style preference
        
        Returns:
            Dictionary with blueprint
        """
        # Use stored values if not provided
        if moves is None:
            if self.last_moves is not None:
                moves = self.last_moves
                logger.info("Using stored moves from previous search_moves call")
            else:
                return {'error': 'No moves available. Please call search_moves first.', 'status': 'failed'}
        
        if music_features is None:
            if self.last_music_features is not None:
                music_features = self.last_music_features
                logger.info("Using stored music features from previous analyze_music call")
            else:
                # Use default values
                music_features = {'tempo': 120.0, 'duration': 180.0}
                logger.warning("No music features available, using defaults")
        
        logger.info(f"Generating blueprint with {len(moves)} moves")
        
        try:
            # For now, use a simplified approach
            # The blueprint generator expects a song_path, so we'll need to handle this
            # In the full implementation, we'd reconstruct the MusicFeatures object
            
            # Create a simple blueprint structure
            # Use the stored song_path if available
            audio_path = self.song_path if self.song_path else 'songs/placeholder.mp3'
            
            blueprint = {
                'task_id': self.task_id,
                'audio_path': audio_path,
                'audio_tempo': music_features['tempo'],
                'moves': [],
                'total_duration': music_features['duration'],
                'difficulty_level': difficulty,
                'generation_parameters': {
                    'energy_level': energy_level,
                    'style': style,
                    'user_id': self.user_id
                },
                'output_config': {
                    'output_path': f"output/user_{self.user_id}/choreography_{self.task_id}.mp4",
                    'output_format': 'mp4',
                    'video_codec': 'libx264',
                    'audio_codec': 'aac',
                    'video_bitrate': '2M',
                    'audio_bitrate': '128k',
                    'frame_rate': 30,
                    'transition_duration': 0.5,
                    'fade_duration': 0.3,
                    'add_audio_overlay': True,
                    'normalize_audio': True
                }
            }
            
            # Calculate how many moves we need to fill the song duration
            song_duration = music_features['duration']
            avg_move_duration = sum(move.get('duration', 8.0) for move in moves) / len(moves) if moves else 8.0
            moves_needed = int(song_duration / avg_move_duration) + 1
            
            logger.info(f"Song duration: {song_duration}s, avg move duration: {avg_move_duration}s, moves needed: {moves_needed}")
            
            # Add moves to blueprint - repeat moves if necessary to fill the song
            current_time = 0.0
            move_index = 0
            clip_counter = 0
            
            while current_time < song_duration and clip_counter < 100:  # Safety limit
                # Cycle through available moves
                move = moves[move_index % len(moves)]
                move_duration = move.get('duration', 8.0)
                
                # Don't exceed song duration
                if current_time + move_duration > song_duration:
                    move_duration = song_duration - current_time
                
                if move_duration > 0:
                    blueprint['moves'].append({
                        'clip_id': f"move_{clip_counter+1}",
                        'video_path': move['video_path'],
                        'start_time': current_time,
                        'duration': move_duration,
                        'transition_type': 'crossfade' if clip_counter > 0 else 'cut',
                        'original_duration': move.get('duration', 8.0),
                        'trim_start': 0.0,
                        'trim_end': 0.0,
                        'volume_adjustment': 1.0
                    })
                    current_time += move_duration
                    clip_counter += 1
                
                move_index += 1
            
            logger.info(f"Generated blueprint with {len(blueprint['moves'])} moves to fill {song_duration}s")
            
            # Save blueprint to database
            from apps.choreography.models import Blueprint, ChoreographyTask
            
            try:
                task = ChoreographyTask.objects.get(task_id=self.task_id)
                Blueprint.objects.create(
                    task=task,
                    blueprint_json=blueprint
                )
                logger.info(f"Blueprint saved to database for task {self.task_id}")
            except Exception as db_error:
                logger.error(f"Failed to save blueprint to database: {db_error}", exc_info=True)
                # Continue anyway - blueprint is still in memory
            
            # Update task status
            stage = "generate_blueprint"
            self._update_task_status(
                task_id=self.task_id,
                message=f"Blueprint generated with {len(blueprint['moves'])} moves ({song_duration:.1f}s)",
                stage=stage,
                progress=self._calculate_progress(stage)
            )
            
            logger.info(f"Blueprint generation complete: {len(blueprint['moves'])} moves")
            
            # Store for use in subsequent calls
            self.last_blueprint = blueprint
            
            return {'blueprint': blueprint, 'num_moves': len(blueprint['moves']), 'status': 'success'}
            
        except Exception as e:
            logger.error(f"Blueprint generation failed: {e}", exc_info=True)
            return {'error': str(e), 'status': 'failed'}
    
    def _assemble_video(self, blueprint: Dict = None) -> Dict:
        """
        Tool: Trigger video assembly job.
        
        Args:
            blueprint: Choreography blueprint (optional - uses stored blueprint if not provided)
        
        Returns:
            Dictionary with job execution info
        """
        # Use stored blueprint if not provided
        if blueprint is None:
            if self.last_blueprint is not None:
                blueprint = self.last_blueprint
                logger.info("Using stored blueprint from previous generate_blueprint call")
            else:
                return {'error': 'No blueprint available. Please call generate_blueprint first.', 'status': 'failed'}
        
        logger.info(f"Triggering video assembly for task {self.task_id}")
        
        try:
            # Submit job with blueprint
            execution_name = self.jobs_service.create_job_execution(
                task_id=self.task_id,
                user_id=self.user_id,
                parameters={'blueprint_json': json.dumps(blueprint)}
            )
            
            # Update task status
            stage = "assemble_video"
            self._update_task_status(
                task_id=self.task_id,
                message=f"Video assembly started: {execution_name}",
                stage=stage,
                progress=self._calculate_progress(stage)
            )
            
            logger.info(f"Video assembly job submitted: {execution_name}")
            return {
                'execution_name': execution_name,
                'status': 'success',
                'message': 'Video assembly job submitted'
            }
            
        except Exception as e:
            logger.error(f"Video assembly failed: {e}", exc_info=True)
            return {'error': str(e), 'status': 'failed'}
    
    def _calculate_progress(self, stage: str) -> int:
        """
        Calculate progress percentage based on workflow stage.
        
        Maps function names to progress percentages to provide
        consistent progress tracking throughout the workflow.
        
        Args:
            stage: Current workflow stage name
        
        Returns:
            Progress percentage (0-100)
        """
        # Progress mapping for each stage
        progress_map = {
            'initializing': 0,
            'extract_parameters': 10,
            'analyze_music': 25,
            'search_moves': 50,
            'generate_blueprint': 75,
            'assemble_video': 90,
            'completed': 100
        }
        
        # Return mapped progress or default to 0
        return progress_map.get(stage, 0)
    
    def _update_task_status(
        self,
        task_id: str,
        message: str,
        stage: str,
        progress: int
    ):
        """
        Update task status in database.
        
        Args:
            task_id: Task ID
            message: Status message
            stage: Current workflow stage
            progress: Progress percentage (0-100)
        """
        from apps.choreography.models import ChoreographyTask
        
        try:
            task = ChoreographyTask.objects.get(task_id=task_id)
            task.message = message
            task.stage = stage
            task.progress = progress
            if progress >= 100:
                task.status = 'completed'
            elif progress > 0:
                task.status = 'running'
            task.save()
            
            logger.info(
                f"Task status updated: {stage} ({progress}%)",
                extra={
                    'task_id': task_id,
                    'stage': stage,
                    'progress': progress,
                    'status_message': message
                }
            )
        except ChoreographyTask.DoesNotExist:
            logger.error(f"Task {task_id} not found for status update")
        except Exception as e:
            logger.error(f"Failed to update task status: {e}", exc_info=True)
