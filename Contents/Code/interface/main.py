# coding=utf-8
from subzero.constants import PREFIX, TITLE, ART
from support.config import config
from support.helpers import pad_title, timestamp, df, display_language
from support.scheduler import scheduler
from support.ignore import ignore_list
from support.items import get_item_thumb, get_on_deck_items, get_all_items, get_items_info, get_item, get_item_title
from menu_helpers import main_icon, debounce, SubFolderObjectContainer, default_thumb, dig_tree, add_ignore_options, \
    ObjectContainer, route, handler
from item_details import ItemDetailsMenu


@handler(PREFIX, TITLE if not config.is_development else TITLE + " DEV", art=ART, thumb=main_icon)
@route(PREFIX)
def fatality(randomize=None, force_title=None, header=None, message=None, only_refresh=False, no_history=False,
             replace_parent=False):
    """
    subzero main menu
    """
    from interface.advanced import PinMenu, ClearPin, AdvancedMenu
    from interface.menu import RefreshMissing, IgnoreListMenu, HistoryMenu

    title = config.full_version  # force_title if force_title is not None else config.full_version
    oc = ObjectContainer(title1=title, title2=title, header=unicode(header) if header else title, message=message,
                         no_history=no_history,
                         replace_parent=replace_parent, no_cache=True)

    # always re-check permissions
    config.refresh_permissions_status()

    # always re-check enabled sections
    config.refresh_enabled_sections()

    if config.lock_menu and not config.pin_correct:
        oc.add(DirectoryObject(
            key=Callback(PinMenu, randomize=timestamp()),
            title=pad_title(L("Enter PIN")),
            summary=L("The owner has restricted the access to this menu. Please enter the correct pin"),
        ))
        return oc

    if not config.permissions_ok and config.missing_permissions:
        if not isinstance(config.missing_permissions, list):
            oc.add(DirectoryObject(
                key=Callback(fatality, randomize=timestamp()),
                title=pad_title(L("Insufficient permissions")),
                summary=config.missing_permissions,
            ))
        else:
            for title, path in config.missing_permissions:
                oc.add(DirectoryObject(
                    key=Callback(fatality, randomize=timestamp()),
                    title=pad_title(L("Insufficient permissions")),
                    summary=F("Insufficient permissions on library %s, folder: %s", title, path),
                ))
        return oc

    if not config.enabled_sections:
        oc.add(DirectoryObject(
            key=Callback(fatality, randomize=timestamp()),
            title=pad_title(L("I'm not enabled!")),
            summary=L("Please enable me for some of your libraries in your server settings; currently I do nothing"),
        ))
        return oc

    if not only_refresh:
        if Dict["current_refresh_state"]:
            oc.add(DirectoryObject(
                key=Callback(fatality, force_title=" ", randomize=timestamp()),
                title=pad_title(L("Working ... refresh here")),
                summary=F("Current state: %s; Last state: %s",
                    (Dict["current_refresh_state"] or "Idle") if "current_refresh_state" in Dict else "Idle",
                    (Dict["last_refresh_state"] or "None") if "last_refresh_state" in Dict else "None"
                )
            ))

        oc.add(DirectoryObject(
            key=Callback(OnDeckMenu),
            title=L("On-deck items"),
            summary=L("Shows the current on deck items and allows you to individually (force-) refresh their metadata subtitles."),
            thumb=R("icon-ondeck.jpg")
        ))
        if "last_played_items" in Dict and Dict["last_played_items"]:
            oc.add(DirectoryObject(
                key=Callback(RecentlyPlayedMenu),
                title=pad_title(L("Recently played items")),
                summary=F("Shows the %s recently played items and allows you to individually (force-) refresh their metadata/subtitles.", config.store_recently_played_amount),
                thumb=R("icon-played.jpg")
            ))
        oc.add(DirectoryObject(
            key=Callback(RecentlyAddedMenu),
            title=L("Recently-added items"),
            summary=L("Shows the recently added items per section."),
            thumb=R("icon-added.jpg")
        ))
        oc.add(DirectoryObject(
            key=Callback(RecentMissingSubtitlesMenu, randomize=timestamp()),
            title=L("Show recently added items with missing subtitles"),
            summary=L("Lists items with missing subtitles. Click on Find recent items with missing subs to update list"),
            thumb=R("icon-missing.jpg")
        ))
        oc.add(DirectoryObject(
            key=Callback(SectionsMenu),
            title=L("Browse all items"),
            summary=L("Go through your whole library and manage your ignore list. You can also (force-) refresh the metadata/subtitles of individual items."),
            thumb=R("icon-browse.jpg")
        ))

        task_name = "SearchAllRecentlyAddedMissing"
        task = scheduler.task(task_name)

        if task.ready_for_display:
            task_state = F("Running: %s/%s (%s%%)", task.items_done, task.items_searching, task.percentage)
        else:
            lr = scheduler.last_run(task_name)
            nr = scheduler.next_run(task_name)
            task_state = F("Last run: %s; Next scheduled run: %s; Last runtime: %s",
                df(scheduler.last_run(task_name)) if lr else "never",
                df(scheduler.next_run(task_name)) if nr else "never",
                str(task.last_run_time).split(".")[0])

        oc.add(DirectoryObject(
            key=Callback(RefreshMissing, randomize=timestamp()),
            title=F("Search for missing subtitles (in recently-added items, max-age: %s)", Prefs[
                "scheduler.item_is_recent_age"]),
            summary=F("Automatically run periodically by the scheduler, if configured. %s", task_state),
            thumb=R("icon-search.jpg")
        ))

        oc.add(DirectoryObject(
            key=Callback(IgnoreListMenu),
            title=F("Display ignore list (%d)", len(ignore_list)),
            summary=L("Show the current ignore list (mainly used for the automatic tasks)"),
            thumb=R("icon-ignore.jpg")
        ))

        oc.add(DirectoryObject(
            key=Callback(HistoryMenu),
            title=L("History"),
            summary=F("Show the last %i downloaded subtitles", int(Prefs["history_size"])),
            thumb=R("icon-history.jpg")
        ))

    oc.add(DirectoryObject(
        key=Callback(fatality, force_title=" ", randomize=timestamp()),
        title=pad_title(L("Refresh")),
        summary=F("Current state: %s; Last state: %s",
            (Dict["current_refresh_state"] or "Idle") if "current_refresh_state" in Dict else "Idle",
            (Dict["last_refresh_state"] or "None") if "last_refresh_state" in Dict else "None"
        ),
        thumb=R("icon-refresh.jpg")
    ))

    # add re-lock after pin unlock
    if config.pin:
        oc.add(DirectoryObject(
            key=Callback(ClearPin, randomize=timestamp()),
            title=pad_title(L("Re-lock menu(s)")),
            summary=L("Enabled the PIN again for menu(s)")
        ))

    if not only_refresh:
        if "provider_throttle" in Dict and Dict["provider_throttle"].keys():
            summary_data = []
            for provider, data in Dict["provider_throttle"].iteritems():
                reason, until, desc = data
                summary_data.append(F("%s until %s (%s)", provider, until.strftime("%y/%m/%d %H:%M"), reason))

            oc.add(DirectoryObject(
                key=Callback(fatality, force_title=" ", randomize=timestamp()),
                title=pad_title(F("Throttled providers: %s", ", ".join(Dict["provider_throttle"].keys()))),
                summary=", ".join(summary_data),
                thumb=R("icon-throttled.jpg")
            ))

        oc.add(DirectoryObject(
            key=Callback(AdvancedMenu),
            title=pad_title(L("Advanced functions")),
            summary=L("Use at your own risk"),
            thumb=R("icon-advanced.jpg")
        ))

    return oc


@route(PREFIX + '/on_deck')
def OnDeckMenu(message=None):
    """
    displays the items on deck
    :param message:
    :return:
    """
    return mergedItemsMenu(title=L("Items On Deck"), base_title=L("Items On Deck"), itemGetter=get_on_deck_items)


@route(PREFIX + '/recently_played')
def RecentlyPlayedMenu():
    base_title = L("Recently Played")
    oc = SubFolderObjectContainer(title2=base_title, replace_parent=True)

    for item in [get_item(rating_key) for rating_key in Dict["last_played_items"]]:
        if not item:
            continue

        if getattr(getattr(item, "__class__"), "__name__") not in ("Episode", "Movie"):
            continue

        item_title = get_item_title(item)

        oc.add(DirectoryObject(
            title=item_title,
            key=Callback(ItemDetailsMenu, title=base_title + " > " + item.title, item_title=item.title,
                         rating_key=item.rating_key)
        ))

    return oc


@route(PREFIX + '/recently_added')
def RecentlyAddedMenu(message=None):
    """
    displays the items recently added per section
    :param message:
    :return:
    """
    return SectionsMenu(base_title=L("Recently added"), section_items_key="recently_added", ignore_options=False)


@route(PREFIX + '/recent', force=bool)
@debounce
def RecentMissingSubtitlesMenu(force=False, randomize=None):
    title = L("Items with missing subtitles")
    oc = SubFolderObjectContainer(title2=title, no_cache=True, no_history=True)

    running = scheduler.is_task_running("MissingSubtitles")
    task_data = scheduler.get_task_data("MissingSubtitles")
    missing_items = task_data["missing_subtitles"] if task_data else None

    if ((missing_items is None) or force) and not running:
        scheduler.dispatch_task("MissingSubtitles")
        running = True

    if not running:
        oc.add(DirectoryObject(
            key=Callback(RecentMissingSubtitlesMenu, force=True, randomize=timestamp()),
            title=L(u"Find recent items with missing subtitles"),
            thumb=default_thumb
        ))
    else:
        oc.add(DirectoryObject(
            key=Callback(RecentMissingSubtitlesMenu, force=False, randomize=timestamp()),
            title=L(u"Updating, refresh here ..."),
            thumb=default_thumb
        ))

    if missing_items is not None:
        for added_at, item_id, item_title, item, missing_languages in missing_items:
            oc.add(DirectoryObject(
                key=Callback(ItemDetailsMenu, title=title + " > " + item_title, item_title=item_title,
                             rating_key=item_id),
                title=item_title,
                summary=F("Missing: %s", ", ".join(display_language(l) for l in missing_languages)),
                thumb=get_item_thumb(item) or default_thumb
            ))

    return oc


def mergedItemsMenu(title, itemGetter, itemGetterKwArgs=None, base_title=None, *args, **kwargs):
    """
    displays an item list of dynamic kinds of items
    :param title:
    :param itemGetter:
    :param itemGetterKwArgs:
    :param base_title:
    :param args:
    :param kwargs:
    :return:
    """
    oc = SubFolderObjectContainer(title2=title, no_cache=True, no_history=True)
    items = itemGetter(*args, **kwargs)

    for kind, title, item_id, deeper, item in items:
        oc.add(DirectoryObject(
            title=title,
            key=Callback(ItemDetailsMenu, title=base_title + " > " + title, item_title=title, rating_key=item_id),
            thumb=get_item_thumb(item) or default_thumb
        ))

    return oc


def determine_section_display(kind, item, pass_kwargs=None):
    """
    returns the menu function for a section based on the size of it (amount of items)
    :param kind:
    :param item:
    :return:
    """
    if pass_kwargs and pass_kwargs.get("section_items_key", "all") != "all":
        return SectionMenu
    if item.size > 80:
        return SectionFirstLetterMenu
    return SectionMenu


@route(PREFIX + '/ignore/set/{kind}/{rating_key}/{todo}/sure={sure}', kind=str, rating_key=str, todo=str, sure=bool)
def IgnoreMenu(kind, rating_key, title=None, sure=False, todo="not_set"):
    """
    displays the ignore options for a menu
    :param kind:
    :param rating_key:
    :param title:
    :param sure:
    :param todo:
    :return:
    """
    is_ignored = rating_key in ignore_list[kind]
    if not sure:
        oc = SubFolderObjectContainer(no_history=True, replace_parent=True, title1=F("%s %s %s %s the ignore list", 
            L("Add") if not is_ignored else L("Remove"), ignore_list.verbose(kind), title,
            L("to") if not is_ignored else L("from")), title2=L("Are you sure?"))
        oc.add(DirectoryObject(
            key=Callback(IgnoreMenu, kind=kind, rating_key=rating_key, title=title, sure=True,
                         todo=L("add") if not is_ignored else L("remove")),
            title=pad_title(L("Are you sure?")),
        ))
        return oc

    rel = ignore_list[kind]
    dont_change = False
    if todo == "remove":
        if not is_ignored:
            dont_change = True
        else:
            rel.remove(rating_key)
            Log.Info("Removed %s (%s) from the ignore list", title, rating_key)
            ignore_list.remove_title(kind, rating_key)
            ignore_list.save()
            state = L("removed from")
    elif todo == "add":
        if is_ignored:
            dont_change = True
        else:
            rel.append(rating_key)
            Log.Info("Added %s (%s) to the ignore list", title, rating_key)
            ignore_list.add_title(kind, rating_key, title)
            ignore_list.save()
            state = L("added to")
    else:
        dont_change = True

    if dont_change:
        return fatality(force_title=" ", header=L("Didn't change the ignore list"), no_history=True)

    return fatality(force_title=" ", header=F("%s %s the ignore list", title, state), no_history=True)


@route(PREFIX + '/sections')
def SectionsMenu(base_title=L("Sections"), section_items_key="all", ignore_options=True):
    """
    displays the menu for all sections
    :return:
    """
    items = get_all_items("sections")

    return dig_tree(SubFolderObjectContainer(title2=L("Sections"), no_cache=True, no_history=True), items, None,
                    menu_determination_callback=determine_section_display, pass_kwargs={"base_title": base_title,
                                                                                        "section_items_key": section_items_key,
                                                                                        "ignore_options": ignore_options},
                    fill_args={"title": "section_title"})


@route(PREFIX + '/section', ignore_options=bool)
def SectionMenu(rating_key, title=None, base_title=None, section_title=None, ignore_options=True,
                section_items_key="all"):
    """
    displays the contents of a section
    :param section_items_key:
    :param rating_key:
    :param title:
    :param base_title:
    :param section_title:
    :param ignore_options:
    :return:
    """
    from menu import MetadataMenu
    items = get_all_items(key=section_items_key, value=rating_key, base="library/sections")

    kind, deeper = get_items_info(items)
    title = unicode(title)

    section_title = title
    title = base_title + " > " + title
    oc = SubFolderObjectContainer(title2=title, no_cache=True, no_history=True)
    if ignore_options:
        add_ignore_options(oc, "sections", title=section_title, rating_key=rating_key, callback_menu=IgnoreMenu)

    return dig_tree(oc, items, MetadataMenu,
                    pass_kwargs={"base_title": title, "display_items": deeper, "previous_item_type": "section",
                                 "previous_rating_key": rating_key})


@route(PREFIX + '/section/firstLetter', deeper=bool)
def SectionFirstLetterMenu(rating_key, title=None, base_title=None, section_title=None, ignore_options=True,
                           section_items_key="all"):
    """
    displays the contents of a section indexed by its first char (A-Z, 0-9...)
    :param ignore_options: ignored
    :param section_items_key: ignored
    :param rating_key:
    :param title:
    :param base_title:
    :param section_title:
    :return:
    """
    from menu import FirstLetterMetadataMenu
    items = get_all_items(key="first_character", value=rating_key, base="library/sections")

    kind, deeper = get_items_info(items)

    title = unicode(title)
    oc = SubFolderObjectContainer(title2=section_title, no_cache=True, no_history=True)
    title = base_title + " > " + title
    add_ignore_options(oc, "sections", title=section_title, rating_key=rating_key, callback_menu=IgnoreMenu)

    oc.add(DirectoryObject(
        key=Callback(SectionMenu, title=L("All"), base_title=title, rating_key=rating_key, ignore_options=False),
        title="All"
    )
    )
    return dig_tree(oc, items, FirstLetterMetadataMenu, force_rating_key=rating_key, fill_args={"key": "key"},
                    pass_kwargs={"base_title": title, "display_items": deeper, "previous_rating_key": rating_key})
