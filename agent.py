from flask import Flask, jsonify
import winreg
import os
import sys
from flask_cors import CORS
import threading
import socketio
import uuid
from collections import deque
import logging

from config.settings import Settings
from config.device import DeviceManager
from utils.root import RootManager
from network.api.tool.index import blueprints, dispatcher_config
# from tasks.post_content import PostContent
# from tasks.crawl_internal_websitePosts import CrawlInternalWebsitePosts
# from tasks.publish_website_post import PublishWebsitePost
# from tasks.crawl_external_website_posts import CrawlExternalWebsitePosts
# from tasks.crawl_fanpage_newsfeed import CrawlFanpageNewsfeed
# from tasks.monitor_fanpage_newsfeed import MonitorFanpageNewsfeed
# from tasks.crawl_fanpage_data import CrawlFanpageData
# from tasks.follow_fanpage import FollowFanpage
# from tasks.crawl_viaNews_feed import CrawlViaNewsfeed
# from tasks.auto_crawl_website import AutoCrawlWebsite

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Allowed CORS origin
ALLOWED_ORIGIN = "*"


class StartApp:
    """Main application class for Flask server initialization."""
    
    def __init__(self):
        self.app = None
        self.device_manager = None
        self.ws_client = WSClient()
    
    def start(self) -> Flask:
        """Initialize and start the Flask application."""
        try:
            self.app = self._create_flask_app()
            self._configure_cors()
            self._register_blueprints()
            self._configure_jinja()
            self._register_error_handlers()
            
            # Register URI scheme only for build version
            if Settings.version == "build":
                self.register_uri_scheme()
            
            # Initialize device manager
            self.device_manager = DeviceManager()
            self.device_manager.create_dependencies()
            
            # Initialize and connect WebSocket client
            self.ws_client.connect()
            
            # Run Flask app
            logger.info("Starting Flask application on http://127.0.0.1:2004")
            self.app.run(
                host="127.0.0.1",
                port=2004,
                debug=True,
                use_reloader=False  # Avoid double initialization with WebSocket
            )
            
            return self.app
            
        except Exception as e:
            logger.error(f"Failed to start application: {e}", exc_info=True)
            raise
    
    def _create_flask_app(self) -> Flask:
        """Create Flask application instance."""
        return Flask(__name__)
    
    def _configure_cors(self):
        """Configure CORS for the application."""
        CORS(
            self.app,
            resources={r"/*": {"origins": ALLOWED_ORIGIN}},
            supports_credentials=True
        )
        logger.info("CORS configured successfully")
    
    def _register_blueprints(self):
        """Register all Flask blueprints."""
        
        for bp, url_prefix in blueprints:
            try:
                self.app.register_blueprint(bp, url_prefix=url_prefix)
                logger.info(f"Blueprint registered: {url_prefix}")
            except Exception as e:
                logger.error(f"Failed to register blueprint {url_prefix}: {e}")
    
    def _configure_jinja(self):
        """Configure Jinja template engine."""
        self.app.jinja_env.variable_start_string = "[["
        self.app.jinja_env.variable_end_string = "]]"
    
    def _register_error_handlers(self):
        """Register error handlers for the application."""
        @self.app.errorhandler(404)
        def page_not_found(e):
            return jsonify({"error": "Page not found"}), 404
        
        @self.app.errorhandler(500)
        def internal_error(e):
            logger.error(f"Internal server error: {e}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500
    
    def register_uri_scheme(self):
        """Register custom URI scheme for Windows."""
        if sys.platform != "win32":
            logger.warning("URI scheme registration is only supported on Windows")
            return
        
        try:
            key_path = r"Software\Classes\toolasfy\shell\open\command"
            
            # Check if URI scheme is already registered
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    existing_value, _ = winreg.QueryValueEx(key, "")
                    if Settings.current_version in existing_value:
                        logger.info("URI scheme already registered")
                        return
            except FileNotFoundError:
                logger.info("URI scheme not found, creating new registration")
            
            # Create new registry keys
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\toolasfy")
            winreg.SetValue(key, "", winreg.REG_SZ, "URL:toolasfy Protocol")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            
            command_key = winreg.CreateKey(key, r"shell\open\command")
            exe_path = os.path.abspath(sys.argv[0])
            custom_exe_path = os.path.join(
                os.path.dirname(exe_path),
                Settings.current_version
            )
            
            winreg.SetValue(
                command_key,
                "",
                winreg.REG_SZ,
                f'"{custom_exe_path}" "%1"'
            )
            
            logger.info(f"Successfully registered custom protocol: toolasfy://")
            
        except PermissionError:
            logger.error("Permission denied: Run as administrator to register URI scheme")
        except Exception as e:
            logger.error(f"Failed to register URI scheme: {e}", exc_info=True)


class WSClient:
    """WebSocket client for handling real-time job dispatching."""
    
    def __init__(self, url: str = "http://127.0.0.1:2004"):
        self.url = url
        self.sio = None
        self.client_id = str(uuid.uuid4())
        self.recent_events = deque(maxlen=100)
        self.root = RootManager()
        self.name_system = self._get_system_name()
        self.is_connected = False
    
    
    def _get_system_name(self) -> str:
        """Retrieve system name from configuration."""
        try:
            return self.root.get_content_file_config('systems_name')
        except Exception as e:
            logger.error(f"Failed to get system name: {e}")
            return "unknown_system"
    
    def connect(self):
        """Initialize WebSocket connection in a separate thread."""
        thread = threading.Thread(target=self._run_socket_client, daemon=True)
        thread.start()
        logger.info(f"WebSocket client thread started with ID: {self.client_id}")
    
    def _run_socket_client(self):
        """Run the Socket.IO client with event handlers."""
        try:
            self.sio = socketio.Client(
                reconnection=True,
                reconnection_attempts=0,  # Infinite attempts
                reconnection_delay=3,
                reconnection_delay_max=30,
            )
            
            self._register_event_handlers()
            self._connect_to_server()
            
        except Exception as e:
            logger.error(f"WebSocket client error: {e}", exc_info=True)
    
    def _register_event_handlers(self):
        """Register Socket.IO event handlers."""
        @self.sio.event
        def connect():
            self.is_connected = True
            logger.info("WebSocket connected successfully")
            self.sio.emit("register_tool", {
                "client_id": self.client_id,
                "name_system": self.name_system
            })
        
        @self.sio.event
        def disconnect():
            self.is_connected = False
            logger.warning("WebSocket disconnected")
        
        @self.sio.event
        def connect_error(data):
            logger.error(f"WebSocket connection error: {data}")
        
        @self.sio.on("start-job")
        def on_start_job(data):
            self._handle_job(data)
    
    def _handle_job(self, data: dict):
        """Handle incoming job from WebSocket."""
        try:
            # Check for duplicate events
            event_id = data.get("event_id") or data.get("timestamp")
            if event_id in self.recent_events:
                logger.debug(f"Duplicate event ignored: {event_id}")
                return
            
            self.recent_events.append(event_id)
            
            # Extract job data
            job_data = data.get("data", {})
            name_system_job = data.get("name_system", "")
            
            # Validate system name
            if self.name_system != name_system_job:
                logger.debug(f"Job for different system: {name_system_job}")
                return
            
            # Extract job parameters
            job_type_id = job_data.get("job_type_id")
            
            # Dispatch job
            self._dispatch_job(job_type_id, data)
            
        except Exception as e:
            logger.error(f"Error handling job: {e}", exc_info=True)
    
    def _dispatch_job(self, job_type_id: int, data: dict):
        """Dispatch job to appropriate task handler."""
        task_class = dispatcher_config.get(job_type_id)
        
        if task_class is None:
            logger.warning(f"No task handler for job type: {job_type_id}")
            return
        
        try:
            task_instance = task_class()
            task_instance.run(data)
            logger.info(f"Job {job_type_id} executed successfully")
        except Exception as e:
            logger.error(f"Failed to execute job {job_type_id}: {e}", exc_info=True)
    
    def _connect_to_server(self):
        """Connect to the WebSocket server."""
        try:
            self.sio.connect(
                "https://socket.htvtonghop.com",
                transports=["websocket"],
                headers={
                    "Origin": "http://127.0.0.1:2004",
                    "Client-ID": self.client_id
                },
                wait=True,
                wait_timeout=10,
            )
            logger.info("Connected to WebSocket server")
            self.sio.wait()
        except Exception as e:
            logger.error(f"Connection failed: {e}", exc_info=True)
