from django.apps import AppConfig
import warnings


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """
        DEPRECATION NOTICE:
        
        The 'core' app has been refactored and is no longer in use.
        All services have been moved to specialized apps:
        
        - Common utilities → 'common' app
          - resource_manager, temp_file_manager, performance_monitor, directory_organizer
          - environment_config, exceptions
        
        - AI/ML services → 'ai_services' app
          - gemini_service, elasticsearch_service, text_embedding_service
          - recommendation_engine, move_analyzer, feature_fusion
          - quality_metrics, embedding_validator, hyperparameter_optimizer, model_validation
        
        - Video processing → 'video_processing' app
          - video_generator, video_storage_service, audio_storage_service
          - youtube_service, choreography_pipeline
          - yolov8_couple_detector, pose_feature_extractor, pose_embedding_generator
          - couple_interaction_analyzer, music_analyzer
          - video_models
        
        The core app has been removed from INSTALLED_APPS as it contains no Django models
        or migrations. Only Pydantic schemas remain in core/models/annotation_schema.py
        for backward compatibility.
        
        Please update your imports:
        - from core.services.* → from common.services.*, ai_services.services.*, or video_processing.services.*
        - from core.config.* → from common.config.*
        - from core.exceptions → from common.exceptions
        - from core.models.video_models → from video_processing.models
        """
        warnings.warn(
            "The 'core' app is deprecated. Services have been moved to 'common', "
            "'ai_services', and 'video_processing' apps. Update your imports accordingly.",
            DeprecationWarning,
            stacklevel=2
        )
