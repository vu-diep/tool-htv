import requests

requests.packages.urllib3.util.connection.HAS_IPV6 = False
from time import sleep
import random
import unicodedata
import re
import traceback

from utils.root import RootManager
from vision.xpath import xpaths
import dateparser
from urllib.parse import urlparse, parse_qs


class Base(RootManager):
    # kiểm tra xem page có truy cập được hay không
    def check_not_fount_page(self, driver):
        try:
            # Kiểm tra các phần tử thông báo lỗi hoặc login form
            error_texts = [
                '//span[contains(normalize-space(.), "Go to News Feed")]',
                '//span[contains(normalize-space(.), "Sorry! Something went wrong :(")]',
                '//h2[@dir="auto"]//span[contains(normalize-space(.), "This content") and contains(., "available at the moment")]',
            ]

            for xpath in error_texts:
                if driver.find_all(xpath):
                    return True  # Nội dung không có sẵn

            # Kiểm tra nếu có form đăng nhập => không thể truy cập
            login_form = driver.find(type_query="id", query="login_form")
            action = login_form.get_attribute("action")

            expected_action = "https://www.facebook.com/login/device-based/regular/login/?login_attempt=1"
            if action != expected_action:
                return True

            return False  # Không có dấu hiệu lỗi => nội dung có sẵn

        except Exception as e:
            # print("Loi khi check fanpage: ", e)
            # Trường hợp lỗi không mong muốn, có thể log lỗi nếu cần
            return False

    def get_info_page(self, driver):
        data = {
            "like_counts": 0,
            "follow_counts": 0,
            "following_counts": 0,
            "name": "",
            "verified": 0,
            "id_facebook": self.handle_get_id_page(driver),
        }
        try:
            name = None
            data_name_errors = [
                "This site can’t be reached",
                "Facebook",
                "This browser is not supported",
                "Home",
                "Facebook is better on the app",
            ]
            for selector in xpaths.title_fanpages:
                try:
                    elem = driver.find(selector, type_query="tag_name")
                    name_page = driver.inner_text(elem).strip()
                    if name_page and name_page not in data_name_errors:
                        name = name_page
                        break
                except:
                    continue
            data["name"] = name

            try:
                verified_elements = name_page.find_all(xpaths.verify_account)
                if verified_elements:
                    data["verified"] = 1
                else:
                    data["verified"] = 0
            except:
                data["verified"] = 0

            likes = driver.find(xpaths.friends_likes, type_query = "css")
            if likes is not None:
                data["like_counts"] = driver.inner_text(likes)

            follows = driver.find(xpaths.followers, type_query = "css")
            if follows is not None:
                data["follow_counts"] = driver.inner_text(follows)

            following = driver.find(xpaths.following, type_query = "css")
            if following is not None:
                data["following_counts"] = driver.inner_text(following)

            return data
        except Exception as e:
            raise e

    def check_block_page(driver, name_fanpage, goto_profile=False):
        from time import sleep

        try:
            blocked = driver.find(
                '//span[contains(normalize-space(.), "You’re Temporarily Blocked")]'
            )

            if not blocked:
                return False

            driver.get("https://www.facebook.com/", e_wait=3)

            # nếu là chuyển hướng vào profile
            if goto_profile:
                if driver.os_type_web:
                    # không timg thấy thằng swich_page
                    switch_page = driver.find(
                        f'//a[contains(@aria-label, "{name_fanpage}")]'
                    )
                    switch_page.click()
                else:
                    # không timg thấy thằng swich_page
                    switch_page = driver.find(
                        f'//div[@role="button" and contains(@aria-label, "Go to profile")]'
                    )
                    driver.click_script(switch_page)
                sleep(10)
                return True

            if driver.os_type_web:
                btn_profile = driver.find('//div[@aria-label="Your profile"]')
                if btn_profile:
                    btn_profile.click()
                    sleep(3)

                    # không timg thấy thằng swich_page
                    switch_page = driver.find(
                        f'//div[@aria-label="Your profile" and @role="dialog"]'
                        f'//div[contains(@aria-label, "{name_fanpage}")]'
                    )
                    switch_page.click()
            else:
                btn_profile = driver.find(
                    '//div[@role="button" and @aria-label="Facebook Menu"]'
                )
                if btn_profile:
                    driver.click_script(btn_profile)
                    sleep(3)

                    # không timg thấy thằng swich_page
                    switch_page = driver.find(
                        f'//div[@role="button" and contains(@aria-label, "{name_fanpage}")]'
                    )
                    driver.click_script(switch_page)
            sleep(10)
            return True
        except Exception as e:
            print("Loi check_block_page: ", e)
            return False

    def switch_page(driver):
        flat_switch_page = False
        for xpath in xpaths.switch_page:
            switchNow = driver.find(xpath)
            if switchNow is not None:
                switchNow.click()
                flat_switch_page = True
                break
        if flat_switch_page == False:
            print("Khong tim thay xpat chuyen huong sang trang chu")
            driver.get("https://facebook.com")
        return flat_switch_page

    def random_sleep(self, max_time=50):
        """
        Tạm dừng chương trình trong khoảng thời gian ngẫu nhiên.

        Args:
            max_time (float): Thời gian nghỉ tối đa (tính theo giây).
        """
        sleep_time = self.random_seconds(1, max_time)
        sleep(sleep_time)

    def random_seconds(self, min_seconds=5, max_seconds=20):
        """
        Trả về số giây ngẫu nhiên trong khoảng từ min_seconds đến max_seconds.

        :param min_seconds: Số giây nhỏ nhất (int)
        :param max_seconds: Số giây lớn nhất (int)
        :return: Số giây ngẫu nhiên (int)
        """
        return random.randint(min_seconds, max_seconds)

    def extract_facebook_content(self, driver, modal):
        from vision.xpath import xpaths
        from vision.convert_url import ConvertUrl

        convert_url = ConvertUrl()
        try:
            self.click_see_mores(driver=driver, parent=modal)
            content_link = []
            replace_content = []
            content = None
            for xpath_content in xpaths.content:
                content = driver.find(xpath_content, parent=modal)
                if content is not None:
                    break
            if content is None:
                return "", content_link
            a_tags = driver.find_all(xpaths.a, parent=content)
            for a in a_tags:
                href = a.get_attribute("href")
                if href:
                    clean_href = convert_url.clean_facebook_url_redirect(href)
                    clean_href = convert_url.remove_params(clean_href, "fbclid")
                    text_link = a.inner_text().strip()
                    if text_link.startswith("http"):
                        content_link.append(clean_href)
                        replace_content.append(
                            {
                                "text": text_link,
                                "link": clean_href,
                            }
                        )
            contentText = content.inner_text()
            for rep in replace_content:
                contentText = contentText.replace(rep.get("text"), rep.get("link"))

            for string in xpaths.remove_string:
                contentText = contentText.replace(string, "")
            return contentText.strip(), content_link
        except Exception as e:
            print(f"Loi khi lay noi dung:", e)
            traceback.print_exc()
            return "", []

    def remove_accents(self, input_str):
        nfkd_form = unicodedata.normalize("NFKD", input_str)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

    # lấy ảnh và video
    def get_image_and_video(self, driver, modal):
        media = None
        data = {"images": [], "videos": []}
        try:
            media = driver.find(xpaths.media, parent=modal)
        except Exception:
            media = modal
        try:
            images = driver.find_all(xpaths.img, parent=media)
            for img in images:
                src = img.get_attribute("src")
                if src and src.startswith("http") and "emoji.php" not in src:
                    data["images"].append(img.get_attribute("src"))

            videos = driver.find_all(xpaths.video, parent=media)
            for video in videos:
                data["videos"].append(video.get_attribute("src"))
        except Exception as e:
            print(f"Bai viet k co anh hoac video: ", e)
            raise Exception("Bai viet k co anh hoac video")
        return data

    def convert_to_db_format(self, time_string):
        try:
            parsed_time = dateparser.parse(time_string)
            if parsed_time:
                # Định dạng lại thành dạng lưu database (YYYY-MM-DD HH:MM:SS)
                return parsed_time.strftime("%Y-%m-%d %H:%M:%S")
            return None
        except Exception as e:
            print(f"Loi khi chuyen doi thoi gian: {e}")
            return None

    def get_post_id(self, href, converTime, params="story_fbid"):
        post_id = ""
        pageLinkPost = "/posts/"
        pageLinkStory = "https://www.facebook.com/permalink.php"
        pageLinkStoryMobile = "story.php"  # thêm cho link mobile

        if (
            any(
                substring in href
                for substring in [pageLinkPost, pageLinkStory, pageLinkStoryMobile]
            )
            or converTime
        ):
            if pageLinkPost in href:
                post_id = href.replace(pageLinkPost, "").split("?")[0]
                post_id = post_id.split("/")[-1]
            elif pageLinkStory in href or pageLinkStoryMobile in href:
                parsed_url = urlparse(href)
                query_params = parse_qs(parsed_url.query)
                post_id = query_params.get(params, [None])[0]
        return post_id

    # hàm có tác dụng tìm modal
    def find_modal(self, driver):
        typeModalXpaths = [
            '//*[@role="dialog" and @aria-labelledby]',
            '//*[@aria-posinset="1"]',
        ]
        """Tìm modal theo danh sách XPath."""
        for xpath in typeModalXpaths:
            modal = driver.find(xpath)
            if modal:
                return modal
        return None

    # hàm có tác dụng lấy thời gian
    def get_time_up(self, driver, modal):
        print("Start get time up")
        try:
            as_links = driver.find_all(
                'a[role="link"][tabindex="0"]', type_query="css", parent=modal
            )

            # Kiểm tra xem bài viết có được tài trợ không
            for a in as_links:
                if not a.is_visible():
                    print("Skip: tag <a> not visible")
                    continue

                try:
                    actions_chains.move_to_element(a).perform()
                except Exception as e:
                    print(f"Skip: Cannot hover - {e}")
                    continue

                try:
                    # Try to get time from spans first
                    spans = a.find_all("span > span > span > span", type_query="css")
                    if spans:
                        content = []
                        for span in spans:
                            if (
                                not span.inner_text()
                                or span.value_of_css_property("position") == "absolute"
                            ):
                                continue
                            try:
                                order = int(span.value_of_css_property("order"))
                                text = span.inner_text().strip()
                                if text:
                                    content.append({"index": order, "text": text})
                            except ValueError:
                                continue

                        if content:
                            content.sort(key=lambda x: x["index"])
                            result_string = "".join(item["text"] for item in content)
                            print(f"Span content: {result_string}")

                            if result_string:
                                db_time = self.convert_to_db_format(result_string)
                                if db_time:
                                    print(
                                        f"Found time from spans: {result_string} => {db_time}"
                                    )
                                    return db_time

                    # Try direct text if spans failed
                    text = a.inner_text().strip()
                    if text:
                        db_time = self.convert_to_db_format(text)
                        if db_time:
                            print(f"Found time from text: {text} => {db_time}")
                            return db_time

                    # Try aria-label as last resort
                    aria = a.get_attribute("aria-label")
                    if aria:
                        db_time = self.convert_to_db_format(aria)
                        if db_time:
                            print(f"Found time from aria: {aria} => {db_time}")
                            return db_time

                except Exception as e:
                    print(f"Error processing link: {str(e)}")
                    continue

            print("No valid time found in any link")
            return None

        except Exception as e:
            print(f"Major error in get_time_up: {str(e)}")
            return None

    # hàm có tác dụng format số
    def convert_shorthand_to_number(self, value):
        """Chuyển đổi các giá trị dạng '4.2K', '1.1M' thành số nguyên. Nếu lỗi, trả về 0."""
        if not value or not isinstance(
            value, str
        ):  # Kiểm tra giá trị rỗng hoặc không phải chuỗi
            return 0

        value = value.strip()  # Loại bỏ khoảng trắng thừa

        suffixes = {
            "K": 10**3,
            "M": 10**6,
            "B": 10**9,
        }

        match = re.search(r"([\d,.]+)([KMB]?)", value, re.IGNORECASE)
        if match:
            num, suffix = match.groups()
            num = num.replace(",", "")  # Xóa dấu phẩy nếu có (vd: '1,2K' -> '12K')

            try:
                num = float(num)
                multiplier = suffixes.get(suffix.upper(), 1)
                return int(num * multiplier)
            except ValueError:
                return 0  # Trường hợp lỗi khi chuyển đổi số

        return 0  # Nếu không khớp với pattern, trả về 0

    def parse_number(self, s):
        """Chuyển chuỗi như '1.3K following' thành số"""
        s = str(s)
        match = re.search(r"([\d\.]+)([KkMm]?)", s)
        if not match:
            return 0
        num, suffix = match.groups()
        num = float(num)
        if suffix.lower() == "k":
            num *= 1_000
        elif suffix.lower() == "m":
            num *= 1_000_000
        return num

    def click_see_mores(self, driver, parent):
        try:
            seeMores = driver.find_all(xpaths.hasMore, parent=parent)
            for see in seeMores:
                try:
                    # Kiểm tra xem có thẻ <a> bên trong xem_them không
                    has_a_tag = driver.find_all("a", type_query="tag_name", parent=see)

                    if not has_a_tag:
                        see.click()
                        self.random_sleep(3)
                except Exception as e:
                    continue
        except Exception as e:
            print(f"Click see more khong thanh cong: {e}")
    
    def handle_get_id_page(self, driver):
        try:
            # Chờ thêm thời gian để JavaScript render 
            sleep(5)
            # Scroll xuống để trigger lazy loading
            driver.scroll_mouse()
            sleep(2)
            
            # Lấy page source
            source = driver.page_source()
            
            # Danh sách các pattern để tìm page_id (từ phổ biến đến hiếm)
            patterns = [
                r'"page_id":"(\d+)"',           # "page_id":"123456"
                r'"page_id":(\d+)',             # "page_id":123456
                r'page_id":"(\d+)"',            # page_id":"123456"
                r'page_id":(\d+)',              # page_id":123456
                r'"pageID":"(\d+)"',            # "pageID":"123456"
                r'"pageID":(\d+)',              # "pageID":123456
                r'"entity_id":"(\d+)"',         # "entity_id":"123456"
                r'"entity_id":(\d+)',           # "entity_id":123456
                r'"profile_id":"(\d+)"',        # "profile_id":"123456"
                r'"profile_id":(\d+)',          # "profile_id":123456
                r',"id":"(\d+)","page_id"',     # ,"id":"xxx","page_id" (lấy id trước page_id)
                r'"id":"(\d{15,})"',            # ID dài hơn 15 số (thường là page/profile id)
            ]
            
            # Thử từng pattern
            for i, pattern in enumerate(patterns):
                matches = re.findall(pattern, source)
                if matches:
                    # Lấy giá trị xuất hiện nhiều nhất (có thể là page_id chính)
                    from collections import Counter
                    most_common = Counter(matches).most_common(1)[0][0]
                    return most_common
            
            meta_patterns = [
                r'<meta[^>]+property="al:android:url"[^>]+content="fb://page/(\d+)"',
                r'<meta[^>]+property="al:ios:url"[^>]+content="fb://page/(\d+)"',
            ]
            
            for pattern in meta_patterns:
                match = re.search(pattern, source)
                if match:
                    return match.group(1)
            
            long_ids = re.findall(r'\b(\d{15,16})\b', source)
            if long_ids:
                from collections import Counter
                most_common_id = Counter(long_ids).most_common(1)[0][0]
                return most_common_id        
            return 0
            
        except Exception as e:
            print("Loi khi lay page id: ", e)
            return None
    
    def back_home(self, driver):
        if driver.os_type_mobile:
            home = driver.find(xpaths.back)
        else:
            home = driver.find(xpaths.home)
        driver.click_script(home)