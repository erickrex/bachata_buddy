"""
Create Kibana dashboards programmatically for Bachata Buddy observability.

This script creates dashboards, visualizations, and index patterns using
Kibana's Saved Objects API, avoiding manual UI configuration.

Usage:
    uv run python scripts/create_kibana_dashboards.py
"""

import requests
import json
import logging
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config.environment_config import EnvironmentConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KibanaDashboardCreator:
    """Create Kibana dashboards programmatically using Saved Objects API."""
    
    def __init__(self, config: EnvironmentConfig):
        """
        Initialize Kibana dashboard creator.
        
        Args:
            config: Environment configuration with Elasticsearch settings
        """
        self.config = config
        
        # Derive Kibana URL from Elasticsearch host
        # Format: project-id.es.region.gcp.elastic-cloud.com -> project-id.kb.region.gcp.elastic-cloud.com
        es_host = config.elasticsearch.host
        self.kibana_url = es_host.replace('.es.', '.kb.')
        
        # Use same API key as Elasticsearch
        self.api_key = config.elasticsearch.api_key
        
        self.headers = {
            'Authorization': f'ApiKey {self.api_key}',
            'kbn-xsrf': 'true',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"Kibana URL: https://{self.kibana_url}")
    
    def create_index_pattern(self, pattern_id: str, title: str, time_field: str = '@timestamp'):
        """
        Create an index pattern in Kibana.
        
        Args:
            pattern_id: Unique ID for the index pattern
            title: Index pattern (e.g., 'app-logs-*')
            time_field: Time field name (default: '@timestamp')
        """
        url = f'https://{self.kibana_url}/api/saved_objects/index-pattern/{pattern_id}'
        
        payload = {
            'attributes': {
                'title': title,
                'timeFieldName': time_field
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Created index pattern: {title}")
                return response.json()
            elif response.status_code == 409:
                logger.info(f"⚠️  Index pattern already exists: {title}")
                return None
            else:
                logger.error(f"❌ Failed to create index pattern: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating index pattern: {e}")
            return None
    
    def create_visualization(self, viz_id: str, title: str, viz_config: dict):
        """
        Create a visualization in Kibana.
        
        Args:
            viz_id: Unique ID for the visualization
            title: Visualization title
            viz_config: Visualization configuration (type, params, etc.)
        """
        url = f'https://{self.kibana_url}/api/saved_objects/visualization/{viz_id}'
        
        payload = {
            'attributes': {
                'title': title,
                'visState': json.dumps(viz_config),
                'uiStateJSON': '{}',
                'description': '',
                'version': 1,
                'kibanaSavedObjectMeta': {
                    'searchSourceJSON': json.dumps({
                        'query': {'query': '', 'language': 'kuery'},
                        'filter': []
                    })
                }
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Created visualization: {title}")
                return response.json()
            elif response.status_code == 409:
                logger.info(f"⚠️  Visualization already exists: {title}")
                return None
            else:
                logger.error(f"❌ Failed to create visualization: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating visualization: {e}")
            return None
    
    def create_dashboard(self, dashboard_id: str, title: str, panel_configs: list):
        """
        Create a dashboard in Kibana.
        
        Args:
            dashboard_id: Unique ID for the dashboard
            title: Dashboard title
            panel_configs: List of panel configurations
        """
        url = f'https://{self.kibana_url}/api/saved_objects/dashboard/{dashboard_id}'
        
        payload = {
            'attributes': {
                'title': title,
                'hits': 0,
                'description': f'Auto-generated dashboard for {title}',
                'panelsJSON': json.dumps(panel_configs),
                'optionsJSON': json.dumps({
                    'useMargins': True,
                    'hidePanelTitles': False
                }),
                'version': 1,
                'timeRestore': False,
                'kibanaSavedObjectMeta': {
                    'searchSourceJSON': json.dumps({
                        'query': {'query': '', 'language': 'kuery'},
                        'filter': []
                    })
                }
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Created dashboard: {title}")
                logger.info(f"   View at: https://{self.kibana_url}/app/dashboards#/view/{dashboard_id}")
                return response.json()
            elif response.status_code == 409:
                logger.info(f"⚠️  Dashboard already exists: {title}")
                logger.info(f"   View at: https://{self.kibana_url}/app/dashboards#/view/{dashboard_id}")
                return None
            else:
                logger.error(f"❌ Failed to create dashboard: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating dashboard: {e}")
            return None
    
    def create_performance_dashboard(self):
        """Create performance monitoring dashboard."""
        logger.info("\n📊 Creating Performance Dashboard...")
        
        # 1. Create index pattern for metrics
        self.create_index_pattern(
            'app-metrics-pattern',
            'app-metrics-*',
            '@timestamp'
        )
        
        # 2. Create visualizations
        
        # Average latency by operation
        latency_viz = {
            'title': 'Average Latency by Operation',
            'type': 'line',
            'aggs': [
                {
                    'id': '1',
                    'enabled': True,
                    'type': 'avg',
                    'schema': 'metric',
                    'params': {'field': 'duration_ms'}
                },
                {
                    'id': '2',
                    'enabled': True,
                    'type': 'date_histogram',
                    'schema': 'segment',
                    'params': {
                        'field': '@timestamp',
                        'interval': 'auto',
                        'min_doc_count': 1
                    }
                },
                {
                    'id': '3',
                    'enabled': True,
                    'type': 'terms',
                    'schema': 'group',
                    'params': {
                        'field': 'operation.keyword',
                        'size': 10,
                        'order': 'desc',
                        'orderBy': '1'
                    }
                }
            ],
            'params': {
                'type': 'line',
                'grid': {'categoryLines': False},
                'categoryAxes': [{'id': 'CategoryAxis-1', 'type': 'category', 'position': 'bottom'}],
                'valueAxes': [{'id': 'ValueAxis-1', 'type': 'value', 'position': 'left'}],
                'seriesParams': [{'show': True, 'type': 'line', 'mode': 'normal'}]
            }
        }
        
        self.create_visualization(
            'perf-latency-viz',
            'Average Latency by Operation',
            latency_viz
        )
        
        # Operation count
        count_viz = {
            'title': 'Operations Count',
            'type': 'metric',
            'aggs': [
                {
                    'id': '1',
                    'enabled': True,
                    'type': 'count',
                    'schema': 'metric',
                    'params': {}
                }
            ],
            'params': {
                'metric': {
                    'percentageMode': False,
                    'useRanges': False,
                    'colorSchema': 'Green to Red',
                    'metricColorMode': 'None',
                    'colorsRange': [{'from': 0, 'to': 10000}],
                    'labels': {'show': True},
                    'invertColors': False,
                    'style': {'bgFill': '#000', 'bgColor': False, 'labelColor': False, 'subText': '', 'fontSize': 60}
                }
            }
        }
        
        self.create_visualization(
            'perf-count-viz',
            'Total Operations',
            count_viz
        )
        
        # 3. Create dashboard with panels
        panels = [
            {
                'version': '8.0.0',
                'gridData': {'x': 0, 'y': 0, 'w': 24, 'h': 15, 'i': '1'},
                'panelIndex': '1',
                'embeddableConfig': {},
                'panelRefName': 'panel_1'
            },
            {
                'version': '8.0.0',
                'gridData': {'x': 24, 'y': 0, 'w': 24, 'h': 15, 'i': '2'},
                'panelIndex': '2',
                'embeddableConfig': {},
                'panelRefName': 'panel_2'
            }
        ]
        
        self.create_dashboard(
            'bachata-performance-dashboard',
            'Bachata Buddy - Performance Monitoring',
            panels
        )
    
    def create_error_dashboard(self):
        """Create error tracking dashboard."""
        logger.info("\n🚨 Creating Error Dashboard...")
        
        # 1. Create index pattern for logs
        self.create_index_pattern(
            'app-logs-pattern',
            'app-logs-*',
            '@timestamp'
        )
        
        # 2. Create error count visualization
        error_count_viz = {
            'title': 'Error Count Over Time',
            'type': 'histogram',
            'aggs': [
                {
                    'id': '1',
                    'enabled': True,
                    'type': 'count',
                    'schema': 'metric',
                    'params': {}
                },
                {
                    'id': '2',
                    'enabled': True,
                    'type': 'date_histogram',
                    'schema': 'segment',
                    'params': {
                        'field': '@timestamp',
                        'interval': 'auto',
                        'min_doc_count': 1
                    }
                }
            ],
            'params': {}
        }
        
        self.create_visualization(
            'error-count-viz',
            'Error Count Over Time',
            error_count_viz
        )
        
        # 3. Create dashboard
        panels = [
            {
                'version': '8.0.0',
                'gridData': {'x': 0, 'y': 0, 'w': 48, 'h': 15, 'i': '1'},
                'panelIndex': '1',
                'embeddableConfig': {},
                'panelRefName': 'panel_1'
            }
        ]
        
        self.create_dashboard(
            'bachata-error-dashboard',
            'Bachata Buddy - Error Tracking',
            panels
        )
    
    def create_usage_dashboard(self):
        """Create usage analytics dashboard."""
        logger.info("\n📈 Creating Usage Dashboard...")
        
        # 1. Create index pattern for events
        self.create_index_pattern(
            'app-events-pattern',
            'app-events-*',
            '@timestamp'
        )
        
        # 2. Create template usage visualization
        template_viz = {
            'title': 'Template Usage (Legacy vs AI)',
            'type': 'pie',
            'aggs': [
                {
                    'id': '1',
                    'enabled': True,
                    'type': 'count',
                    'schema': 'metric',
                    'params': {}
                },
                {
                    'id': '2',
                    'enabled': True,
                    'type': 'terms',
                    'schema': 'segment',
                    'params': {
                        'field': 'data.template_type.keyword',
                        'size': 5,
                        'order': 'desc',
                        'orderBy': '1'
                    }
                }
            ],
            'params': {
                'type': 'pie',
                'addTooltip': True,
                'addLegend': True,
                'legendPosition': 'right',
                'isDonut': True
            }
        }
        
        self.create_visualization(
            'usage-template-viz',
            'Template Usage',
            template_viz
        )
        
        # 3. Create dashboard
        panels = [
            {
                'version': '8.0.0',
                'gridData': {'x': 0, 'y': 0, 'w': 24, 'h': 15, 'i': '1'},
                'panelIndex': '1',
                'embeddableConfig': {},
                'panelRefName': 'panel_1'
            }
        ]
        
        self.create_dashboard(
            'bachata-usage-dashboard',
            'Bachata Buddy - Usage Analytics',
            panels
        )
    
    def create_all_dashboards(self):
        """Create all dashboards."""
        logger.info("🚀 Creating Kibana Dashboards for Bachata Buddy\n")
        
        try:
            self.create_performance_dashboard()
            self.create_error_dashboard()
            self.create_usage_dashboard()
            
            logger.info("\n✅ All dashboards created successfully!")
            logger.info(f"\n📊 Access your dashboards at:")
            logger.info(f"   https://{self.kibana_url}/app/dashboards")
            
        except Exception as e:
            logger.error(f"\n❌ Error creating dashboards: {e}")
            raise


def main():
    """Main function to create dashboards."""
    try:
        # Load configuration
        config = EnvironmentConfig()
        
        # Verify Elasticsearch configuration
        if not config.elasticsearch.api_key:
            logger.error("❌ ELASTICSEARCH_API_KEY not set in environment")
            return 1
        
        if not config.elasticsearch.host:
            logger.error("❌ ELASTICSEARCH_HOST not set in environment")
            return 1
        
        # Create dashboards
        creator = KibanaDashboardCreator(config)
        creator.create_all_dashboards()
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Failed to create dashboards: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit(main())
