from time import time, sleep
from datetime import datetime
import re
import json
import threading
import traceback

from network.api.servers.accounts import Account
from network.api.servers.pages import Pages
from network.api.servers.jobs import Jobs
from network.api.servers.histories import Histories
from network.api.servers.posts import Posts
from network.api.servers.tool_activity_log import ToolActivityLog

from .base import Base
from browser.driver import Driver
from .login import Login
from .check_point import HandleCheckpoint
from vision.convert_url import ConvertUrl

from vision.xpath import xpaths
from state.session import session_newsfeed_via


class CrawlNewsfeed(Base):
    def __init__(self, identifier, config, is_page=True):
        self.identifier = identifier
        self.config = config
        self.is_page = is_page

        self.accounts = Account()
        self.pages = Pages()
        self.jobs = Jobs()
        self.convert_url = ConvertUrl()
        self.histories = Histories()
        self.posts = Posts()

        self.start_crawl()

    def start_crawl(self):
        socket = self.config["socket"]
        try:

            # Xác định điều kiện tìm kiếm profile
            tab = self.config["tab"]
            tab = tab[self.identifier]
            name_center = self.config["name_center"]
            tool_activity_logs_id = self.config["tool_activity_logs_id"]

            account = {}
            datas = {
                "time_start": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "time_end": None,
            }
            if self.is_page == False:
                data = self.accounts.show(id=self.identifier)
                account = data
                datas["status_login"] = 3
            else:
                data = self.pages.show(id=self.identifier)
                account = data["account"]
                datas["status"] = 2
            profile = account["profile"]
            if profile == None:
                socket(
                    id=self.identifier,
                    message="Tài khoản không có profile vui lòng kiểm tra lại",
                    tool_activity_logs_id=tool_activity_logs_id,
                    status=1,
                )
                return

            idProfile = profile.get("id")
            new_file_name = f"{self.identifier}{name_center}{idProfile}"
            profile["user_dir"] = "./tmp/profiles/" + new_file_name

            # Xác định thông tin cập nhật
            time_run_sql = data.get("time_run")
            time_sleep_sql = data.get("time_sleep")
            # Cập nhật thời gian bắt đầu
            update_entity = self.pages if self.is_page else self.accounts

            update_entity.update(id=self.identifier, data=datas)
            response_update_entity = update_entity.show(self.identifier)
            number_interactions = response_update_entity.get("number_interactions")

            # cập nhật thêm cấu hình trước cho hàm handle_craw
            self.config.update(
                {
                    "id": self.identifier,
                    "tab": tab,
                    "time_run_sql": time_run_sql,
                    "time_sleep_sql": time_sleep_sql,
                    "profile": profile,
                    "craw_panpage": self.is_page,
                    "account": account,
                    "number_interactions": number_interactions,
                    "page": data,
                }
            )
            self.handle_crawl()
        except Exception as e:
            socket(
                id=self.identifier,
                message="Lỗi không xác định vui lòng gọi IT",
                tool_activity_logs_id=tool_activity_logs_id,
                status=0,
            )
            print(f"Loi khi bat dau chay newsfeed: {e}")
            raise Exception("Loi khong xac dinh vui long goi IT")

    def handle_crawl(self):
        # Đưa các cấu hình từ config ra thành biến để tiện sử dụng
        search = self.config["search"]
        # search = True
        filter_keyword = self.config["filter_keyword"]
        keyword = self.config["keyword"]
        socket = self.config["socket"]
        id = self.config["id"]
        tab = self.config["tab"]
        job_id = self.config["jobs_id"]
        tool_activity_logs_id = self.config["tool_activity_logs_id"]
        time_run_sql = int(self.config["time_run_sql"])
        time_sleep_sql = int(self.config["time_sleep_sql"])
        profile = self.config["profile"]
        craw_panpage = self.config["craw_panpage"]
        account = self.config["account"]
        page = self.config["page"]
        root = self.config["root"]

        name_fanpage = page.get("name")
        driver = None
        # lấy ra danh sách các page không được cào dữ liệu
        list_link_page_not_crawl = self.get_page_not_crawl()

        stop_event = tab["stop_event"]
        socket(
            id=id,
            message="Bắt đầu khởi tạo trình duyệt",
            tool_activity_logs_id=tool_activity_logs_id,
            status=0,
        )
        # đổi sang giây
        time_run = time_run_sql * 3600
        if time_run == 0:
            socket(
                id=id,
                message="Thời gian chạy không thể bằng 0",
                tool_activity_logs_id=tool_activity_logs_id,
                status=1,
            )
            return
        time_sleep = time_sleep_sql * 3600
        self.accounts.update(account.get("id"), {"status_login": 3})
        params = {
            "account_id": account.get("id", 0),
            "cookie_id": (
                account.get("latest_cookie")["id"]
                if account.get("latest_cookie")
                else 0
            ),
        }
        # lấy từ khóa
        sendNotiKeyword = True
        keywords = []

        # Nếu cần sử dụng keywords thì mới lấy
        if filter_keyword == True:
            while not stop_event.is_set():
                keywords = self.accounts.get_keywords(account.get("id"), True)
                if len(keywords) != 0:
                    break
                if sendNotiKeyword:
                    message = "Chưa chọn từ khóa lấy bài viết"
                    socket(
                        id=id,
                        message=message,
                        tool_activity_logs_id=tool_activity_logs_id,
                        status=0,
                    )
                    self.send_message_telegram(
                        f"Tài khoản {account['name']} {message}",
                        group="check",
                        action=root,
                    )
                    print("Chua chon tu khoa lay bai viet")
                    sendNotiKeyword = False

        try:
            if account is None:
                socket(
                    id=id,
                    message="Chưa chọn tài khoản lấy bài viết",
                    tool_activity_logs_id=tool_activity_logs_id,
                    status=1,
                )
                raise Exception("Chua chon tai khoan lay bai viet")
            socket(
                id=id,
                message="Đang khởi tạo trình duyệt....",
                tool_activity_logs_id=tool_activity_logs_id,
                status=2,
            )

            driver = Driver(profile, startUrl=False)  # Khởi tạo trình duyệt với profile
            # đánh dấu số lần upload profile lên server
            while not stop_event.is_set():
                start_time = time()
                self.config["start_time"] = start_time
                self.config["time_run"] = time_run
                # theo dõi vị trí các từ khóa trong mảng keywords
                indexKeywords = 0
                if driver.isClosed():  # Nếu bị đóng thì tự khởi động lại
                    print("Trinh duyet bi dong khoi dong lai: ")
                    driver = Driver(profile, startUrl=False)

                # xác định thời gian chạy và thời gian ngủ
                # đánh dấu số lần thử login lại
                driver.action_send_error = root
                while time() - start_time < time_run and not stop_event.is_set():
                    tab["check"] = 1
                    tab["status_process"] = 1
                    if (
                        driver is None or driver.isClosed()
                    ):  # Nếu bị đóng thì tự khởi động lại
                        print("Trinh duyet da bi dong: ", driver)
                        driver = Driver(profile, startUrl=False)
                    if profile is None or account is None:
                        raise ValueError("Khong the lay thong tin profile hoac account")
                    socket(
                        id=id,
                        message="Đã khởi tạo trình duyệt",
                        tool_activity_logs_id=tool_activity_logs_id,
                        status=1,
                    )
                    try:
                        socket(
                            id=id,
                            message="Đang chuyển hướng Facebook...",
                            tool_activity_logs_id=tool_activity_logs_id,
                            status=1,
                        )
                        driver.get("https://facebook.com", e_wait=5)
                        # kiểm tra xem có đã đăng nhập hay chưa
                        login = Login(driver, account)
                        if not login.handle_login():
                            socket(
                                id=id,
                                message="Không thể đăng nhập",
                                tool_activity_logs_id=tool_activity_logs_id,
                                status=1,
                            )
                            raise Exception("Khong the dang nhap")

                        socket(
                            id=id,
                            message="Đăng nhập thành công...",
                            tool_activity_logs_id=tool_activity_logs_id,
                            status=1,
                        )
                        print("Da dang nhap thanh cong")

                        self.accounts.update(account.get("id"), {"status_login": 3})
                        name_page = ""
                        comments = []
                        # nếu là fanpage thì lấy ra thông tin fanpage
                        if craw_panpage:
                            comments = page.get("comments")
                            link = page.get("link")

                            # Kiểm tra link phải là link của fanpage Facebook
                            if link and link.startswith("https://www.facebook.com/"):
                                driver.get(link, e_wait=3)
                                page_exists = self.check_not_fount_page(driver)
                                # kiểm tra đường link có hợp lệ không, nếu khong hợp lệ thì thông báo và chyển hướng về trang chủ
                                if page_exists:
                                    message = f"Đường dẫn fanpage không thể truy cập.\nTên fanpage: {page.get('name')}\nLink kiểm tra: {link}\nVui lòng kiểm tra và cập nhật lại đường dẫn."
                                    socket(
                                        id=id,
                                        message=message,
                                        tool_activity_logs_id=tool_activity_logs_id,
                                        status=0,
                                    )
                                    driver.get("https://facebook.com", e_wait=3)
                                    self.send_message_telegram(
                                        message, group="check", action=root
                                    )

                                socket(
                                    id=id,
                                    message=f'Đăng nhập thành công, đang xử lý fanpage: {page.get("name")}',
                                    tool_activity_logs_id=tool_activity_logs_id,
                                    status=1,
                                )
                                try:
                                    name_page = self.get_info_page(driver)
                                except Exception as e:
                                    socket(
                                        id=id,
                                        message="Lấy thông tin fanpage thất bại",
                                        tool_activity_logs_id=tool_activity_logs_id,
                                        status=1,
                                    )
                                    print(e)

                                page["name"] = name_page.strip()
                                if self.check_block_page(driver, name_fanpage) == False:
                                    self.switch_page(driver)  # Chuyển hướng tới fanpage
                            else:
                                driver.send_message_telegram(
                                    f"Đường link không hợp lệ cho fanpage {page.get('name')}: {link}",
                                    group="check",
                                    action=root,
                                )
                                socket(
                                    id=id,
                                    message=f"Bỏ qua link không hợp lệ cho fanpage: {link}",
                                    tool_activity_logs_id=tool_activity_logs_id,
                                    status=1,
                                )
                        else:
                            socket(
                                id=id,
                                message=f'Đăng nhập thành công, đang xử lý tài khoản {account.get("name")}',
                                tool_activity_logs_id=tool_activity_logs_id,
                                status=1,
                            )

                        print("Dang chuyen huong Facebook")
                        while (
                            time() - start_time < time_run and not stop_event.is_set()
                        ):
                            # nếu vị trí mà chưa vượt ra ngoài mảng keywords thì tiếp tục lấy keyword tại vị trí hiện tại
                            if indexKeywords < len(keywords) and search == True:
                                keyword = keywords[indexKeywords]
                                indexKeywords += 1
                                self.render_and_search_keywords(
                                    keyword["keyword"], driver
                                )
                            else:
                                # Khi đã vượt ra ngoài rồi mà đang trong chức năng search thì reset indexKeywords về 0 để tiếp tục tìm lại từ đầu keyword
                                if search == True:
                                    indexKeywords = 0

                            socket(
                                id=id,
                                message=f"Bắt đầu lấy bài viết...",
                                tool_activity_logs_id=tool_activity_logs_id,
                                status=1,
                            )
                            try:
                                self.config["keywords"] = keywords
                                self.config["name_page"] = name_page
                                self.config["comments"] = comments
                                self.config["list_link_page_not_crawl"] = (
                                    list_link_page_not_crawl
                                )
                                self.config["params"] = params
                                driver.get("https://facebook.com", e_wait=3)
                                if driver.os_type_web:
                                    self.handle_craw_web(driver, stop_event)
                                elif driver.os_type_mobile:
                                    self.handle_craw_mobile(driver, stop_event)
                                self.random_sleep()
                                continue
                            except Exception as e:
                                print("Loi lay bai viet that bai:", e)
                                traceback.print_exc()
                                # socket(
                                #     id=id,
                                #     message=f"Lấy bài viết thất bại",
                                #     tool_activity_logs_id=tool_activity_logs_id,
                                #     status=1,
                                # )
                                # driver.send_image_error(f"Lấy bài viết thất bại: {e}")
                            break
                    except Exception as e:
                        socket(
                            id=id,
                            message=f"Proxy không hoạt động",
                            tool_activity_logs_id=tool_activity_logs_id,
                            status=1,
                        )
                        res = self.accounts.update(
                            account.get("id"), {"status_login": 6}
                        )
                        if "net::ERR_TUNNEL_CONNECTION_FAILED" in str(e):
                            print("Loi: Proxy khong the ket noi!")
                        else:
                            print(f"Loi khac xay ra: {e}")
                    except ValueError as e:
                        socket(
                            id=id,
                            message=f"Tài khoản không thể đăng nhập 30s sau sẽ thử đăng nhập lại",
                            tool_activity_logs_id=tool_activity_logs_id,
                            status=1,
                        )
                        res = self.accounts.update(
                            account.get("id"), {"status_login": 1}
                        )

                # nếu không có yêu cầu dừng tiến trình từ trình duyệt thì thực hiện ngủ theo thời gian đã sắp đặt trước
                if not stop_event.is_set():
                    if driver:
                        driver.quit()
                    # Ngủ 1 giờ trong thời gian ngủ vẫn gửi thông báo về clent
                    message = "Đang nghỉ {current} giây còn lại {total} giây. Trình duyệt đang bị đóng"
                    seconds = time_sleep
                    message_template = "Chờ {current} / {total} giây để tiếp tục"
                    for i in range(seconds, 0, -1):
                        try:
                            # Kiểm tra stop event trước khi làm bất kỳ điều gì
                            if stop_event and stop_event.is_set():
                                socket(
                                    id=id,
                                    message="Đã đừng đếm ngược",
                                    tool_activity_logs_id=tool_activity_logs_id,
                                    status=1,
                                )
                                break

                            message = message_template.format(current=i, total=seconds)
                            socket(
                                id=id,
                                message=message,
                                tool_activity_logs_id=tool_activity_logs_id,
                                status=1,
                            )
                            sleep(1)
                        except Exception as e:
                            print(f"Loi trong qua trinh dem nguoc: {e}")
                            break
                    # sau khi ngủ thì mở trình duyệt để làm việc tiếp
                    if not stop_event.is_set():
                        driver = Driver(profile, startUrl=False)

            self.jobs.update(id=job_id, data={"status": "done"})
        except Exception as e:

            socket(
                id=id,
                message=f"Đã xảy ra lỗi....",
                tool_activity_logs_id=tool_activity_logs_id,
                status=1,
            )
            if driver:
                driver.send_image_error(f"Đã có lỗi xảy ra: {e}")
            print(f"Da co loi xay ra: {e}")
            self.jobs.update(id=job_id, data={"status": "failed"})
        finally:
            check_point = HandleCheckpoint(driver)
            status, code_check = check_point.start(driver, account, root)
            if status:
                driver.send_message_telegram(
                    f"Tài khoản {account['name']} bị checkpoint {code_check} tại chức năng {root}",
                    group="check",
                    action=root,
                )

            if account and account.get("status_login") == 3:
                self.accounts.update(
                    account.get("id"), {"status_login": 2, "checkpoint": code_check}
                )
            else:
                self.accounts.update(
                    account.get("id"), {"status_login": 1, "checkpoint": code_check}
                )
            socket(
                id=id,
                message=f"Trình duyệt đang bị đóng",
                tool_activity_logs_id=tool_activity_logs_id,
                status=2,
            )
            driver.quit()
            socket(
                id=id,
                message=f"Đã dừng chương trình",
                tool_activity_logs_id=tool_activity_logs_id,
                status=0,
            )
            driver.send_message_telegram(
                f"Tài khoản {account['name']} đã dừng {root}",
                group="check",
                action=root,
            )

    # hàm có tác dụng lấy ra các page không được lấy dữ liệu
    def get_page_not_crawl(self):
        # lấy ra danh sách các page khôn được cào dữ liệu
        list_page_not_crawl = self.pages.get_all(
            {"category": "company", "page_not_crwal": "true"}
        )
        # Lấy tất cả các 'name' trong object
        list_link_page_not_crawl = [page["link"] for page in list_page_not_crawl]
        return list_link_page_not_crawl

    # Hàm có tác dụng chuyển hướng đến tìm kiếm theo từ khóa và thực hiện click vào nút lấy bài viết mới nhất
    def render_and_search_keywords(self, keyword, driver):
        try:
            if driver.os_type_mobile:
                keywordFormat = "https://www.facebook.com/search_results/?q=" + keyword
                # thực hiện chuyển hướng đến keywords
                driver.get(keywordFormat, e_wait=3)
                checkbox = driver.find('.//div[@role="button"]//span[text()="Posts"]')
            else:
                keywordFormat = "https://www.facebook.com/search/posts?q=" + keyword
                # thực hiện chuyển hướng đến keywords
                driver.get(keywordFormat, e_wait=3)
                # ấn null all để trỏ ra menu
                btn_all = driver.find('.//span[text() = "All"]')
                if btn_all:
                    btn_all.click()
                # thực hiện lọc theo bài viết gần đây
                sleep(10)
                checkbox = driver.find(
                    '//input[@aria-label="Recent posts" or @aria-label="Recent Posts"]'
                )
            # Click vào checkbox nếu tìm thấy
            if checkbox:
                print("tim thay checkbox")
                checkbox.click()
            self.random_sleep(5)
        except Exception as e:
            print(f"Loi khi chuyen huong den search: {e}")

    def handle_craw_web(self, driver, stop_event):
        socket = self.config["socket"]
        id = self.config["id"]
        account = self.config["account"]
        page = self.config["page"]
        params = self.config["params"]
        tool_activity_logs_id = self.config["tool_activity_logs_id"]

        try:
            idHistory = 0
            print("Lay danh sach link bai viet")
            socket(
                id=id,
                message=f"Lấy danh sách link bài viết",
                tool_activity_logs_id=tool_activity_logs_id,
                status=1,
            )
            sleep(20)
            print("bat dau lay duong link bai viet")
            list_articles = self.get_list_post_web(driver=driver, stop_event=stop_event)
            print("list_articles: ", json.dumps(list_articles, indent=4))
            return
            try:
                # gửi dữ liệu sau khi lấy đủ 10 bài viết
                responseAddHistory = self.histories.createNewsFeed(
                    {"account_id": account.get("id"), "counts": len(list_articles)}
                )
                socket(
                    id=id,
                    message=responseAddHistory["message"],
                    tool_activity_logs_id=tool_activity_logs_id,
                    status=1,
                )
                idHistory = responseAddHistory["id"]
            except Exception as e:
                driver.send_image_error(
                    f"Lỗi lưu khi gửi tạo history create newsfeed: {e}"
                )
                print(f"Loi khi gui tao history create newsfeed: {e}")
                socket(
                    id=id,
                    message=f"Lỗi lưu khi gửi tạo history create newsfeed: {e}",
                    tool_activity_logs_id=tool_activity_logs_id,
                    status=1,
                )
                return
            i = 0
            # lặp qua đường link chi tiết rồi lấy ra bài viết
            while i < len(list_articles) and not stop_event.is_set():
                article = list_articles[i]
                try:
                    socket(
                        id=id,
                        message=f"Đang thực hiện chuyển hướng lấy bài viết",
                        tool_activity_logs_id=tool_activity_logs_id,
                        status=1,
                    )
                    post_fb_link = article.get("post_fb_link")
                    print("Dang thuc hien chuyen huong lay bai viet: ", post_fb_link)
                    driver.get(post_fb_link, e_wait=3)

                    # kiểm tra trang web có bị lỗi không nếu lỗi thì bỏ qua
                    page_exists = self.check_not_fount_page(driver)
                    if page_exists:
                        socket(
                            id=id,
                            message=f"Bài viết không khả dụng hoặc đã bị xóa",
                            tool_activity_logs_id=tool_activity_logs_id,
                            status=1,
                        )
                        i += 1
                        self.histories.updateValidCrawlNewsFeed(idHistory, {})
                        continue
                    article = self.crawl_content_page(driver, article)
                    if article:
                        # lấy ra page vừa lấy
                        article["idHistoryCrawPage"] = idHistory
                        print("Dang gui du lieu len server")
                        socket(
                            id=id,
                            message="Đang gửi dữ liệu lên server",
                            tool_activity_logs_id=tool_activity_logs_id,
                            status=1,
                        )
                        response = self.posts.add_post_newsfeed(
                            {"data": article}, params
                        )
                        print("Da gui du lieu len server: ", response)
                        socket(id, response["message"], 1)
                    else:
                        responseUpdateHistory = self.histories.updateValidCrawlNewsFeed(
                            idHistory, {}
                        )
                        socket(
                            id=id,
                            message=responseUpdateHistory["message"],
                            tool_activity_logs_id=tool_activity_logs_id,
                            status=1,
                        )
                    i += 1
                except Exception as e:
                    content = f"Tài khoản: {account.get("name")} - Fanpage: {page.get("name")}  - Lỗi lấy bài viết: {e}"
                    driver.send_image_error(content)
                    print(f"Loi luu bai viet: {e}")
                    socket(
                        id=id,
                        message=f"Lỗi lấy bài viết vui lòng gọi IT",
                        tool_activity_logs_id=tool_activity_logs_id,
                        status=1,
                    )
            self.histories.update(idHistory, {"status": 2})
        except Exception as e:
            raise Exception(e)

    def get_list_post_web(self, driver, stop_event):
        start_time = self.config["start_time"]
        time_run = self.config["time_run"]
        get_article_friend = self.config["get_article_friend"]
        keywords = self.config["keywords"]
        filter_keyword = self.config["filter_keyword"]

        dataLink = []
        listId = set()

        limit_article = 1
        list_article = []
        list_post_id = []

        # thực hiện vòng lặp đảm bảo rằng lấy đủ limit article
        while (
            len(list_article) < limit_article
            and time() - start_time < time_run
            and not stop_event.is_set()
        ):
            list_posts = []
            # Lặp qua từng XPath cho đến khi tìm được phần tử
            for xpath in xpaths.list_posts:
                list_posts = driver.find_all(xpath)
                if list_posts:
                    break
            len_list_post = len(list_posts)
            print("len_list_post: ", len_list_post)
            print("list_article: ", len(list_article))
            for modal in list_posts:
                try:
                    # cuộn chuột đến bài post
                    modal.scroll_into_view_if_needed()
                    sleep(1)
                    # Nếu không lấy các bài viết của bạn bè
                    # if get_article_friend == False:
                    #     # chỉ lấy các bài viết có chữ follow
                    #     btn_follow = driver.find_all(xpaths.btn_follow, parent=modal)
                    #     if not btn_follow:
                    #         continue
                    # kiểm tra nếu có see more thì click vào để lấy toàn bộ nội dung
                    content, content_link = self.extract_facebook_content_web(
                        driver, modal=modal
                    )
                    print("content: ", content)
                    sleep(self.random_seconds())
                    matched_keywords = []
                    if filter_keyword:
                        normalized_content = self.remove_accents(content.lower())
                        for kw in keywords:
                            keyword_text = kw["keyword"]
                            normalized_keyword = self.remove_accents(
                                keyword_text.lower()
                            )

                            # Kiểm tra trong nội dung bài viết
                            if normalized_keyword in normalized_content:
                                matched_keywords.append(kw)
                                continue  # khỏi cần kiểm tra trong comment nữa nếu đã thấy
                        # nếu không tìm thấy keyword thì bỏ qua
                        if len(matched_keywords) == 0:
                            continue
                    # thu thập đường link
                    idAreaPost = (
                        modal.get_attribute("aria-posinset")
                        or modal.get_attribute("data-tracking-duration-id")
                        or modal.get_attribute("aria-describedby")
                        or modal.get_attribute("data-ft")
                    )
                    if idAreaPost not in listId:
                        listId.add(idAreaPost)
                        links = modal.find_all(".//a")
                        dataMedia = self.get_image_and_video(driver, modal)
                        for link in links:
                            if (
                                link.is_displayed()
                                and link.size["width"] > 0
                                and link.size["height"] > 0
                            ):
                                driver.hover_element_script(link)
                                driver.focus_element_script(link)
                                href = link.get_attribute("href")
                                if not href:
                                    print("Khong tim thay href trong link")
                                    continue
                                href = self.convert_url.clean_url_keep_params(href)
                                link_time = link.text_content().strip()
                                try:
                                    converTime = self.convert_to_db_format(link_time)
                                except:
                                    converTime = None

                                post_id = self.get_post_id(href, converTime)

                                if post_id == "" or any(
                                    d["post_fb_id"] == post_id
                                    or d["post_fb_link"] == href
                                    for d in dataLink
                                ):
                                    continue
                                if post_id in list_post_id:
                                    continue

                                list_article.append(
                                    {
                                        "post_fb_id": post_id,
                                        "post_fb_link": href,
                                        "matched_keywords": matched_keywords,
                                        "content": content,
                                        "content_link": content_link,
                                        "media": dataMedia,
                                    }
                                )
                                list_post_id.append(post_id)

                    if stop_event.is_set():
                        break
                except Exception as e:
                    print(f"Phan tu khong ton tai, tim lai phan tu: {e}")
                    continue
            driver.scroll_mouse(delta_y=500, times=5, delay=0.4)
            sleep(self.random_seconds())

        return list_article

    def crawl_content_page(self, driver, article):

        list_link_page_not_crawl = self.config["list_link_page_not_crawl"]
        number_interactions = self.config["number_interactions"]
        filter_link = self.config["filter_link"]
        keywords = self.config["keywords"]
        filter_keyword = self.config["filter_keyword"]

        data = {}
        sleep(2)
        print(f"Bat dau lay du lieu bai viet")
        modal = None

        # Sử lý lấy từng ô bài viết
        for modalXPath in xpaths.modal:
            try:
                modal = driver.find(modalXPath)
                print(f"Tim thay modal voi xpath: {modalXPath}")
                break
            except Exception as e:
                continue

        if not modal:
            print("Khong tim thay modal")
            return {}

        timeUp = self.get_time_up(driver)

        # Lấy nội dung
        content_link = article["content_link"]
        # Lưu thông tin bài viết
        data["time_up"] = timeUp
        data["post_id"] = article["post_fb_id"]
        # Lấy ảnh và video
        dataMedia = article["media"]
        if len(dataMedia["images"]) == 0 and len(dataMedia["videos"]) == 0:
            dataMedia = self.get_image_and_video(modal)
            # kiểm tra nếu có see more thì click vào để lấy toàn bộ nội dung
            content, content_link = self.extract_facebook_content_web(
                modal=modal, driver=driver
            )

            matched_keywords = []
            if filter_keyword:
                normalized_content = self.remove_accents(content.lower())
                for kw in keywords:
                    keyword_text = kw["keyword"]
                    normalized_keyword = self.remove_accents(keyword_text.lower())

                    # Kiểm tra trong nội dung bài viết
                    if normalized_keyword in normalized_content:
                        matched_keywords.append(kw)
                        continue  # khỏi cần kiểm tra trong comment nữa nếu đã thấy
                if len(matched_keywords) == 0:
                    return {}
            else:
                data["matched_keywords"] = matched_keywords
                data["content"] = content
                data["content_link"] = content_link
        else:
            data["content"] = article["content"]
            data["matched_keywords"] = article["matched_keywords"]
            data["content_link"] = content_link
        data["media"] = dataMedia
        # Lấy số lượng cảm xúc và bình luận
        numberOfReactionsAndComments = self.get_number_of_reactions_and_comments(modal)
        data["number_of_reactions"] = numberOfReactionsAndComments
        data["link_facebook"] = article["post_fb_link"]

        print("dang lay binh luan bai viet")
        # Lấy bình luận
        comments, has_link_in_comments = self.get_comments(modal, driver, article)
        # kiểm tra xem trong bài viết hoặc comment có link hay không
        if filter_link and (len(content_link) == 0 and has_link_in_comments == False):
            return {}
        data["comments"] = comments

        # Thực hiện xem chi tiết ảnh
        self.views_image(dataMedia["images"], driver, modal)
        sleep(5)

        # Lấy nguồn gốc bài viết (thực hiện sau cùng)
        sourcePost = self.get_source_post(driver, modal)
        data["source_post"] = sourcePost

        # Kiểm tra nếu sourcePost["link"] có trong list_link_page_not_crawl
        if sourcePost and sourcePost.get("link") in list_link_page_not_crawl:
            print(
                f"Source {sourcePost['link']} nam trong danh sach khong can cao, bo qua."
            )
            return {}

        like_source_post = self.parse_number(numberOfReactionsAndComments.get("like"))
        if like_source_post < number_interactions:
            print(
                f"Luot tuong tac khong du, luot tuong tac page: {like_source_post} luot tuong tac mong muon: {number_interactions}, link: {article['post_fb_link']} bo qua."
            )
            return {}

        return data

    # lấy số lượng cảm xúc và bình luận
    def get_number_of_reactions_and_comments(self, modal):
        data = {
            "comment": 0,
            "like": 0,
            "share": 0,
        }
        try:
            all_reactions = modal.find('(//div[text()="All reactions:"]/..)[last()]')
            like = all_reactions.text_content()
            like = self.convert_shorthand_to_number(like)
            data["like"] = like
        except Exception as e:
            print(f"Khong lay duoc like")
        try:
            comment_element = modal.find(
                '//div[@role="button" and @aria-expanded="true"]//span[contains(text(), "comments")]'
            )
            comment = comment_element.text_content()
            comment = self.convert_shorthand_to_number(comment)
            data["comment"] = comment
        except Exception as e:
            print(f"Khong lay duoc comments")
        try:
            shares_element = modal.find(
                '(//div[@role="button"]//span[contains(text(), "shares")])[last()]'
            )
            shares = shares_element.text_content()
            shares = self.convert_shorthand_to_number(shares)
            data["share"] = shares
        except Exception as e:
            print(f"Khong lay duoc shares")

        except Exception as e:
            print(f"Khong lay duoc like, comment, share: {e}")
        return data

    def get_comments(self, modal, driver, linkItem):
        print("Bat dau lay comment")
        data = []
        has_link_in_comments = False
        removeComment = ["·", "Author\n", "  ", "Top fan", "Follow"]
        type_element = "comments"
        if driver.os_type_mobile:
            type_element = "commentsMobile"
        try:
            scroll = driver.find(xpaths.scroll)
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight;", scroll
            )
            print("Cuon chuot xuong (tim thay element scroll)")
        except Exception as e:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print("Cuon chuot xuong bang window: ", e)
        sleep(3)

        try:
            comments = modal.find_all(getattr(xpaths, type_element))
            print(f"Tim thay {len(comments)} binh luan")
            # xu ly các phần tử "Xem thêm"
            for cm in comments:
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight;", cm
                )
                try:
                    xem_them = cm.find(xpaths.hasMore)
                    if xem_them:
                        # Kiểm tra xem có thẻ <a> bên trong xem_them không
                        has_a_tag = xem_them.find_all("a", type_query="tag_name")

                        if not has_a_tag:
                            driver.execute_script("arguments[0].click();", xem_them)
                except:
                    pass

            countComment = 0
            for cm in comments:
                if countComment >= 10:
                    break

                textComment = ""
                link_comment = []
                try:
                    div_elements = cm.find_all("./div")
                    if len(div_elements) < 2:
                        print("Khong co du 2 the div ben trong comment, bo qua.")
                        continue  # Bỏ qua nếu không có đủ phần tử

                    div_2 = div_elements[1].find_all("./div")

                    if len(div_2) == 0:
                        print("Khong co phan tu ben trong div 2, bo qua.")
                        continue  # Không có phần tử bên trong, bỏ qua

                    textComment = div_2[0].text_content().strip()

                    if textComment == "":
                        print("Khong co noi dung comment, bo qua.")
                        continue  # Không có nội dung, bỏ qua

                    # Lấy danh sách thẻ <a>
                    a_tags = div_2[1].find_all(".//a") if len(div_2) > 1 else []
                    if not a_tags:
                        a_tags = div_2[0].find_all(".//a")

                    for a in a_tags:
                        try:
                            # Kiểm tra xem thẻ <a> có thẻ <img> phía trước không
                            img_element = None
                            try:
                                img_element = a.find("preceding-sibling::img")
                            except:
                                pass

                            if img_element:
                                print(
                                    "The <a> co the <img> phia truoc, khong lay href."
                                )
                            else:
                                href = a.get_attribute("href")
                                if (
                                    href
                                    and self.convert_url.is_valid_link(href, linkItem)
                                    and href not in link_comment
                                ):
                                    link_comment.append(href)
                        except Exception as e:
                            print(f"Loi khi lay href: {e}")

                    # lấy link theo kiểm mobile
                    if driver.os_type_mobile:
                        try:
                            link_comment_elements = cm.find_all(
                                './/*[contains(@aria-label, "Comment")]/..//span[@role="link" and @data-focusable="true"]'
                            )
                            if link_comment_elements:
                                href = link_comment_elements[0].text_content().strip()
                                if (
                                    href
                                    and self.convert_url.is_valid_link(href, linkItem)
                                    and href not in link_comment
                                ):
                                    link_comment.append(href)
                        except Exception as e:
                            print(f"Loi khi lay link comment: {e}")
                            continue

                except Exception as e:
                    print(f"Loi khi xu ly comment: {e}")
                    continue  # Bỏ qua comment này nếu có lỗi

                # Xóa các ký tự không cần thiết
                for text in removeComment:
                    textComment = textComment.replace(text, "")

                textArray = textComment.split("\n")

                # Kiểm tra nếu có 'Top fan'
                if "Top fan" in textComment:
                    user_name = textArray[1] if len(textArray) > 1 else ""
                    textContentComment = " ".join(textArray[2:])
                else:
                    user_name = textArray[0] if len(textArray) > 0 else ""
                    textContentComment = " ".join(textArray[1:])

                textContentComment = textContentComment.replace("Follow", "").strip()

                countComment += 1
                if len(link_comment) > 0:
                    has_link_in_comments = True
                data.append(
                    {
                        "user_name": user_name,
                        "content": textContentComment,
                        "link_comment": [
                            self.convert_url.clean_facebook_url_redirect(url)
                            for url in link_comment
                        ],
                    }
                )

        except Exception as e:
            print(f"Loi tong quat trong get_comments: {e}")
        except Exception as e:
            print(e)
            print("Khong lay duoc binh luan!")
            raise Exception("Khong lay duoc binh luan!")
        finally:
            return data, has_link_in_comments

    # Hàm có tác dụng xem ảnh để facebook quan tâm đề xuất bài viết
    def views_image(self, images, driver, modal):
        if len(images) > 0:
            for img in images:
                try:
                    # Kiểm tra xem img có phải là chuỗi hợp lệ không
                    if not isinstance(img, str):
                        print(f"URL anh khong hop lo: {img}")
                        continue  # Bỏ qua nếu không phải chuỗi

                    # Tìm <img> có src giống với ảnh trong modal
                    try:
                        link = modal.find(f".//img[@src='{img}']")
                    except Exception:
                        print(f"⚠️ Khong tim thay anh: {img}")
                        continue  # Bỏ qua nếu không tìm thấy ảnh

                    # Tìm thẻ <a> cha bao quanh <img>
                    try:
                        link_element = link.find("./ancestor::a")
                        href = link_element.get_attribute(
                            "href"
                        )  # Lấy href của thẻ <a>
                    except Exception:
                        print("Khong tim thay the <a> bao quanh anh.")
                        continue  # Bỏ qua nếu không có thẻ <a>

                    # Nếu href không phải của Facebook thì bỏ qua
                    if not href.startswith("https://www.facebook.com/"):
                        print(f"⛔ Link ngoai, khong click: {href}")
                        continue  # Bỏ qua link ngoài

                    # Kiểm tra xem ảnh có thuộc quảng cáo không
                    try:
                        ad_element = link.find(
                            "./ancestor::div[@data-ad-rendering-role='image']"
                        )
                        print("anh thuoc quang cao! Khong click vao anh nay.")
                        continue  # Bỏ qua nếu ảnh thuộc quảng cáo
                    except:
                        pass  # Không có quảng cáo thì tiếp tục

                    # Click vào ảnh nếu hợp lệ
                    # try:
                    #     WebDriverWait(driver, 10).until(
                    #         EC.element_to_be_clickable(link)
                    #     ).click()
                    # except Exception as e:
                    #     print(f"Khong the click vao anh")
                    #     continue
                    # sleep(3)
                    driver.closeModal(0, True)
                    sleep(1)

                    # Đóng các tab thừa nếu có
                    # while len(driver.window_handles) > 1:
                    #     for handle in driver.window_handles[1:]:
                    #         driver.switch_to.window(handle)
                    #         driver.close()
                    #     driver.switch_to.window(driver.window_handles[0])

                except Exception as e:
                    print(f"Loi khi xem anh: {e}")
                    continue

    def get_source_post(self, driver, modal):
        try:
            data = {}
            print("Dang lay duong link profile")

            # Lấy đường dẫn tới profile
            proficeName = modal.find(
                '(//div[@data-ad-rendering-role="profile_name"])[last()]'
            )
            a_element = proficeName.find("a", type_query="tag_name")
            a_href = a_element.get_attribute("href")

            data["link"] = self.convert_url.extract_clean_url_profile(a_href)

            if a_href:
                driver.get(a_href, e_wait=10)

                # Lấy các thông tin của page
                info_page = self.get_info_page(driver)
                data["like_counts"] = info_page["like_counts"]
                data["follow_counts"] = info_page["follow_counts"]
                data["following_counts"] = info_page["following_counts"]
                data["name"] = info_page["name"]
                data["verified"] = info_page["verified"]
                data["id_facebook"] = info_page["id_facebook"]
            return data
        except Exception as e:
            print(f"Loi khi lay nguon goc bai viet: {e}")
            return {}

    def handle_craw_mobile(self, driver, stop_event):
        socket = self.config["socket"]
        id = self.config["id"]
        account = self.config["account"]
        page = self.config["page"]
        time_run_sql = self.config["time_run_sql"]
        tool_activity_logs_id = self.config["tool_activity_logs_id"]

        params = self.config["params"]
        start_time = time()
        time_run = time_run_sql * 3600
        account_id = account.get("id", 0)
        cookie_id = (
            account.get("latest_cookie")["id"]
            if account and account.get("latest_cookie")
            else 0
        )
        counts = 1
        count_article_success = 0
        position_article = 1
        print("Lay danh sach link bai viet")
        responseAddHistory = self.histories.createNewsFeed(
            {"account_id": account_id, "counts": 0}
        )
        socket(
            id=id,
            message=responseAddHistory["message"],
            tool_activity_logs_id=tool_activity_logs_id,
            status=1,
        )
        idHistory = responseAddHistory["id"]
        while (
            time() - start_time < time_run
            and not stop_event.is_set()
            and count_article_success < 10
        ):
            # nếu vị trí bài viết lớn hơn 100 thì reset về 1
            if position_article > 100:
                position_article = 1
            # nếu vị trí bài viết bằng 1 thì scroll cuối màn hình
            elif position_article > 1:
                driver.execute_script("window.scrollBy(0, window.innerHeight);")
                sleep(2)
            try:
                path = f"""(
                    ((//*[@data-tracking-duration-id][{position_article}])
                    //*[@data-action-id])[1]
                    //*
                    [(@data-mcomponent="TextArea" or @data-mcomponent="ServerTextArea")
                    and @data-focusable="true"
                    and not(@role="button")]
                )[last()]"""

                try:
                    btn_detail = driver.find(path)
                except Exception:
                    position_article += 1
                    continue
                socket(
                    id=id,
                    message=f"Lấy danh sách link bài viết",
                    tool_activity_logs_id=tool_activity_logs_id,
                    status=1,
                )
                time_text = btn_detail.text_content().strip()
                try:
                    converTime = self.convert_to_db_format(time_text)
                    driver.click_script(btn_detail)
                except:
                    converTime = None
                try:
                    driver.page.wait_for_url("**/story.php")
                except:
                    link = driver.current_url
                    print(f"Url khong chua /story.php bo qua: {link}")
                    position_article += 1
                    continue
                link = driver.current_url
                post_id = self.get_post_id(link, converTime)
                root_page_id = self.get_post_id(link, converTime, "id")
                link = {
                    "post_fb_id": post_id,
                    "post_fb_link": link,
                    "status": 1,
                    "cookie_id": cookie_id,
                    "account_id": account_id,
                    "time_up": converTime,
                    "root_page_id": root_page_id,
                }
                try:
                    # nếu chưa có lịch sử thì tạo mới
                    if counts > 1:
                        self.histories.update(id=idHistory, data={"counts": counts})
                except Exception as e:
                    raise Exception(f"Lỗi lưu khi gửi tạo history create newsfeed: {e}")
                # lặp qua đường link chi tiết rồi lấy ra bài viết
                try:
                    counts += 1
                    article = self.craw_content_page_mobile(
                        driver=driver, linkItem=link
                    )
                    if article:
                        # lấy ra page vừa lấy
                        article["idHistoryCrawPage"] = idHistory
                        print("Dang gui du lieu len server")
                        socket(
                            id=id,
                            message=f"Đang gửi dữ liệu lên server",
                            tool_activity_logs_id=tool_activity_logs_id,
                            status=1,
                        )
                        response = self.posts.add_post_newsfeed(
                            {"data": article}, params
                        )
                        print("Da gui du lieu len server: ", response)
                        message = response.get("message", "Lỗi server vui lòng gọi IT")
                        socket(
                            id=id,
                            message=message,
                            tool_activity_logs_id=tool_activity_logs_id,
                            status=1,
                        )
                        count_article_success += 1
                    else:
                        responseUpdateHistory = self.histories.updateValidCrawlNewsFeed(
                            idHistory, {}
                        )
                        socket(
                            id=id,
                            message=responseUpdateHistory["message"],
                            tool_activity_logs_id=tool_activity_logs_id,
                            status=1,
                        )
                except Exception as e:
                    content = f"Tài khoản: {account.get("name")} - Fanpage: {page.get("name")}  - Lỗi lấy bài viết: {e}"
                    socket(
                        id=id,
                        message=content,
                        tool_activity_logs_id=tool_activity_logs_id,
                        status=1,
                    )
                    raise Exception(content)
            except Exception as e:
                print("Loi trong handle_craw_mobile: ", e)
                raise Exception(e)
            finally:
                position_article += 1
                search = self.config["search"]
                max_back_times = 2 if search else 1

                for _ in range(max_back_times):
                    try:
                        # thực hiện back lại trang để lấy link khác
                        back_button = driver.find('//div[@aria-label="Back"]')
                        driver.click_script(back_button)
                        sleep(5)
                    except Exception as e:
                        break

                sleep(5)
                self.histories.update(idHistory, {"status": 2})

    def craw_content_page_mobile(self, driver, linkItem, config):
        keywords = config["keywords"]
        number_interactions = config["number_interactions"]
        filter_keyword = config["filter_keyword"]
        list_link_page_not_crawl = config["list_link_page_not_crawl"]
        filter_link = config["filter_link"]

        try:
            data = {}
            print("dang lay noi dung bai viet")
            # lấy noi dung bài viết
            content_element = driver.find(
                '((((//*[@data-pull-to-refresh-action-id])[1]//*[@data-mcomponent="MContainer" and @data-type="container"]//*[@data-mcomponent="ServerTextArea" and @data-type="text" and @style]//*[@dir="auto" and @style]//span[@class="f1"])[1])//..)[1]',
            )
            content = content_element.text_content().strip()
            content_link = []
            # tìm đường link trong nội dung bài viết
            link_content_elements = content_element.find_all('//span[@role="link"]')
            if len(link_content_elements) > 0:
                for link_element in link_content_elements:
                    href = link_element.text_content().strip()
                    if href and href.startswith("http"):
                        clean_href = self.convert_url.clean_facebook_url_redirect(href)
                        clean_href = self.convert_url.remove_params(
                            clean_href, "fbclid"
                        )
                        content_link.append(
                            self.convert_url.clean_facebook_url_redirect(href)
                        )

            # Lấy bình luận
            comments, has_link_in_comments = self.get_comments(driver, driver, linkItem)
            # kiểm tra xem trong bài viết hoặc comment có link hay không
            if filter_link and (
                len(content_link) == 0 and has_link_in_comments == False
            ):
                return {}

            # kiểm tra từ khóa với bình luận và nội dung bài viết
            matched_keywords = []
            if filter_keyword:
                normalized_content = self.remove_accents(content.lower())
                normalized_comments = [
                    self.remove_accents(comment["content"].lower())
                    for comment in comments
                ]

                for kw in keywords:
                    keyword_text = kw["keyword"]
                    normalized_keyword = self.remove_accents(keyword_text.lower())

                    # Kiểm tra trong nội dung bài viết
                    if normalized_keyword in normalized_content:
                        matched_keywords.append(kw)
                        continue  # khỏi cần kiểm tra trong comment nữa nếu đã thấy

                    # Kiểm tra trong bình luận
                    for comment_text in normalized_comments:
                        if normalized_keyword in comment_text:
                            matched_keywords.append(kw)
                            break  # dừng kiểm tra các comment còn lại nếu đã thấy

                if not matched_keywords:
                    return {}

            # lấy lượt tương tác
            # Thẻ copy nằm chung div với thẻ chứa lượt tương tác nên lây trực tiếp nó
            list_rections_element = driver.find_all(
                '//div[@role="button"and @data-action-id]//div[@data-mcomponent="ServerTextArea"]//div[@dir="auto"]/ancestor::*[@role="button"]',
            )
            number_of_reactions = {
                "comment": 0,
                "like": 0,
                "share": 0,
            }
            for rections_element in list_rections_element:
                aria_label = rections_element.get_attribute("aria-label")
                if aria_label:
                    reactions = self.parse_reactions(aria_label)
                    # Cộng dồn vào kết quả tổng
                    for key in number_of_reactions:
                        number_of_reactions[key] += reactions.get(key, 0)

            # kiểm tra lượt tương tác có đạt yêu cầu không
            like_source_post = number_of_reactions.get("like", 0)
            if like_source_post < number_interactions:
                print(
                    f"Luot tuong tac khong du, luot tuong tac page: {like_source_post} luot tuong tac mong muon: {number_interactions}, link: {linkItem['post_fb_link']} bo qua."
                )
                return {}

            image_elements = driver.find_all(
                '//*[@data-pull-to-refresh-action-id]//div[@data-focusable="true"]//img[@alt and string-length(@alt) > 10]',
            )
            video_elements = driver.find_all(
                '//*[@data-pull-to-refresh-action-id]//div[@aria-label="Video player"]//video',
            )
            media = {"images": [], "videos": []}
            for img in image_elements:
                src = img.get_attribute("src")
                if src and src.startswith("http") and "emoji.php" not in src:
                    media["images"].append(src)

            # Thực hiện xem chi tiết ảnh
            self.views_image(media["images"], driver, driver)
            sleep(5)

            # Lưu thông tin bài viết
            data["time_up"] = linkItem["time_up"]
            data["content"] = content
            data["matched_keywords"] = matched_keywords
            data["content_link"] = content_link
            # Lấy ảnh và video
            data["media"] = media
            # Lấy số lượng cảm xúc và bình luận
            data["number_of_reactions"] = number_of_reactions
            data["comments"] = comments
            data["link_facebook"] = linkItem["post_fb_link"]

            print("lay nguon goc bai viet")
            # lấy tên page
            name_page_element = driver.find(
                '(//*[@data-mcomponent="ServerTextArea" and @data-type="text"]//span[@data-action-id and @role="link" and @data-focusable="true"][1])[1]'
            )
            name = name_page_element.text_content().strip()
            # chuyển hướng đến trang cá nhân của bài viết
            driver.execute_script(
                "arguments[0].scrollIntoView(true);", name_page_element
            )
            sleep(1)  # chờ một chút để render xong
            driver.execute_script("arguments[0].click();", name_page_element)
            sleep(3)
            rool_page = driver.current_url
            # Kiểm tra nếu sourcePost["link"] có trong list_link_page_not_crawl
            if rool_page and rool_page in list_link_page_not_crawl:
                print(f"Source {rool_page} nam trong danh sach khong can cao, bo qua.")
                return {}

            like_counts, follow_counts, following_counts = (
                self.get_number_source_post_mobile(driver)
            )
            try:
                verified = driver.find('//span[text()=" 󱢏"]')
            except:
                pass
            verified = 1 if verified else 0
            id_facebook = self.handle_get_id_page(driver)
            print("id_facebook: ", id_facebook)
            data["source_post"] = {
                "link": rool_page,
                "name": name,
                "like_counts": like_counts,
                "follow_counts": follow_counts,
                "following_counts": following_counts,
                "verified": verified,
                "id_facebook": id_facebook,
            }
            return data
        except Exception as e:
            import traceback

            print(f"Loi khi lay noi dung bai viet: {e}")
            traceback.print_exc()
            raise Exception(f"Loi khi lay noi dung bai viet: {e}")

    def parse_reactions(self, aria_label):
        number_of_reactions = {
            "comment": 0,
            "like": 0,
            "share": 0,
        }

        # Normalize: bỏ ký tự đặc biệt và lowercase
        clean_label = re.sub(r"[^\x00-\x7F]+", " ", aria_label).lower()

        # Tách từng phần ra
        patterns = {
            "like": r"([\d\.]+[kKmM]?)\s*like",
            "comment": r"([\d\.]+[kKmM]?)\s*comment",
            "share": r"([\d\.]+[kKmM]?)\s*share",
        }

        def parse_number(s):
            s = s.lower()
            if "k" in s:
                return int(float(s.replace("k", "")) * 1000)
            elif "m" in s:
                return int(float(s.replace("m", "")) * 1000000)
            else:
                return int(s)

        for key, pattern in patterns.items():
            match = re.search(pattern, clean_label)
            if match:
                try:
                    number_of_reactions[key] = parse_number(match.group(1))
                except:
                    pass  # không chuyển được thì giữ nguyên là 0

        return number_of_reactions

    def get_number_source_post_mobile(self, driver):
        # Các phần tử này được lấy từ trang mới nên an toàn
        like_counts = 0
        follow_counts = 0
        following_counts = 0

        followers = driver.find('(//span[text()="followers"]/..)//span[1]')
        if followers:
            follow_counts = self.convert_shorthand_to_number(followers.text_content())
        likes = driver.find('(//span[text()="likes"]/..)//span[1]')
        if likes:
            like_counts = self.convert_shorthand_to_number(likes.text_content())
        following = driver.find('(//span[text()="following"]/..)//span[1]')
        if following:
            following_counts = self.convert_shorthand_to_number(
                following.text_content()
            )
        return like_counts, follow_counts, following_counts


class CrawlViaNewsfeed:

    def run(self, data):
        job_data = data.get("data")
        config_request = job_data.get("payload").get("config")
        config = {
            "get_article_friend": False,
            "name_center": "_newsfeed_via_",
            "search": False,
            "filter_keyword": False,
            "filter_link": False,
            "tab": session_newsfeed_via,
            "keyword": True,
            "socket": socket_newsfeed_via,
            "jobs_id": data.get("jobs_id"),
            "tool_activity_logs_id": data.get("tool_activity_logs_id"),
            "root": "Cào newsfeed theo via",
        }
        if config_request.get("crawl_type") == "search":
            config["search"] = True
            config["name_center"] = "_search_via_"
            config["root"] = "Cào search theo via"
        if config_request.get("filter_type") == "keyword":
            config["filter_keyword"] = True
        if config_request.get("filter_type") == "link":
            config["filter_link"] = True
        identifier = job_data.get("representative_code")
        stop_event = threading.Event()
        thread = threading.Thread(
            target=CrawlNewsfeed, args=(identifier, config, False)
        )
        session_newsfeed_via[identifier] = {
            "check": 2,
            "status": "Bắt đầu thực khi",
            "status_process": 1,
            "stop_event": stop_event,
            "thread": thread,
        }
        thread.start()


def socket_newsfeed_via(id, message, tool_activity_logs_id, status=0, params={}):
    tool_activity_log = ToolActivityLog()
    data = {"id": id, "status": message, "check": status, **params}
    session_newsfeed_via[str(id)] = {**session_newsfeed_via.get(str(id), {}), **data}
    tool_activity_log.update(id=tool_activity_logs_id, data={"content": data})
