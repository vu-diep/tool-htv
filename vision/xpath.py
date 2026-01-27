class Xpath:
    form_logout = "//meta[@name='viewport']"
    verify_account = './/*[@aria-label="Verified"]'
    friends_likes = "a[href*='friends_likes']"
    followers = "a[href*='followers']"
    following = "a[href*='following']"
    list_posts = [
        "//*[@aria-posinset]",
        "//*[@data-tracking-duration-id]",
        "//*[@aria-describedby]",
        '//*[role="article"]',
    ]
    modal = (
        [
            '//*[@role="dialog" and @aria-labelledby]',
            '//*[@aria-posinset="1"]',
            "//*[@aria-describedby and @aria-labelledby]",
        ],
    )
    comment_button = './/*[@data-ad-rendering-role="comment_button"]'
    content = ['.//*[@data-ad-rendering-role="story_message"]', '/div[2]']
    scroll = ".//div/div/div/div[2]"
    media = './/*[@data-ad-rendering-role="story_message"]/parent::div/following-sibling::div'
    dyamic = './/*[@data-visualcompletion="ignore-dynamic"]/div/div/div/div'
    hasMore = ".//div[text()='See more']"
    comments = [
        ".//*[@aria-describedby and @aria-labelledby]//*[contains(@aria-label, 'Comment')]",
        ".//*[contains(@aria-label, 'Comment')]/..",
    ]
    btn_follow = '//div[@data-ad-rendering-role="profile_name"]//div[@role="button"]//span[text() = "Follow"]'
    switch_page = [
        '//*[@aria-label="Switch Now"]',
        '//*[@aria-label="Switch"]',
        '(//*[@aria-label="Switch"])[last()]',
        '//div[@aria-label="Review Now"]',
        '//*[@aria-label="Use Page"]',
    ]
    remove_string = [
        "\n",
        "·",
        "  ",
        "See Translation",  # Xem bản dịch
        "See original",  # Xem bản gốc
        "Rate this translation",  # Xếp hạng bản dịch này
    ]
    a = ".//a"
    ancestor_a = "./ancestor::a"
    img = ".//img"
    img_feedImage = ".//img[@data-imgperflogname='feedImage']"
    video = ".//video"
    comment_element = '//div[@role="button" and @aria-expanded="true"]//span[contains(text(), "comments")]'
    shares_element = '(//div[@role="button"]//span[contains(text(), "shares")])[last()]'
    all_reactions = '(//div[text()="All reactions:"]/..)[last()]'
    div_elements = "./div"
    img_element = "preceding-sibling::img"
    link_comment_elements = './/*[contains(@aria-label, "Comment")]/..//span[@role="link" and @data-focusable="true"]'
    title_fanpages = ["(//h1)/span/..", "(//h1)[last()]"]
    profile_name = '(//div[@data-ad-rendering-role="profile_name"])[last()]'
    home = '//*[@aria-label="Home"]'
    back = '//*[@aria-label="Back"]'
    profile_page_mobile = '//*[@aria-label="Tap to open profile page"]'
    time_up_mobile = "//div[@aria-label='Tap to open profile page']/../div[@data-type='text']//*[not(self::*[@role='link'] or ancestor::*[@role='link'])]/self::span"
    btn_comment_article_mobile = "//div[@role='button' and contains(@aria-label, 'comments')]"
    image_mobile = '//div[@role="button" and contains(@aria-label, "like")]/../../..//div[@data-type="container"]//div[contains(@aria-label, "May be an image of") and @data-type="text"]//img'
    video_mobile = './/div[@data-type="container"]//video'
    
class XpathLogin:
    input_login = [
        {"query": "email", "type": "tag_name"},
        {"query": ".//input[@name='email']", "type": "xpath"},
    ]
    input_login_password = [
        {
            "query": ".//div[@aria-labelledby='Log in']//input[@type='password']",
            "type": "xpath",
        },
        {"query": ".//input[@type='password']", "type": "xpath"},
        {"query": "pass", "type": "tag_name"},
    ]
    button_login = [
        {
            "query": ".//div[@aria-labelledby='Log in']//button[@name='login']",
            "type": "xpath",
        },
        {"query": ".//button[@name='login']", "type": "xpath"},
        {"query": "loginbutton", "type": "id"},
        {"query": "login", "type": "name"},
        {"query": "//span[text()='Log in'", "type": "xpath"},
    ]
    recent_login = "//a[@title]//img"
    profile_selectors = [
        '//*[@aria-label="Your profile"]',
        '//*[@aria-label="Go to profile"]',
    ]
    allow_all_cookies = '//*[@aria-label="Allow all cookies"]'
    btn_use_profile = '//span[text()="Use another profile"]'
    btn_try_another_way = '//div[@role="button"]//span'
    btn_authentication_app = [
        '(//input[@type="radio"])[2]',
        '//div[@aria-label="Authentication app, Get a code from your authentication app."]',
    ]
    xpath_continues = [
        '//div[@role="dialog"]//div[@role="button"]//div[@role="none"]//span//span',
        '//div[@aria-label="Continue"]//span[text()="Continue"]',
        '//span[text()="Continue"]',
    ]
    xpath_authen_app = [
        "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'authentication app')]",
        "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'Đi đến ứng dụng xác thực')]",
    ]
    save_your_login_info = '//span[text()="Save your login info?"]'
    save = '//div[@aria-label="Save"]'
    submit_2falive = '//*[@id="submit"]'
    code_2falive = '//*[@id="output"]'
    imput_authentication_app = '//input[@type="text"]'
    btn_continues = [
        "(//*[contains(text(), 'Continue')])[last()]",
        "(//*[contains(text(), 'Tiếp tục')])[last()]",
    ]

xpaths = Xpath()
xpath_login = XpathLogin()
