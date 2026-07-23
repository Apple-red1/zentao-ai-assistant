import pytest

from zentao_ai.zentao.models import BugSnapshot
from zentao_ai.zentao.query_filters import (
    extract_title_tags,
    filter_assignee_bugs,
    filter_title_bugs,
    is_unclosed_status,
    normalize_title_search_text,
)


def bug(bug_id: int, title: str, status: str = "active") -> BugSnapshot:
    return BugSnapshot(
        id=bug_id,
        title=title,
        status=status,
        version="v1",
        snapshotVersion="v1",
        snapshotStable=True,
    )


ITEMS = (
    bug(2537, "【AI建站】【区块路线】页脚的超链接无法点击"),
    bug(3397, "【站点后台】登录按钮背景色改为白色，文字改为黑色"),
)


def test_filters_ai_site_tag_across_all_statuses() -> None:
    assert filter_assignee_bugs(ITEMS, title_tag="AI建站", status="all") == (
        ITEMS[0],
    )


def test_filters_admin_tag_to_unclosed_bugs() -> None:
    assert filter_assignee_bugs(ITEMS, title_tag="站点后台", status="unclosed") == (
        ITEMS[1],
    )


def test_returns_all_unclosed_bugs_without_title_tag() -> None:
    assert filter_assignee_bugs(ITEMS, title_tag=None, status="unclosed") == ITEMS


def test_extracts_only_repeated_leading_full_width_tags() -> None:
    assert extract_title_tags(ITEMS[0].title) == ("ai建站", "区块路线")
    assert extract_title_tags("正文【AI建站】") == ()
    assert extract_title_tags("[AI建站]正文") == ()


def test_normalizes_and_trims_tag_values_for_exact_matching() -> None:
    item = bug(1, "【 ＡＩ建站 】正文")
    assert extract_title_tags(item.title) == ("ai建站",)
    assert filter_assignee_bugs((item,), title_tag=" ai建站 ", status="all") == (item,)


def test_similar_tag_does_not_match() -> None:
    item = bug(1, "【AI建站项目】正文")
    assert filter_assignee_bugs((item,), title_tag="AI建站", status="all") == ()


def test_unclosed_recognizes_active_and_open_states() -> None:
    assert is_unclosed_status(" ACTIVE ")
    assert is_unclosed_status("ｏｐｅｎ")


def test_unclosed_excludes_terminal_and_unknown_states() -> None:
    for status in ("resolved", "closed", "已解决", "已关闭", "mystery"):
        assert not is_unclosed_status(status)


def test_all_retains_unknown_states_while_unclosed_excludes_them() -> None:
    item = bug(1, "【AI建站】正文", status="mystery")
    assert filter_assignee_bugs((item,), title_tag=None, status="all") == (item,)
    assert filter_assignee_bugs((item,), title_tag=None, status="unclosed") == ()


@pytest.mark.parametrize(
    "title",
    [
        "【设计器】【统一面板-文本元素】文本元素悬停设置宽度未生效",
        "【设计器】【统一面板-time】字体大小设置H标签的字体大小时未生效",
        "【设计器】【统一面板-按钮】按钮元素中字体颜色未生效",
        "【设计器】【统一面板-倒计时】选中其中一个part会跳到不存在的part中",
        "【设计器】【统一面板-容器类】设置视频背景后无法调节透明度",
        "【AI建站】设计器统一面板样式异常",
    ],
)
def test_filters_titles_with_normalized_keyword(title: str) -> None:
    item = bug(1, title)
    assert filter_title_bugs(
        (item,), title_keyword="设计器统一面板", status="all"
    ) == (item,)


def test_normalizes_nfc_and_casefold_for_title_search() -> None:
    assert normalize_title_search_text(" Cafe\u0301 ") == "café"
    item = bug(1, "CAFÉ guide")
    assert filter_title_bugs((item,), title_keyword="cafe\u0301", status="all") == (item,)


def test_does_not_match_reordered_title_characters() -> None:
    item = bug(1, "alpha beta")
    assert filter_title_bugs((item,), title_keyword="beta alpha", status="all") == ()


def test_rejects_title_keyword_containing_only_separators_and_whitespace() -> None:
    with pytest.raises(ValueError, match="^title keyword is empty$"):
        filter_title_bugs((bug(1, "title"),), title_keyword=" [ - ] \t", status="all")


def test_title_unclosed_includes_every_status_except_closed() -> None:
    items = tuple(
        bug(index, "match", status=status)
        for index, status in enumerate(("active", "open", "resolved", "closed"))
    )
    assert filter_title_bugs(items, title_keyword="match", status="unclosed") == items[:3]


def test_title_all_includes_closed_bugs() -> None:
    item = bug(1, "match", status="closed")
    assert filter_title_bugs((item,), title_keyword="match", status="all") == (item,)
