from typing import Dict, Optional

from .profiles import profiles
from tasks.newsfeed import CrawlViaNewsfeed

# Khai báo rote
blueprints = [
    (profiles, "/api/profiles"),
]
# Khai báo các hàm chức năng sẽ chạy khi nhận được tín hiệu từ server
dispatcher_config: Dict[int, Optional[object]] = {
    # 1: PostContent,
    # 5: CrawlInternalWebsitePosts,
    # 9: PublishWebsitePost,
    # 12: CrawlExternalWebsitePosts,
    # 13: CrawlFanpageNewsfeed,
    # 14: MonitorFanpageNewsfeed,
    # 15: CrawlFanpageData,
    # 16: FollowFanpage,
    17: CrawlViaNewsfeed,
    # 18: AutoCrawlWebsite,
}
