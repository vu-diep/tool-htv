import os
import json
from time import sleep
import shutil
from playwright.sync_api import sync_playwright, BrowserContext, Browser, Page
from typing import Optional
from playwright.sync_api import Page, Locator, TimeoutError
import logging
import requests
from fake_useragent import UserAgent
import requests
import time, locale
import random
from user_agents import parse
import platform
import urllib.parse


from utils.root import RootManager
from config.settings import Settings
from network.api.servers.profiles import Profiles

class GetInfoProfile:
    def __init__(self, profile):
        self.profile = profile
        self.data = profile.get('data', {})
        self.neccessary = profile.get('data', {}).get('neccessary', {})
        self.location = profile.get('data', {}).get('location', {})
        self.advanced = profile.get('data', {}).get('advanced', {})
        self.dataCustoms = profile.get('dataCustoms', {})
        self.proxy = profile.get('proxy', {})
        self.proxyInfo = self.getProxyInfo()
        self.dataCustoms['proxy_info'] = self.proxyInfo  
        self.neccessary['user_dir'] = './tmp/profiles/'


    def get_info(self):
        fake_user_agent()
        self.fake_language()
        self.fake_timezone()
        self.fake_webRTC()
        self.fake_geo_data()
        self.fake_screen_resolution()
        self.fake_navigator()
        self.fake_media_drivers()
        self.fake_port_scan_protection()
        self.fake_webGl_gpu_metadata()
        return self.profile
    
    def fake_webGl_gpu_metadata(self):
        """Handle WebGL/GPU metadata for different platforms with randomization"""
        # Multiple GPU configs for each platform
        GPU_CONFIGS = {
            'android': [
                {
                    'device': 'Adreno (TM) 650',
                    'device_id': '0x06050000',
                    'supplier': 'Qualcomm',
                    'supplier_id': '0x4D4F4351'
                },
                {
                    'device': 'Mali-G78 MP14',
                    'device_id': '0x682',
                    'supplier': 'ARM',
                    'supplier_id': '0x13B5'
                },
                {
                    'device': 'Adreno (TM) 740',
                    'device_id': '0x06060000',
                    'supplier': 'Qualcomm',
                    'supplier_id': '0x4D4F4351'
                }
            ],
            'windows': [
                {
                    'device': 'NVIDIA GeForce GTX 1650',
                    'device_id': '0x1F82',
                    'supplier': 'NVIDIA',
                    'supplier_id': '0x10DE'
                },
                {
                    'device': 'NVIDIA GeForce RTX 3060',
                    'device_id': '0x2504',
                    'supplier': 'NVIDIA',
                    'supplier_id': '0x10DE'
                },
                {
                    'device': 'AMD Radeon RX 6600',
                    'device_id': '0x73FF',
                    'supplier': 'AMD',
                    'supplier_id': '0x1002'
                }
            ],
            'linux': [
                {
                    'device': 'AMD Radeon RX 580',
                    'device_id': '0x67DF',
                    'supplier': 'AMD',
                    'supplier_id': '0x1002'
                },
                {
                    'device': 'NVIDIA GeForce GTX 1660',
                    'device_id': '0x2184',
                    'supplier': 'NVIDIA',
                    'supplier_id': '0x10DE'
                }
            ],
            'macos': [
                {
                    'device': 'Apple M1',
                    'device_id': '0x00008200',
                    'supplier': 'Apple',
                    'supplier_id': '0x4C505041'
                },
                {
                    'device': 'Apple M2',
                    'device_id': '0x00008300',
                    'supplier': 'Apple',
                    'supplier_id': '0x4C505041'
                }
            ]
        }
        def get_random_gpu(os_type, profile_id):
            """Get consistent but random GPU for a profile"""
            gpus = GPU_CONFIGS.get(os_type, GPU_CONFIGS['windows'])
            # Use profile ID as seed for consistent selection
            seed = sum(ord(c) for c in str(profile_id))
            random.seed(seed)
            return random.choice(gpus)
        if self.advanced.get('webGlGpuMetadata') == "hidden":
            # Detect platform from user agent
            ua = self.neccessary.get('user_agent', '').lower()
            profile_id = self.profile.get('id', '')
            if 'android' in ua:
                os_type = 'android'
            elif 'macintosh' in ua or 'mac os' in ua:
                os_type = 'macos'
            elif 'linux' in ua:
                os_type = 'linux'
            else:
                os_type = 'windows'
            # Get random but consistent GPU for this profile
            self.dataCustoms['webGlGpuMetadata'] = get_random_gpu(os_type, profile_id)

    def fake_port_scan_protection(self):
        """Save port scan protection settings"""
        if self.advanced.get('portScanProtected') == "hidden":
            self.dataCustoms['portScanProtected'] = '21,22,23,25,80,443,3306,5432'

    def fake_media_drivers(self):
        """Fake media devices based on device type and mode"""
        
        if self.advanced.get('mediaDrivers') == "custom":
            # Lấy cấu hình từ custom settings
            media_config = self.dataCustoms.get('mediaDrivers', {})
            self.dataCustoms['mediaDrivers'] = {
                'audioInput': media_config.get('audioInput', 1),  # Mic
                'videoInput': media_config.get('videoInput', 0),  # Camera  
                'audioOutput': media_config.get('audioOutput', 1)  # Speaker
            }
            
        elif self.advanced.get('mediaDrivers') == "hidden":
            # Lấy user agent để xác định loại thiết bị
            ua = self.neccessary.get('user_agent', '').lower()
            
            # Cấu hình theo loại thiết bị
            if 'android' in ua or 'mobile' in ua:
                # Mobile thường có 2 camera (trước/sau), 1 mic, 1 loa
                self.dataCustoms['mediaDrivers'] = {
                    'audioInput': 1,   # 1 mic
                    'videoInput': 2,   # 2 camera
                    'audioOutput': 1   # 1 speaker
                }
            elif 'macbook' in ua or 'macintosh' in ua:
                # Macbook có webcam, mic và loa tích hợp
                self.dataCustoms['mediaDrivers'] = {
                    'audioInput': 1,   # Built-in mic
                    'videoInput': 1,   # Built-in webcam  
                    'audioOutput': 1   # Built-in speaker
                }
            else:
                # PC/Laptop Windows thường không có camera
                self.dataCustoms['mediaDrivers'] = {
                    'audioInput': 1,   # Mic
                    'videoInput': 0,   # No camera
                    'audioOutput': 1   # Speaker
                }

    def fake_navigator(self):
        """Handle navigator properties with focus on core fingerprinting elements"""
        def get_os_config(ua):
            """Get default config based on user agent"""
            if 'android' in ua:
                return {
                    'cores': '4',
                    'oscpu': '',  # Android không có oscpu
                    'foundation': ''
                }
            elif 'linux' in ua:
                return {
                    'cores': '2',
                    'oscpu': 'Linux x86_64',
                    'foundation': ''
                }  
            elif 'macintosh' in ua or 'mac os' in ua:
                return {
                    'cores': '4',
                    'oscpu': 'Intel Mac OS X 10_15_7',
                    'foundation': ''
                }
            else:
                return {
                    'cores': '4',
                    'oscpu': 'Windows NT 10.0; Win64; x64',
                    'foundation': ''
                }

        if self.advanced['navigator'] == "custom":
            custom_nav = self.dataCustoms.get('navigator', {})
            ua = custom_nav.get('userAgent', '').lower() or self.neccessary.get('user_agent', '').lower()
            
            # Lấy config mặc định dựa trên UA
            default_config = get_os_config(ua)
            
            nav_config = {
                'userAgent': custom_nav.get('userAgent') or self.neccessary.get('user_agent'),
                'hardwareConcurrency': custom_nav.get('hardwareConcurrency') or default_config['cores'],
                'foundation': custom_nav.get('foundation') or default_config['foundation'],
                'oscpu': custom_nav.get('oscpu') or default_config['oscpu']
            }
            self.dataCustoms['navigator'] = nav_config
        elif self.advanced['navigator'] == "hidden":
            ua = self.neccessary.get('user_agent', '').lower()
            default_config = get_os_config(ua)
            
            nav_config = {
                'userAgent': self.neccessary.get('user_agent'),
                'hardwareConcurrency': default_config['cores'],
                'foundation': default_config['foundation'], 
                'oscpu': default_config['oscpu']
            }
            self.dataCustoms['navigator'] = nav_config

    def fake_geo_data(self):
        if self.location['geoData'] == "hidden":
            self.dataCustoms['geoData'] = {
                'accuracy': self.dataCustoms['geoData']['accuracy'],
                'latitude': self.proxyInfo.get('lat', ''),   
                'longitude': self.proxyInfo.get('lon', ''),
            }
    
    def fake_screen_resolution(self):
        if self.advanced['screenResolution'] == "hidden":
            # Get OS from user agent
            ua = self.neccessary.get('user_agent', '').lower()
            # Define resolutions by OS with weights
            resolutions = {
                'windows': [
                    ("1920x1080", 30),  # FHD
                    ("1366x768", 25),   # Laptop common
                    ("2560x1440", 15),  # QHD
                    ("1536x864", 10),   # HD+
                    ("3840x2160", 5),   # 4K
                ],
                'macos': [
                    ("2560x1600", 30),  # MacBook Pro 13"
                    ("2880x1800", 25),  # MacBook Pro 15"
                    ("3456x2234", 15),  # MacBook Pro 16"
                    ("1920x1080", 10),  # External display
                    ("3024x1964", 5),   # MacBook Pro 14"
                ],
                'linux': [
                    ("1920x1080", 35),
                    ("1366x768", 25),
                    ("2560x1440", 15),
                    ("1600x900", 10),
                ],
                'android': [
                    ("412x915", 25),    # Galaxy S21
                    ("390x844", 25),    # iPhone 12
                    ("360x780", 20),    # Common Android
                    ("393x851", 15),    # Pixel
                ],
                'ios': [
                    ("390x844", 30),    # iPhone 12/13
                    ("428x926", 25),    # iPhone Max
                    ("375x812", 20),    # iPhone X/11
                    ("414x896", 15),    # iPhone Plus
                ]
            }

            # Determine OS
            if 'macintosh' in ua or 'mac os' in ua:
                os_type = 'macos'
            elif 'android' in ua:
                os_type = 'android'
            elif 'iphone' in ua or 'ipad' in ua:
                os_type = 'ios'
            elif 'linux' in ua:
                os_type = 'linux'
            else:
                os_type = 'windows'  # Default to Windows
            
            # Get resolutions for OS
            os_resolutions = resolutions.get(os_type, resolutions['windows'])
            # Select resolution based on weights
            resolutions_list, weights = zip(*os_resolutions)
            self.dataCustoms['screenResolution'] = random.choices(
                resolutions_list, 
                weights=weights, 
                k=1
            )[0]

    def fake_webRTC(self):
        self.dataCustoms['webRTC'] = self.proxyInfo.get('query', '')

    def fake_timezone(self):
        # Common Windows to IANA timezone mappings
        WINDOWS_TO_IANA = {
            "SE Asia Standard Time": "Asia/Bangkok",
            "Tokyo Standard Time": "Asia/Tokyo", 
            "China Standard Time": "Asia/Shanghai",
            "Singapore Standard Time": "Asia/Singapore",
            "Central European Standard Time": "Europe/Budapest",
            "Pacific Standard Time": "America/Los_Angeles",
            "Eastern Standard Time": "America/New_York",
            "GMT Standard Time": "Europe/London",
        }

        if self.location['timezone'] == "hidden":
            # Try proxy timezone first
            if self.proxyInfo and self.proxyInfo.get('timezone'):
                self.dataCustoms['timezone'] = self.proxyInfo['timezone']
            else:
                # Fall back to system timezone with mapping
                windows_tz = time.tzname[0]  # Get Windows timezone
                self.dataCustoms['timezone'] = WINDOWS_TO_IANA.get(windows_tz, "Asia/Bangkok")

    def fake_language(self):
        if self.location['language'] == "hidden":
            COUNTRY_LANG_MAP = {
                "US": "en-US",
                "GB": "en-GB",
                "AU": "en-AU",
                "CA": "en-CA",
                "NZ": "en-NZ",
                "VN": "vi-VN",
                "FR": "fr-FR",
                "BE": "fr-BE",
                "CH": "fr-CH",
                "JP": "ja-JP",
                "KR": "ko-KR",
                "CN": "zh-CN",
                "TW": "zh-TW",
                "HK": "zh-HK",
                "DE": "de-DE",
                "AT": "de-AT",
                "CH": "de-CH",
                "IT": "it-IT",
                "ES": "es-ES",
                "MX": "es-MX",
                "AR": "es-AR",
                "CL": "es-CL",
                "BR": "pt-BR",
                "PT": "pt-PT",
                "RU": "ru-RU",
                "UA": "uk-UA",
                "PL": "pl-PL",
                "NL": "nl-NL",
                "SE": "sv-SE",
                "NO": "no-NO",
                "FI": "fi-FI",
                "DK": "da-DK",
                "CZ": "cs-CZ",
                "SK": "sk-SK",
                "HU": "hu-HU",
                "TR": "tr-TR",
                "TH": "th-TH",
                "ID": "id-ID",
                "MY": "ms-MY",
                "PH": "en-PH",
                "IL": "he-IL",
                "SA": "ar-SA",
                "AE": "ar-AE",
                "IR": "fa-IR",
                "EG": "ar-EG",
                "ZA": "en-ZA",
                "NG": "en-NG",
                "PK": "ur-PK",
                "IN": "hi-IN",
                "BD": "bn-BD",
                "LK": "si-LK",
            }
            default_lang = locale.getdefaultlocale()[0].replace('_', '-')
            country_code = self.proxyInfo.get("countryCode")
            self.dataCustoms['language'] = (
                COUNTRY_LANG_MAP.get(country_code.upper()) if country_code 
                else default_lang or "en-US"
            )

    def fake_user_agent(self):
        if self.advanced.get('userAgent') == "custom":
            custom_ua = self.dataCustoms.get('userAgent')
            if custom_ua:
                self.neccessary['user_agent'] = custom_ua
                return
        
        os = self.neccessary.get('os')
        response_fake_user_agent = fake_user_agent (os)
        # Store generated UA
        self.neccessary['user_agent'] = response_fake_user_agent["user_agent"]
        self.neccessary['window_size'] = response_fake_user_agent["window_size"]
        self.neccessary['d_width'] = response_fake_user_agent["d_width"]
        self.neccessary['d_height'] = response_fake_user_agent["d_height"]
        self.neccessary['d_p_r'] = response_fake_user_agent["d_p_r"]

    def getProxyInfo(self):
        from network.api.servers.proxies import  Proxies
        type = self.neccessary['proxy']
        proxy = self.proxy
        proxies = Proxies()
        if type == 'proxy-saved':
            proxy = proxies.show(proxy.get('id'))
            if not proxy:
                return {}
        elif type == 'proxy-custom':
            proxy['ip'] = proxy.get('host')
        else:
            return {}
        try:
            proxy_request = {
                "http": f"http://{proxy['user']}:{proxy['pass']}@{proxy['ip']}:{proxy['port']}",
                "https": f"http://{proxy['user']}:{proxy['pass']}@{proxy['ip']}:{proxy['port']}"
            }
            res = requests.get("http://ip-api.com/json/", proxies=proxy_request, timeout=5)
            res.raise_for_status()
            return res.json()
        except:
            return {}
        
def fake_user_agent(os):
    """
    Tạo User Agent ngẫu nhiên và thông tin màn hình dựa trên hệ điều hành.

    Args:
        os (str): Hệ điều hành (windows, macos, linux, android, không phân biệt hoa/thường).

    Returns:
        dict: Dictionary chứa window_size, d_width, d_height, d_p_r, user_agent.

    Raises:
        ValueError: Nếu os không hợp lệ.
    """
    # Chuẩn hóa os thành chữ thường
    os_input = os.lower().strip()

    # Ánh xạ hệ điều hành không phân biệt hoa/thường
    getOs = {
        'windows': 'Windows',
        'macos': 'Mac OS X',
        'linux': 'Linux',
        'android': 'Android',
    }
    if( os_input == 'dyamic'):
        system = platform.system()
        os_input = system.lower().strip()
    # Kiểm tra xem os có hợp lệ không
    if os_input not in getOs:
        raise ValueError(f"Hệ điều hành '{os}' không hỗ trợ. Vui lòng chọn: {list(getOs.keys())}")

    # Lấy tên hệ điều hành chuẩn
    os_normalized = getOs[os_input]

    # Danh sách trình duyệt theo hệ điều hành
    browsers_by_os = {
        'Windows': ['Chrome', 'Edge', 'Firefox'],
        'Mac OS X': ['Safari', 'Chrome', 'Firefox'],
        'Linux': ['Firefox', 'Chrome'],
        'Android': ['Chrome Mobile', 'Samsung Internet', 'Firefox Mobile'],
    }

    # Lấy trình duyệt và nền tảng
    browsers = browsers_by_os[os_normalized]
    platforms = 'mobile' if os_normalized == 'Android' else 'desktop'

    # Danh sách độ phân giải và tỷ lệ pixel cho các hệ điều hành
    resolution_map = {
        "generic_android": [
            (360, 640, 1.5),    # thiết bị bình thường
            (480, 800, 1.5),    # WVGA (các thiết bị cũ)
            (720, 1280, 2.0),   # HD
            (1080, 1920, 3.0),  # Full HD
            (1080, 2400, 2.5),  # Full HD+ (18:9, 20:9)
        ],
        "generic_windows": [
            (1920, 1080, 1.5),  # Full HD
        ],
        "generic_mac_os_x": [
            (1920, 1200, 1.5),  # MacBook Pro (non-Retina)
        ],
        "generic_linux": [
            (1920, 1080, 1.5),  # Full HD
        ],
        # Ánh xạ cho các model cụ thể (Android)
        "SM-G960": [(1080, 1920, 3.0)],  # Samsung Galaxy S9
        "SM-G998": [(1440, 3200, 3.5)],  # Samsung Galaxy S21 Ultra
        "Pixel 4": [(1080, 2280, 2.5)],  # Google Pixel 4
        "Pixel 7 Pro": [(1440, 3120, 3.5)],  # Google Pixel 7 Pro
    }

    try:
        # Khởi tạo UserAgent
        ua = UserAgent(os=os_normalized, browsers=browsers, platforms=platforms)
        user_agent = ua.random

        # Phân tích User Agent
        ua_parsed = parse(user_agent)

        # Lấy model thiết bị (nếu có) hoặc dùng generic
        device_model = ua_parsed.device.model if ua_parsed.device.model else f"generic_{os_normalized.lower().replace(' ', '_')}"
        resolutions = resolution_map.get(device_model, resolution_map[f"generic_{os_normalized.lower().replace(' ', '_')}"])

        # Chọn ngẫu nhiên một độ phân giải
        d_width, d_height, d_p_r = random.choice(resolutions)

        # Tính window_size (80-100% kích thước màn hình)
        window_width = random.randint(int(d_width * 0.8), d_width)
        window_height = random.randint(int(d_height * 0.8), d_height)
        window_size = f"{window_width},{window_height}"

        return {
            "window_size": window_size,
            "d_width": d_width,
            "d_height": d_height,
            "d_p_r": d_p_r,
            "user_agent": user_agent,
        }
    except Exception as e:
        raise Exception(f"Lỗi khi tạo User Agent: {e}")

class ChromeManager:
    """Manages Playwright browser creation and configuration with profile support."""

    def __init__(self, use_extension=True):
        self.root = RootManager()
        self.root_url = self.root.get_root()
        self.config = self.root.get_content_file_config() or {}
        self.driver_config = self.config.get("driver", {})
        self.use_extension = use_extension
        self.os_type_mobile = False
        self.os_type_web = True
        self.playwright = None
        self.browser = None
        self.profiles = Profiles()

    def create_browser(
        self,
        profile=None,
        headless=None,
        startUrl=True,
        incognito=False,
        custom_options={}
    ):
        """Main method to create and configure Playwright browser."""
        print("Bat dau tao trinh duyet Playwright")
        
        headless = self._get_headless_setting(headless)
        
        # Khởi tạo playwright
        self.playwright = sync_playwright().start()
        
        if not profile:
            return self._create_simple_browser(headless, custom_options)
        
        os_type = profile.get("os", "windows").lower()
        self.os_type_mobile = os_type in ["android", "ios"]
        self.os_type_web = os_type in ["windows", "macos", "dynamic"]
        
        return self._create_profile_based_browser(
            profile, headless, startUrl, incognito, custom_options
        )

    def _get_headless_setting(self, headless):
        """Determine headless setting from parameter or config."""
        if headless is not None:
            return headless
        return self.driver_config.get("headless", "false") == "true"

    def _create_simple_browser(self, headless, custom_options):
        """Create browser without profile configuration."""
        ua = self._build_user_agent()
        
        browser_type = self.playwright.chromium
        
        launch_options = {
            "headless": headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        }
        launch_options.update(custom_options)
        
        self.browser = browser_type.launch(**launch_options)
        context = self.browser.new_context(
            user_agent=ua["agent"],
            viewport={
                "width": ua["d_width"],
                "height": ua["d_height"]
            },
            device_scale_factor=ua["d_p_r"]
        )
        
        page = context.new_page()
        return {"browser": self.browser, "context": context, "page": page}

    def _create_profile_based_browser(
        self, profile, headless, startUrl, incognito, custom_options
    ):
        """Create browser with profile-based configuration."""
        
        # Xác định browser type
        browser_type = self.playwright.chromium
        # Build launch options
        launch_options = self._build_launch_options(
            profile, headless, custom_options
        )
        
        # Build context options
        context_options = self._build_context_options(profile, incognito)
        
        try:
            self.delete_section_profile(profile)
            
            # Create context
            if profile.get("user_dir") and not incognito:
                user_data_dir = os.path.join(self.root_url, profile["user_dir"])
                os.makedirs(user_data_dir, exist_ok=True)

                context = browser_type.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=headless,
                    args=launch_options["args"],
                    executable_path=launch_options.get("executable_path"),
                    proxy=launch_options.get("proxy"),
                )

                self.browser = context.browser
                page = context.pages[0] if context.pages else context.new_page()
            else:
                self.browser = browser_type.launch(**launch_options)
                context = self.browser.new_context(**context_options)
                page = context.new_page()

            # Apply fingerprinting
            os_type = profile.get("os", "windows").lower()
            self._apply_fingerprinting(page, profile, os_type)
            
            # Handle start URLs
            if startUrl:
                self._handle_start_urls(page, profile)
            
            # Set title
            profile_name = profile.get("name", "Unknown")
            self.add_title(title=f"HTV-{profile_name}", page=page)
            
            return {"browser": self.browser, "context": context, "page": page}
            
        except Exception as e:
            print(f"[ERROR] Failed to create browser: {e}")
            self.quit()
            raise

    def _build_launch_options(self, profile, headless, custom_options):
        """Build browser launch options."""
        binary_location = self.root.get_full_url_user(Settings.chromium_path)
        
        launch_options = {
            "headless": headless,
            "executable_path": binary_location if os.path.exists(binary_location) else None,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        }
        
        # Add extension if needed
        if self.use_extension:
            extension_path = self.root.get_full_url_user(Settings.extention_omocapcha_path)
            if os.path.exists(extension_path):
                launch_options["args"].append(f"--load-extension={extension_path}")
                launch_options["args"].append("--disable-extensions-except=" + extension_path)
        
        # Add proxy if configured
        proxy = profile.get("proxy")
        if proxy and all(proxy.get(k) for k in ("ip", "port", "user", "pass")):
            launch_options["proxy"] = {
                "server": f"http://{proxy['ip']}:{proxy['port']}",
                "username": proxy["user"],
                "password": proxy["pass"]
            }
        
        launch_options.update(custom_options)
        return launch_options

    def _build_context_options(self, profile, incognito):
        """Build browser context options."""
        # Configure user agent
        if profile.get("user_agent"):
            ua_data = {
                "agent": profile["user_agent"],
                "d_width": profile.get("d_width"),
                "d_height": profile.get("d_height"),
                "d_p_r": profile.get("d_p_r")
            }
            
            # Update missing fields
            if not all([ua_data["d_width"], ua_data["d_height"], ua_data["d_p_r"]]):
                ua = self._build_user_agent(profile)
                updated_fields = {}
                
                for key in ["d_width", "d_height", "d_p_r"]:
                    if ua_data.get(key) is None:
                        ua_data[key] = ua[key]
                        updated_fields[key] = ua[key]
                
                if updated_fields:
                    self.profiles.update(profile.get("id"), updated_fields)
        else:
            ua = self._build_user_agent(profile)
            ua_data = ua
            self.profiles.update(profile.get("id"), ua)
        
        context_options = {
            "user_agent": ua_data["agent"],
            "viewport": {
                "width": ua_data["d_width"],
                "height": ua_data["d_height"]
            },
            "device_scale_factor": ua_data["d_p_r"],
            "locale": "en-US",
            "timezone_id": profile.get("customs", {}).get("timezone", "America/Los_Angeles")
        }
        
        # Mobile configuration
        os_type = profile.get("os", "windows").lower()
        if os_type in ["android", "ios"]:
            context_options["is_mobile"] = True
            context_options["has_touch"] = True
        
        # Geolocation if needed
        geolocation = profile.get("geolocation")
        if geolocation:
            context_options["geolocation"] = {
                "latitude": geolocation.get("latitude", 0),
                "longitude": geolocation.get("longitude", 0)
            }
            context_options["permissions"] = ["geolocation"]
        
        return context_options

    def _build_user_agent(self, profile=None):
        """Build user agent configuration."""
        os_type = (
            profile.get("os", "windows").lower() if profile is not None else "windows"
        )
        ua = fake_user_agent(os_type)
        return {
            "agent": ua["user_agent"],
            "window_size": ua["window_size"],
            "d_width": ua["d_width"],
            "d_height": ua["d_height"],
            "d_p_r": ua["d_p_r"],
        }
    def _apply_fingerprinting(self, page, profile, os_type):
        """Apply browser fingerprinting based on profile settings."""
        
        def get_custom_value(key, default=None):
            return profile.get("customs", {}).get(key, default)

        # Dynamic OS handling
        if os_type == "dynamic":
            return

        # OS specific configurations
        os_configs = {
            "windows": {
                "platform": "Win32",
                "oscpu": "Windows NT 10.0; Win64; x64",
                "vendor": "Google Inc.",
                "renderer": "ANGLE (NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
                "device": "NVIDIA GeForce RTX 3060",
                "hardware_concurrency": 8,
                "device_memory": 8,
                "fonts": ["Arial", "Times New Roman", "Courier New"],
                "color_depth": 24,
            },
            "macos": {
                "platform": "MacIntel",
                "oscpu": "Intel Mac OS X 10_15_7",
                "vendor": "Apple Inc.",
                "renderer": "Apple M1",
                "device": "Apple M1",
                "hardware_concurrency": 8,
                "device_memory": 8,
                "fonts": ["Helvetica", ".AppleSystemUIFont", "San Francisco"],
                "color_depth": 30,
            },
            "linux": {
                "platform": "Linux x86_64",
                "oscpu": "Linux x86_64",
                "vendor": "Google Inc.",
                "renderer": "ANGLE (Intel Mesa Intel(R) UHD Graphics 630 (CML GT2))",
                "device": "Intel UHD Graphics 630",
                "hardware_concurrency": 4,
                "device_memory": 4,
                "fonts": ["DejaVu Sans", "FreeSans", "Liberation Sans"],
                "color_depth": 24,
            },
        }

        os_config = os_configs.get(os_type, os_configs["windows"])
        js_patches = []

        # Disable Automation Flags
        js_patches.insert(
            0,
            """
            // Disable automation flags
            window.navigator.chrome = {
                runtime: {},
            };
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """,
        )

        # Navigator handling
        if profile.get("navigator") in ["hidden", "custom"]:
            nav = get_custom_value("navigator", {})
            user_agent = nav.get("userAgent", profile.get("user_agent"))
            js_patches.append(
                f"""
                Object.defineProperty(navigator, 'platform', {{
                    value: '{os_config["platform"]}',
                    configurable: false
                }});
                
                Object.defineProperty(navigator, 'userAgent', {{
                    value: '{user_agent}',
                    configurable: false
                }});

                Object.defineProperty(navigator, 'vendor', {{
                    value: '{os_config["vendor"]}',
                    configurable: false
                }});

                Object.defineProperty(navigator, 'oscpu', {{
                    value: '{os_config["oscpu"]}',
                    configurable: false
                }});
                
                Object.defineProperty(navigator, 'webdriver', {{
                    get: () => false
                }});
                
                Object.defineProperty(navigator, 'hardwareConcurrency', {{
                    value: {os_config["hardware_concurrency"]},
                    configurable: false
                }});
                
                Object.defineProperty(navigator, 'deviceMemory', {{
                    value: {os_config["device_memory"]},
                    configurable: false
                }});
                """
            )

        # WebRTC handling
        if profile.get("web_rtc") in ["hidden", "custom"]:
            webrtc_ip = get_custom_value(
                "webRTC", (profile.get("proxy") or {}).get("ip", "0.0.0.0")
            )
            js_patches.append(
                f"""
                (function() {{
                    const originalRTCPeerConnection = window.RTCPeerConnection || window.webkitRTCPeerConnection;
                    window.RTCPeerConnection = function(config) {{
                        const pc = new originalRTCPeerConnection(config);
                        
                        const origAddIceCandidate = pc.addIceCandidate.bind(pc);
                        pc.addIceCandidate = function(candidate) {{
                            if (candidate && candidate.candidate) {{
                                const modifiedCandidate = candidate.candidate.replace(
                                    /(\\d{{1,3}}\\.){{3}}\\d{{1,3}}/g,
                                    '{webrtc_ip}'
                                );
                                candidate = new RTCIceCandidate({{
                                    ...candidate,
                                    candidate: modifiedCandidate
                                }});
                            }}
                            return origAddIceCandidate(candidate);
                        }};
                        
                        return pc;
                    }};
                }})();
                """
            )

        # WebGL spoofing
        if profile.get("webgl_graphics") in ["hidden", "custom"]:
            js_patches.append(
                f"""
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                    if (parameter === 37445) return '{os_config["vendor"]}';
                    if (parameter === 37446) return '{os_config["renderer"]}';
                    return getParameter.call(this, parameter);
                }};

                const getParameterWebGL2 = WebGL2RenderingContext.prototype.getParameter;
                WebGL2RenderingContext.prototype.getParameter = function(parameter) {{
                    if (parameter === 37445) return '{os_config["vendor"]}';
                    if (parameter === 37446) return '{os_config["renderer"]}';
                    return getParameterWebGL2.call(this, parameter);
                }};
                """
            )

        # Font spoofing
        if profile.get("font_data") in ["hidden", "custom"]:
            fonts = get_custom_value("fonts", os_config["fonts"])
            js_patches.append(
                f"""
                Object.defineProperty(document, 'fonts', {{
                    value: {{
                        enumerate: () => Promise.resolve({json.dumps([{'postscriptName': f} for f in fonts])})
                    }},
                    configurable: false
                }});
                """
            )

        # Screen spoofing
        if profile.get("screen_resolution") in ["hidden", "custom"]:
            js_patches.append(
                f"""
                Object.defineProperty(screen, 'colorDepth', {{
                    value: {os_config['color_depth']},
                    configurable: false
                }});
                
                Object.defineProperty(window, 'devicePixelRatio', {{
                    value: {2 if os_type == 'macos' else 1},
                    configurable: false
                }});
                """
            )

        # Timezone spoofing
        if profile.get("timezone") in ["hidden", "custom"]:
            tz = get_custom_value("timezone", "America/Los_Angeles")
            js_patches.append(
                f"""
                const originalIntl = Intl;
                Intl.DateTimeFormat = function(locales, options) {{
                    if (options && options.timeZone) {{
                        options.timeZone = '{tz}';
                    }} else if (options) {{
                        options.timeZone = '{tz}';
                    }} else {{
                        options = {{ timeZone: '{tz}' }};
                    }}
                    return new originalIntl.DateTimeFormat(locales, options);
                }};
                Object.assign(Intl, originalIntl);
                """
            )

        # Language spoofing
        if profile.get("language") in ["hidden", "custom"]:
            lang = get_custom_value("language", "en-US,en;q=0.9")
            js_patches.append(
                f"""
                Object.defineProperty(navigator, 'language', {{
                    value: '{lang.split(',')[0]}',
                    configurable: false
                }});
                
                Object.defineProperty(navigator, 'languages', {{
                    value: {json.dumps(lang.split(','))},
                    configurable: false
                }});
                """
            )

        # Audio Context spoofing
        if profile.get("audio_context") in ["hidden", "custom"]:
            js_patches.append(
                """
                const origCreateOscillator = AudioContext.prototype.createOscillator;
                AudioContext.prototype.createOscillator = function() {
                    const oscillator = origCreateOscillator.call(this);
                    const origStart = oscillator.start;
                    oscillator.start = function(...args) {
                        return origStart.apply(this, args);
                    };
                    return oscillator;
                };
                """
            )

        # Apply all patches
        if js_patches:
            script = ";".join(js_patches)
            page.add_init_script(script)

    def _handle_start_urls(self, page, profile):
        """Handle starting URLs."""
        start_url = profile.get("start_url", {})
        if not start_url.get("default"):
            return

        try:
            page.goto(start_url.get("default"))
            sleep(2)
            
            context = page.context
            for url in start_url.get("list", []):
                if url.strip():
                    try:
                        new_page = context.new_page()
                        new_page.goto(url)
                        sleep(1)
                    except:
                        continue
        except Exception as e:
            print(f"Error loading start URLs: {e}")

    def delete_section_profile(self, profile):
        """Delete session files from profile directory."""
        user_dir = profile.get("user_dir")
        if not user_dir:
            return
            
        session_files = [
            os.path.join(user_dir, "Default", "Sessions"),
            os.path.join(user_dir, "Default", "Session Storage"),
            os.path.join(user_dir, "Default", "Current Session"),
            os.path.join(user_dir, "Default", "Current Tabs"),
            os.path.join(user_dir, "Default", "Last Session"),
            os.path.join(user_dir, "Default", "Last Tabs"),
        ]

        for session_file in session_files:
            try:
                if os.path.exists(session_file):
                    if os.path.isdir(session_file):
                        shutil.rmtree(session_file)
                    else:
                        os.remove(session_file)
            except Exception as e:
                print(f"Khong the xoa {session_file}: {e}")

    def add_title(self, title, page):
        """Set custom title for the page."""
        js = f"""
        (function() {{
            function applyTitle() {{
                document.title = "{title}";
            }}
            applyTitle();
            let obs = new MutationObserver(applyTitle);
            obs.observe(document.querySelector('title'), {{ childList: true }});
        }})();
        """
        page.evaluate(js)

    def quit(self):
        """Close browser and playwright instance."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()