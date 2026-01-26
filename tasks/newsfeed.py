from time import time, sleep, monotonic
from datetime import datetime
import re
import json
import threading
import traceback
from lxml import etree

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
            # Tạo vòng đời
            while not stop_event.is_set():
                start_time = time()
                self.config["start_time"] = start_time
                self.config["time_run"] = time_run
                # theo dõi vị trí các từ khóa trong mảng keywords
                indexKeywords = 0
                if driver.isClosed():  # Nếu bị đóng thì tự khởi động lại
                    print("Trinh duyet bi dong khoi dong lai: ")
                    driver = Driver(profile, startUrl=False)

                # đánh dấu số lần thử login lại
                driver.action_send_error = root
                # xác định thời gian chạy và thời gian ngủ
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
                        # nếu vị trí mà chưa vượt ra ngoài mảng keywords thì tiếp tục lấy keyword tại vị trí hiện tại
                        if indexKeywords < len(keywords) and search == True:
                            keyword = keywords[indexKeywords]
                            indexKeywords += 1
                            self.render_and_search_keywords(keyword["keyword"], driver)
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
                                self.handle_crawl_web(driver, stop_event)
                            elif driver.os_type_mobile:
                                self.handle_crawl_mobile(driver, stop_event)
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

    def handle_crawl_web(self, driver, stop_event):
        start_time = self.config["start_time"]
        time_run = self.config["time_run"]
        socket = self.config["socket"]
        id = self.config["id"]
        account = self.config["account"]
        page = self.config["page"]
        params = self.config["params"]
        tool_activity_logs_id = self.config["tool_activity_logs_id"]
        get_article_friend = self.config["get_article_friend"]
        filter_keyword = self.config["filter_keyword"]
        list_post_id = []
        keywords = self.config["keywords"]
        
        start_time_crawl = monotonic()
        # thời gian thực hiện search. 5p
        timeout_search = 3000
        last_run_search = start_time_crawl
        index_keyword = 0
        
        # tạo lịch sử cào bài
        responseAddHistory = self.histories.createNewsFeed(
            {"account_id": account.get("id"), "counts": 0}
        )
        history_id = responseAddHistory["id"]
        quantity_post = 0
        listId = set()
        print("keywords: ", json.dumps(keywords, indent=4))
        
        # vòng lặp thực hiện công việc cào dữ liệu
        while time() - start_time < time_run and not stop_event.is_set():
            try:
                now = monotonic()
                # Sử lý logic search. Cứ sau timeout_search mà không tìm được bài nào và có yêu cầu lọc theo keyword thì thực hiện search rồi mới thu thập bài viết
                if filter_keyword and now - last_run_search >= timeout_search and len(keywords) > 0:
                    keyword = keywords[index_keyword]
                    print("Thuc hien search tu khoa: ", keyword)
                    self.search_keywords(keyword, driver)
                    index_keyword += index_keyword
                    
                list_posts = []
                # Lặp qua từng XPath cho đến khi tìm được phần tử
                for xpath in xpaths.list_posts:
                    list_posts = driver.find_all(xpath)
                    if list_posts:
                        break
                len_list_post = len(list_posts)
                print("len_list_post: ", len_list_post)
                for modal in list_posts:
                    try:
                        # nếu modal đã k còn thì bỏ qua
                        if driver.check_dom(modal) == False:
                            continue
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
                        content, content_link = self.extract_facebook_content(
                            driver, modal=modal
                        )
                        print("content: ", content)
                        print("content_link: ", content_link)
                        sleep(self.random_seconds())
                        matched_keywords = []
                        if filter_keyword  and len(keywords) > 0:
                            matched_keywords = self.filter_keywords(
                                content=content, keywords=keywords
                            )
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
                            links = driver.find_all(xpaths.a, parent=modal)
                            dataMedia = self.get_image_and_video(driver, modal)
                            for link in links:
                                if link is None:
                                    continue
                                box = link.bounding_box()
                                if (
                                    link.is_visible()
                                    and box["width"] > 0
                                    and box["height"] > 0
                                ):
                                    driver.js_hover_and_focus(link)
                                    sleep(5)
                                    href = link.get_attribute("href")
                                    print("href: ", href)
                                    if not href:
                                        print("Khong tim thay href trong link")
                                        continue
                                    href = self.convert_url.clean_url_keep_params(href)
                                    link_time = link.inner_text().strip()
                                    try:
                                        converTime = self.convert_to_db_format(link_time)
                                    except:
                                        converTime = None
                                    post_id = self.get_post_id(href, converTime)
                                    if post_id == "" or post_id in list_post_id:
                                        continue
                                    driver.click_script(link)
                                    # Lấy số lượng cảm xúc và bình luận
                                    print("dang lay tuong tac bai viet")
                                    numberOfReactionsAndComments = (
                                        self.get_number_of_reactions_and_comments(driver, modal)
                                    )
                                    print("dang lay binh luan bai viet")
                                    print("numberOfReactionsAndComments: ", json.dumps(numberOfReactionsAndComments, indent=4))
                                    # Lấy bình luận
                                    comments, has_link_in_comments = self.get_comments(
                                        modal, driver
                                    )
                                    # Thực hiện xem chi tiết ảnh
                                    self.views_image(dataMedia["images"], driver, modal)
                                    sourcePost = self.get_source_post(driver, modal)
                                    article = {
                                        "post_fb_id": post_id,
                                        "link_facebook": href,
                                        "matched_keywords": matched_keywords,
                                        "content": content,
                                        "content_link": content_link,
                                        "media": dataMedia,
                                        "number_of_reactions": numberOfReactionsAndComments,
                                        "comments": comments,
                                        "source_post": sourcePost,
                                        "idHistoryCrawPage": history_id
                                    }
                                    response = self.posts.add_post_newsfeed({"data": article}, params)
                                    print("article: ", json.dumps(article, indent=4))
                                    print("Da gui du lieu len server: ", response)
                                    socket(id, response["message"], 1)
                                    quantity_post +=1
                                    self.histories.update(id=history_id, data={'counts': quantity_post})
                                    # quay trở về trang chủ
                                    self.back_home(driver=driver)
                    except Exception as e:
                        print(f"Phan tu khong ton tai, tim lai phan tu: {e}")
                        traceback.print_exc()
                        continue
            except Exception as e:
                raise Exception(e)

    def handle_crawl_mobile(self, driver, stop_event):
        start_time = self.config["start_time"]
        time_run = self.config["time_run"]
        socket = self.config["socket"]
        id = self.config["id"]
        account = self.config["account"]
        page = self.config["page"]
        params = self.config["params"]
        tool_activity_logs_id = self.config["tool_activity_logs_id"]
        get_article_friend = self.config["get_article_friend"]
        filter_keyword = self.config["filter_keyword"]
        list_post_id = []
        keywords = self.config["keywords"]
        
        start_time_crawl = monotonic()
        # thời gian thực hiện search. 5p
        timeout_search = 3000
        last_run_search = start_time_crawl
        index_keyword = 0
        
        # tạo lịch sử cào bài
        responseAddHistory = self.histories.createNewsFeed(
            {"account_id": account.get("id"), "counts": 0}
        )
        history_id = responseAddHistory["id"]
        quantity_post = 0
        listId = set()
        print("keywords: ", json.dumps(keywords, indent=4))
        
        # vòng lặp thực hiện công việc cào dữ liệu
        while time() - start_time < time_run and not stop_event.is_set():
            try:
                now = monotonic()
                # Sử lý logic search. Cứ sau timeout_search mà không tìm được bài nào và có yêu cầu lọc theo keyword thì thực hiện search rồi mới thu thập bài viết
                if filter_keyword and now - last_run_search >= timeout_search and len(keywords) > 0:
                    keyword = keywords[index_keyword]
                    print("Thuc hien search tu khoa: ", keyword)
                    self.search_keywords(keyword, driver)
                    index_keyword += index_keyword
                    
                list_posts = []
                # Lặp qua từng XPath cho đến khi tìm được phần tử
                for xpath in xpaths.list_posts:
                    list_posts = driver.find_all(xpath)
                    if list_posts:
                        break
                len_list_post = len(list_posts)
                print("len_list_post: ", len_list_post)
                for modal in list_posts:
                    try:
                        # nếu modal đã k còn thì bỏ qua
                        if driver.check_dom(modal) == False:
                            continue
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
                        content, content_link = self.extract_facebook_content(
                            driver, modal=modal
                        )
                        print("content: ", content)
                        print("content_link: ", content_link)
                        sleep(self.random_seconds())
                        matched_keywords = []
                        if filter_keyword  and len(keywords) > 0:
                            matched_keywords = self.filter_keywords(
                                content=content, keywords=keywords
                            )
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
                            # chuyển hướng vào trong chi tiết bài viết
                            time_up_element = driver.find(xpaths.time_up_mobile, parent=modal)
                            if time_up_element is None:
                                continue
                            time_up = time_up_element.inner_text().strip()
                            print("time_up: ", time_up)
                            driver.click_script(time_up_element)
                            profile_page = driver.find(xpaths.profile_page_mobile, parent=modal)
                            
                    except Exception as e:
                        print(f"Phan tu khong ton tai, tim lai phan tu: {e}")
                        traceback.print_exc()
                        continue
            except Exception as e:
                raise Exception(e)

    # Hàm có tác dụng chuyển hướng đến tìm kiếm theo từ khóa và thực hiện click vào nút lấy bài viết mới nhất
    def search_keywords(self, keyword, driver):
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
                    driver.click_script(btn_all)
                # thực hiện lọc theo bài viết gần đây
                sleep(10)
                checkbox = driver.find('//input[@aria-label="Recent posts" or @aria-label="Recent Posts"]')
            # Click vào checkbox nếu tìm thấy
            if checkbox:
                print("tim thay checkbox")
                driver.click_script(checkbox)
            self.random_sleep(5)
        except Exception as e:
            print(f"Loi khi chuyen huong den search: {e}")

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
                    content, content_link = self.extract_facebook_content(
                        driver, modal=modal
                    )
                    print("content: ", content)
                    print("content_link: ", content_link)
                    sleep(self.random_seconds())
                    matched_keywords = []
                    if filter_keyword:
                        matched_keywords = self.filter_keywords(
                            content=content, keywords=keywords
                        )
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
                        links = driver.find_all(xpaths.a, parent=modal)
                        dataMedia = self.get_image_and_video(driver, modal)
                        for link in links:
                            if link is None:
                                continue
                            box = link.bounding_box()
                            if (
                                link.is_visible()
                                and box["width"] > 0
                                and box["height"] > 0
                            ):
                                driver.js_hover_and_focus(link)
                                sleep(5)
                                href = link.get_attribute("href")
                                print("href: ", href)
                                if not href:
                                    print("Khong tim thay href trong link")
                                    continue
                                href = self.convert_url.clean_url_keep_params(href)
                                link_time = link.inner_text().strip()
                                print("link_time: ", link_time)
                                try:
                                    converTime = self.convert_to_db_format(link_time)
                                except:
                                    converTime = None
                                print("converTime: ", converTime)

                                post_id = self.get_post_id(href, converTime)
                                print("post_id: ", post_id)
                                if post_id == "" or post_id in list_post_id:
                                    continue
                                link.click()
                                # Lấy số lượng cảm xúc và bình luận
                                print("dang lay tuong tac bai viet")
                                numberOfReactionsAndComments = (
                                    self.get_number_of_reactions_and_comments(driver, modal)
                                )
                                print("dang lay binh luan bai viet")
                                print("numberOfReactionsAndComments: ", json.dumps(numberOfReactionsAndComments, indent=4))
                                # Lấy bình luận
                                comments, has_link_in_comments = self.get_comments(
                                    modal, driver
                                )
                                # Thực hiện xem chi tiết ảnh
                                self.views_image(dataMedia["images"], driver, modal)
                                sourcePost = self.get_source_post(driver, modal)
                                print("source_post: ", sourcePost)
                                article = {
                                    "post_fb_id": post_id,
                                    "link_facebook": href,
                                    "matched_keywords": matched_keywords,
                                    "content": content,
                                    "content_link": content_link,
                                    "media": dataMedia,
                                    "number_of_reactions": numberOfReactionsAndComments,
                                    "comments": comments,
                                    "source_post": sourcePost,
                                }
                                return article

                    if stop_event.is_set():
                        break
                except Exception as e:
                    print(f"Phan tu khong ton tai, tim lai phan tu: {e}")
                    traceback.print_exc()
                    continue
            driver.scroll_mouse(delta_y=500, times=5, delay=0.4)
            sleep(self.random_seconds())

        return list_article

    def filter_keywords(self, content, keywords):
        matched_keywords = []
        normalized_content = self.remove_accents(content.lower())
        for kw in keywords:
            keyword_text = kw["keyword"]
            normalized_keyword = self.remove_accents(keyword_text.lower())

            # Kiểm tra trong nội dung bài viết
            if normalized_keyword in normalized_content:
                matched_keywords.append(kw)
        # nếu không tìm thấy keyword thì bỏ qua
        return matched_keywords

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
            content, content_link = self.extract_facebook_content(
                modal=modal, driver=driver
            )
            print("content: ", content)
            print("content_link: ", content_link)
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
        numberOfReactionsAndComments = self.get_number_of_reactions_and_comments(
            driver, modal
        )
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
    def get_number_of_reactions_and_comments(self, driver, modal):
        data = {
            "comment": 0,
            "like": 0,
            "share": 0,
        }
        try:
            all_reactions = driver.find(
                xpaths.all_reactions, type_query="tag_name", parent=modal
            )
            like = all_reactions.inner_text()
            like = self.convert_shorthand_to_number(like)
            data["like"] = like
        except Exception as e:
            print(f"Khong lay duoc like")
        try:
            comment_element = driver.find(
                xpaths.comment_element, type_query="tag_name", parent=modal
            )
            comment = comment_element.inner_text()
            comment = self.convert_shorthand_to_number(comment)
            data["comment"] = comment
        except Exception as e:
            print(f"Khong lay duoc comments")
        try:
            shares_element = driver.find(
                xpaths.shares_element, type_query="tag_name", parent=modal
            )
            shares = shares_element.inner_text()
            shares = self.convert_shorthand_to_number(shares)
            data["share"] = shares
        except Exception as e:
            print(f"Khong lay duoc shares")

        except Exception as e:
            print(f"Khong lay duoc like, comment, share: {e}")
        return data

    def get_comments(self, modal, driver):
        print("Bat dau lay comment")
        data = []
        has_link_in_comments = False
        removeComment = ["·", "Author\n", "  ", "Top fan", "Follow"]
        
        try:
            comment_button = driver.find(xpaths.comment_button)
            if comment_button is not None:
                driver.scroll_to_locator(comment_button)
            print("Cuon chuot xuong (tim thay element scroll): ", comment_button)
        except Exception as e:
            driver.scroll_mouse()
            print("Cuon chuot xuong bang window: ", e)
        sleep(3)

        try:
            comments = None
            # Thử lấy comments bằng cách thông thường
            for xpath_comment in xpaths.comments:
                comments = driver.find_all(xpath_comment, parent=modal)
                if len(comments) > 0:
                    break
            print(f"Tim thay {len(comments)} binh luan")
            
            # Nếu không lấy được comments, sử dụng fallback method
            if len(comments) == 0:
                print("Khong lay duoc comments bang cach thuong, su dung fallback method...")
                data, has_link_in_comments = self._parse_comments_from_html(driver, modal)
                return data, has_link_in_comments
            
            # Xử lý comments theo cách thông thường
            # xu ly các phần tử "Xem thêm"
            for cm in comments:
                driver.scroll_to_locator(cm)
                self.click_see_mores(driver=driver, parent=cm)

            countComment = 0
            for cm in comments:
                if countComment >= 10:
                    break

                textComment = ""
                link_comment = []
                try:
                    div_elements = driver.find_all(xpaths.div_elements, parent=cm)
                    if len(div_elements) < 2:
                        print("Khong co du 2 the div ben trong comment, bo qua.")
                        continue

                    div_2 = driver.find_all(xpaths.div_elements, parent=div_elements[1])
                    if len(div_2) == 0:
                        print("Khong co phan tu ben trong div 2, bo qua.")
                        continue

                    textComment = div_2[0].inner_text().strip()

                    if textComment == "":
                        print("Khong co noi dung comment, bo qua.")
                        continue

                    # Lấy danh sách thẻ <a>
                    a_tags = (
                        driver.find_all(xpaths.a, parent=div_2[1])
                        if len(div_2) > 1
                        else []
                    )
                    if not a_tags:
                        a_tags = driver.find_all(xpaths.a, parent=div_2[0])
                    for a in a_tags:
                        try:
                            img_element = None
                            try:
                                img_element = driver.find(xpaths.img_element, parent=a)
                            except:
                                pass

                            if img_element:
                                print("The <a> co the <img> phia truoc, khong lay href.")
                            else:
                                href = a.get_attribute("href")
                                if (
                                    href
                                    and self.convert_url.is_valid_link(href)
                                    and href not in link_comment
                                ):
                                    link_comment.append(href)
                        except Exception as e:
                            print(f"Loi khi lay href: {e}")

                    # lấy link theo kiểm mobile
                    if driver.os_type_mobile:
                        try:
                            link_comment_elements = driver.find_all(
                                xpaths.link_comment_elements, parent=cm
                            )
                            if link_comment_elements:
                                href = link_comment_elements[0].inner_text().strip()
                                if (
                                    href
                                    and self.convert_url.is_valid_link(href)
                                    and href not in link_comment
                                ):
                                    link_comment.append(href)
                        except Exception as e:
                            print(f"Loi khi lay link comment: {e}")
                            continue

                except Exception as e:
                    print(f"Loi khi xu ly comment: {e}")
                    continue

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
            print("Khong lay duoc binh luan!")
            raise Exception("Khong lay duoc binh luan!")
        finally:
            return data, has_link_in_comments


    def _parse_comments_from_html(self, driver, modal):
        """
        Fallback method: Parse comments từ HTML source code
        """
        print("Parsing comments from HTML source...")
        data = []
        has_link_in_comments = False
        removeComment = ["·", "Author\n", "  ", "Top fan", "Follow"]
        
        try:
            html = driver.page_source()
            tree = etree.HTML(html)
            
            comment_elements = []
            for xpath in xpaths.comments:
                comment_elements = tree.xpath(xpath)
                if len(comment_elements) > 0:
                    print(f"Tim thay {len(comment_elements)} comments bang XPath: {xpath}")
                    break
            
            if len(comment_elements) == 0:
                print("Khong tim thay comment nao trong HTML")
                return data, has_link_in_comments
            
            countComment = 0
            for cm_element in comment_elements[:10]:  # Giới hạn 10 comments
                try:
                    # Lấy text content
                    text_content = cm_element.xpath('string(.)')
                    print("text_content: ", text_content)
                    textComment = ' '.join([t.strip() for t in text_content if t.strip()])
                    
                    if not textComment:
                        continue
                    
                    # Lấy links
                    link_comment = []
                    a_elements = cm_element.xpath('.//a[@href]')
                    for a in a_elements:
                        href = a.get('href')
                        # Kiểm tra xem có img trong <a> không
                        has_img = len(a.xpath('.//img')) > 0
                        if not has_img and href and self.convert_url.is_valid_link(href):
                            if href not in link_comment:
                                link_comment.append(href)
                    
                    # Xóa các ký tự không cần thiết
                    for text in removeComment:
                        textComment = textComment.replace(text, "")
                    
                    textArray = textComment.split("\n")
                    textArray = [t.strip() for t in textArray if t.strip()]
                    
                    # Kiểm tra nếu có 'Top fan'
                    if "Top fan" in textComment:
                        user_name = textArray[1] if len(textArray) > 1 else ""
                        textContentComment = " ".join(textArray[2:])
                    else:
                        user_name = textArray[0] if len(textArray) > 0 else ""
                        textContentComment = " ".join(textArray[1:])
                    
                    textContentComment = textContentComment.replace("Follow", "").strip()
                    
                    if textContentComment:  # Chỉ thêm nếu có nội dung
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
                    print(f"Loi khi parse comment tu HTML: {e}")
                    continue
            
            print(f"Da parse duoc {countComment} comments tu HTML")
            
        except Exception as e:
            print(f"Loi trong _parse_comments_from_html: {e}")
        
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
                        link = driver.find(xpaths.img_feedImage, parent=modal)
                        # Tìm thẻ <a> cha bao quanh <img>
                        link_element = driver.find(xpaths.ancestor_a, parent=link)
                        href = link_element.get_attribute("href")  # Lấy href của thẻ <a>
                        print("href: ", href)
                        # Nếu href không phải của Facebook thì bỏ qua
                        if not href.startswith("https://www.facebook.com/"):
                            print(f"⛔ Link ngoai, khong click: {href}")
                            continue  # Bỏ qua link ngoài
                        # Kiểm tra xem ảnh có thuộc quảng cáo không
                        ad_element = driver.find("./ancestor::div[@data-ad-rendering-role='image']",parent=link)
                        if ad_element is not None:
                            continue
                        # Click vào ảnh nếu hợp lệ
                        link.scroll_into_view_if_needed()
                        driver.click_script(link)
                    except Exception as  e:
                        print(f"⚠️ Khong tim thay anh: {img}")
                        traceback.print_exc()
                        continue  # Bỏ qua nếu không tìm thấy ảnh
                    
                    sleep(10)
                    driver.close_modal(last=True)
                except Exception as e:
                    print(f"Loi khi xem anh: {e}")
                    continue

    def get_source_post(self, driver, modal):
        try:
            data = {}
            print("Dang lay duong link profile")

            # Lấy đường dẫn tới profile
            proficeName = driver.find( xpaths.profile_name, parent=modal, type_query="tag_name")
            a_element = driver.find("a", type_query="tag_name", parent=proficeName)
            a_href = a_element.get_attribute("href")

            data["link"] = self.convert_url.extract_clean_url_profile(a_href)

            if a_href:
                a_element.click()

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
            traceback.print_exc()
            return {}


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
            content = content_element.inner_text().strip()
            content_link = []
            # tìm đường link trong nội dung bài viết
            link_content_elements = content_element.find_all('//span[@role="link"]')
            if len(link_content_elements) > 0:
                for link_element in link_content_elements:
                    href = link_element.inner_text().strip()
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
            name = name_page_element.inner_text().strip()
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
            follow_counts = self.convert_shorthand_to_number(followers.inner_text())
        likes = driver.find('(//span[text()="likes"]/..)//span[1]')
        if likes:
            like_counts = self.convert_shorthand_to_number(likes.inner_text())
        following = driver.find('(//span[text()="following"]/..)//span[1]')
        if following:
            following_counts = self.convert_shorthand_to_number(following.inner_text())
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
        print("identifier: ", identifier)
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
