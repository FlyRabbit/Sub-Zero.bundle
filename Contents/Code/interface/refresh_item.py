# coding=utf-8

from subzero.constants import PREFIX
from menu_helpers import debounce, set_refresh_menu_state, route
from support.items import refresh_item
from support.helpers import timestamp
from support.i18n import _


@route(PREFIX + '/item/refresh/{rating_key}/force', force=True)
@route(PREFIX + '/item/refresh/{rating_key}')
@debounce
def RefreshItem(rating_key=None, came_from="/recent", item_title=None, force=False, refresh_kind=None,
                previous_rating_key=None, timeout=8000, randomize=None, trigger=True):
    assert rating_key
    from interface.main import fatality
    header = " "
    if trigger:
        set_refresh_menu_state(_(u"Triggering %(forced)sRefresh for %(title)s",
                                 forced=_("Force-") if force else "",
                                 title=item_title))
        Thread.Create(refresh_item, rating_key=rating_key, force=force, refresh_kind=refresh_kind,
                      parent_rating_key=previous_rating_key, timeout=int(timeout))

        header = _(u"%(refresh_or_forced_refresh)s of item %(item_id)s triggered",
                   refresh_or_forced_refresh=_("Refresh") if not force else _("Forced-refresh"),
                   item_id=rating_key)
    return fatality(randomize=timestamp(), header=header, replace_parent=True)
