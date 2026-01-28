import os
from time import sleep
from typing import Optional
from playwright.sync_api import Locator, TimeoutError
import logging
import requests
import requests
import asyncio

from .chrome import ChromeManager
from .yolo_reader import YOLOReader
from utils.bot_telegram import BotTelegram


class Driver(ChromeManager):
    def __init__(
        self,
        profile=None,
        headless=None,
        startUrl=True,
        incognito=False,
        use_extension=True,
        custom_options = {}
    ):
        # gọi constructor của class cha và truyền use_extension
        super().__init__(use_extension=use_extension)
        result= self.create_browser(
            profile=profile,
            headless=headless,
            startUrl=startUrl,
            incognito=incognito,
            custom_options=custom_options
        )
        # Quản lý trình duyệt
        self.browser = result["browser"]
        # Hồ sơ trình duyệt: profile
        self.context = result["context"]
        # tab trình duyệt
        self.page = result["page"]
        self.logger = logging.getLogger(__name__)
        self.action_send_error = ""
        self.current_url = self.page.url
        self.current_page = self.page
        
    def get(self, url: str, e_wait: int = 0, driver=None):
        page = driver if driver else self.current_page   # hỗ trợ truyền page riêng nếu cần
        page.goto(url)
        if e_wait > 0:
            sleep(e_wait)
    
    def build_selector(self, query: str, type_query: str):
        if type_query == "xpath":
            q = query.strip()

            # Nếu đã có prefix xpath= → giữ nguyên
            if q.startswith("xpath="):
                return q

            # Các dạng XPath hợp lệ
            if (
                q.startswith("//")
                or q.startswith(".//")
                or q.startswith("(")
            ):
                return f"xpath={q}"

            # Fallback: coi như shorthand → thêm //
            return f"xpath=//{q}"

        elif type_query in ("css", "tag_name"):
            return query

        elif type_query == "text":
            return f"text={query}"

        elif type_query == "id":
            return f"#{query.lstrip('#')}"

        else:
            raise ValueError(f"Unsupported type_query: {type_query}")

    
    def find(
        self,
        query: str,
        type_query: str = "xpath",
        send_keys: Optional[str] = None,
        wait: int = 3000,
        parent: Optional[Locator] = None,
    ) -> Optional[Locator]:
        selector = self.build_selector(query, type_query)
        scope = parent if parent else self.current_page
        locator = scope.locator(selector).first

        try:
            scope.locator(selector).first.wait_for(timeout=wait)
        except TimeoutError:
            self.logger.warning(f"Element NOT FOUND: {query}")
            return None
        locator.scroll_into_view_if_needed()
        if not locator.is_visible():
            self.logger.warning(f"Element found but NOT visible: {query}")
            return None

        if send_keys is not None:
            locator.fill(send_keys)

        return locator


    def find_all(
        self,
        query: str,
        type_query: str = "xpath",
        wait: float = 0,
        last: bool = False,
        parent: Optional[Locator] = None,
    ):
        try:
            selector = self.build_selector(query, type_query)
            scope = parent if parent else self.current_page
            locator = scope.locator(selector)
            if type_query == "xpath" and selector.startswith(".//") and parent:
                selector = selector[1:]  # .// -> //
            # Wait element đầu tiên
            if wait > 0:
                sleep(wait)
            
            if last:
                return locator.last
            
            # Trả về list Locator
            count = locator.count()
            return [locator.nth(i) for i in range(count)]
            
        except Exception as e:
            self.logger.error(f"Find_all element error: {e}, query: {query}")
            return []
    
    def click_text(self, text, wait=0):
        xpath = f"//*[contains(text(), '{text}')]"
        try:
            ele = self.find(xpath, wait=wait)
            if ele is not None:
                ele.click()
        except Exception as e:
            print(f"Khong click dc element: {xpath}: ")
    
    def click_ok(self):
        try:
            ok_button = self.find('//*[@aria-label="OK"]')
            ok_button.click()
        except Exception as e:
            pass
    
    def new_tab(self, domain: str = None):
        new_page = self.context.new_page()
        
        if domain is not None:
            new_page.goto(domain)
            new_page.wait_for_load_state("networkidle", timeout=30000)  # tùy chọn chờ load ổn định
        
        self.current_page = new_page            # <-- quan trọng: chuyển focus sang tab mới
        return new_page
    
    def switch_to_page(self, page):
        """Chuyển tab đang làm việc sang page khác"""
        if page and not page.is_closed():
            self.current_page = page
            self.current_page.bring_to_front()  # tùy chọn - chỉ có tác dụng visual
            self.logger.info(f"Da chuyen sang tab: {self.current_page.url}")
        else:
            self.logger.warning("Không thể chuyen sang tab nay (da dong khong ton tai)")

    def switch_to_main(self):
        """Quay về tab chính ban đầu"""
        if not self.page.is_closed():
            self.switch_to_page(self.page)
            
    def send_image_error(self, content, api="upload-image-error"):
        try:
            content = self.root.config_message(message=content, action=self.action_send_error)

            self.model.headers.pop(
                "Content-Type", None
            )  # Xóa Content-Type để requests tự đặt

            # Chụp ảnh màn hình và lưu thành file
            img_path = "error.png"
            self.current_page.save_screenshot(img_path)

            # Mở file ảnh và gửi lên API
            with open(img_path, "rb") as img_file:
                files = {"image": ("error.png", img_file, "image/png")}
                data = {"content": content}

                response = requests.post(
                    url=f"{self.model.base_url}/{api}",
                    headers=self.model.headers,
                    files=files,
                    data=data,
                )
            # Kiểm tra phản hồi từ API
            if response.status_code == 200:
                print("Anh da duoc gui thanh cong.")
        except Exception as e:
            print(f"Loi xong qua trinh gui anh: {e}")

        finally:
            # Xóa file ảnh sau khi gửi
            if os.path.exists(img_path):
                os.remove(img_path)
                print("Danh da bi xoa.")
    
    def screenshot(self, path="screen.png"):
        if path == "":
            return self.current_page.screenshot(full_page=True)
        return self.current_page.screenshot(path=path, full_page=True)
    
    def click_script(self, locator, wait=0.5):
        try:
            locator.wait_for(state="visible", timeout=5000)
            locator.scroll_into_view_if_needed()
            sleep(wait)
            locator.click(force=True)
        except Exception as e:
            raise Exception(f"Lỗi click: {e}") from e
        
    def hover_element_script(self, element, wait_time=1):
        self.execute_script("""
            const element = arguments[0];
            
            element.scrollIntoView({behavior: 'smooth', block: 'center'});
            
            // Tạo và dispatch các events theo thứ tự tự nhiên
            const events = [
                'mouseenter',
                'mouseover', 
                'mousemove'
            ];
            
            events.forEach(eventType => {
                const event = new MouseEvent(eventType, {
                    bubbles: true,
                    cancelable: true,
                    view: window,
                    detail: 1,
                    screenX: 0,
                    screenY: 0,
                    clientX: element.getBoundingClientRect().left + element.offsetWidth / 2,
                    clientY: element.getBoundingClientRect().top + element.offsetHeight / 2,
                    ctrlKey: false,
                    altKey: false,
                    shiftKey: false,
                    metaKey: false,
                    button: 0,
                    relatedTarget: null
                });
                element.dispatchEvent(event);
            });
            
            // Focus vào element (một số site cần focus để hiển thị tooltip/link)
            if (element.focus) {
                element.focus();
            }
            
            // Trigger pointer events (một số framework modern dùng pointer thay vì mouse)
            const pointerOverEvent = new PointerEvent('pointerover', {
                bubbles: true,
                cancelable: true,
                view: window,
                clientX: element.getBoundingClientRect().left + element.offsetWidth / 2,
                clientY: element.getBoundingClientRect().top + element.offsetHeight / 2
            });
            element.dispatchEvent(pointerOverEvent);
            
            return true;
        """, element)
        
        sleep(wait_time)
    
    def focus_element_script(self, element, wait=0.5):
        self.current_page.execute_script("""arguments[0].scrollIntoView(true);arguments[0].focus();""", element)
        sleep(wait)
                       
       # Tạo hàm send_message để sử dụng ở nơi khác
    
    async def send_message(self, message, group):
        try:
            TOKEN = '7914192265:AAFdqhdCCRTOBWoszckui-fDrMhMu0iXWzA'
            bot_instance = BotTelegram(TOKEN)
            bot = bot_instance.createChat()
            # phân loại nhóm trước khi gửi tin nhắn
            chat_id = self.get_content_file_config('chat_telegram_id_tool_fb_success', '-1002493389024')
            if group == "check":
                chat_id = self.get_content_file_config('chat_telegram_id_tool_fb_check', '-1002448273317')
            chat_id = chat_id.strip()
            if not chat_id:
                print("Khong tim thay chat id: ", chat_id)
                return
            await bot.send_messages(message=message, chat_id=chat_id)
        except Exception as e:
            print("Loi khi gui tin nhan telegram: ",e)
            print(e)

    def send_message_telegram(self, message, group="success", action=""):
        content = self.root.config_message(message=message, action=action)
        asyncio.run(self.send_message(message=content, group=group))
    
    def execute_script(self, script, element):
        self.current_page.evaluate(script, element)
    def isClosed(self):
        return self.current_page.is_closed()
    def set_cookies(self, cookies):
        self.context.add_cookies(cookies)
    def wait_selector(self, selector, timeount):
        try:
            self.current_page.wait_for_selector(selector, timeout=timeount)
            return True
        except TimeoutError:
            self.logger.warning(f"Timeout waiting for element: {selector}")
            return False
    def click_text(
        self,
        text: str,
        wait: int = 5000,           # thời gian chờ tối đa (ms)
        exact: bool = True,         # True: khớp chính xác text, False: chứa text
        position: str = "first",    # "first" hoặc "last" (hoặc "any" để click cái đầu tiên tìm thấy)
    ):
        """
        Click vào element chứa đoạn text được cung cấp.
        
        :param text: Đoạn text cần click (ví dụ: "Đăng nhập", "Tiếp tục", "Xem thêm")
        :param wait: Thời gian chờ element xuất hiện (ms), mặc định 5000
        :param exact: True nếu phải khớp chính xác text, False nếu chỉ cần chứa text
        :param position: "first" (mặc định), "last", hoặc "any" (click cái đầu tiên)
        :return: True nếu click thành công, False nếu không tìm thấy hoặc lỗi
        """
        try:
            # Tạo locator bằng get_by_text (ưu tiên cách này vì ổn định hơn XPath)
            locator = self.current_page.get_by_text(text, exact=exact)
            
            # Chờ element xuất hiện và visible
            locator.wait_for(state="visible", timeout=wait)
            
            # Xử lý theo position
            if position == "last":
                target_locator = locator.last
            elif position == "first" or position == "any":
                target_locator = locator.first
            else:
                raise ValueError("position chỉ hỗ trợ: 'first', 'last', 'any'")

            # Kiểm tra tồn tại
            if target_locator.count() == 0:
                self.logger.warning(f"Không tìm thấy text '{text}' (exact={exact}, position={position})")
                return False

            # Scroll vào view và click an toàn
            target_locator.scroll_into_view_if_needed()
            
            # Dùng click native của Playwright
            target_locator.click()
            
            self.logger.info(f"Da click thanh cong vao text: '{text}' (position={position})")
            return True

        except TimeoutError:
            self.logger.warning(f"Timeout cho text '{text}' sau {wait}ms")
            return False
        except Exception as e:
            self.logger.error(f"Loi khi click text '{text}': {str(e)}")
            return False
        
    def scroll_mouse(
        self,
        delta_y: float = 300,       # pixel cuộn dọc mỗi lần (dương: xuống, âm: lên)
        delta_x: float = 0,         # pixel cuộn ngang (thường 0)
        times: int = 1,             # số lần cuộn (để cuộn nhiều hơn)
        delay: float = 0.3          # delay giữa các lần cuộn (giây) để giống người thật
    ):
        """
        Giả lập cuộn chuột (mouse wheel) trên trang hiện tại.
        
        :param delta_y: Pixel cuộn dọc (dương: xuống dưới, âm: lên trên)
        :param delta_x: Pixel cuộn ngang
        :param times: Số lần thực hiện cuộn
        :param delay: Thời gian chờ giữa các lần cuộn (giây)
        """
        try:
            for _ in range(times):
                self.current_page.mouse.wheel(delta_x=delta_x, delta_y=delta_y)
                if delay > 0:
                    sleep(delay)
            
            self.logger.info(f"Đã cuộn chuột: delta_y={delta_y}, times={times}")
            
        except Exception as e:
            self.logger.error(f"Lỗi khi cuộn chuột: {e}")

    def scroll_to_locator(
        self,
        locator,
        timeout: int = 5000,
    ):
        """
        Cuộn chuột từng bước cho tới khi locator xuất hiện trong viewport

        :param locator: Playwright Locator
        :param timeout: thời gian đợi tối đa
        """
        try:
            locator.scroll_into_view_if_needed(timeout=timeout)

        except Exception as e:
            self.logger.error(f"Lỗi scroll tới locator: {e}")
            return False
            
    def js_hover_and_focus(self, locator: Locator):
        try:
            locator.wait_for(state="attached", timeout=3000)

            # Hover thật
            locator.hover(force=True)

            # JS evaluate TRỰC TIẾP trên element
            locator.evaluate(
                """
                (element) => {
                    element.scrollIntoView({ behavior: 'smooth', block: 'center' });

                    const rect = element.getBoundingClientRect();
                    const x = rect.left + rect.width / 2;
                    const y = rect.top + rect.height / 2;

                    ['mouseenter', 'mouseover', 'mousemove'].forEach(type => {
                        element.dispatchEvent(new MouseEvent(type, {
                            bubbles: true,
                            cancelable: true,
                            clientX: x,
                            clientY: y
                        }));
                    });

                    ['pointerenter', 'pointerover', 'pointermove'].forEach(type => {
                        element.dispatchEvent(new PointerEvent(type, {
                            bubbles: true,
                            cancelable: true,
                            clientX: x,
                            clientY: y,
                            pointerType: 'mouse'
                        }));
                    });

                    element.focus?.({ preventScroll: true });
                    return true;
                }
                """
            )

            return True

        except Exception as e:
            print("Hover & focus error:", e)
            return False
    
    def close_modal(self, index=0, last=False, type='//*[@aria-label="Close"]'):
        try:
            modals = self.find_all(type)
            if len(modals) > index:
                if last:
                    self.click_script(modals[-1])
                else:
                    self.click_script(modals[index])
        except Exception as e:
            print(f"Loi click modal: ", e)
    
    def inner_text_js(self, locator):
        text = locator.evaluate("el => el.textContent")
        return text
    def inner_text(self, locator):
        text = locator.inner_text()
        if text is None:
            text = self.inner_text_js(locator=locator)
        return text
    def page_source(self):
        html = self.current_page.content()
        return html
    def check_dom(self, locator):
        return locator.count() > 0
    def click_mouse(self, center_x, center_y):
        self.current_page.mouse.click(center_x, center_y)
    def send_keys(self, content):
        self.current_page.keyboard.type(content, delay=60)
    
    def yolo_reader(self, model_path):
        dpr =  self.current_page.evaluate("window.devicePixelRatio")
        yolo = YOLOReader(model_path, dpr)
        return yolo
    
    def test_yolo(self, result_yolo_detect):
        self.current_page.evaluate(f"""
            const div = document.createElement('div');
            div.style.position = 'fixed';
            div.style.left = '{result_yolo_detect['x1']}px';
            div.style.top = '{result_yolo_detect['y1']}px';
            div.style.width = '{result_yolo_detect['width']}px';
            div.style.height = '{result_yolo_detect['height']}px';
            div.style.border = '3px solid red';
            div.style.zIndex = '99999';
            div.style.pointerEvents = 'none';
            document.body.appendChild(div);
        """)