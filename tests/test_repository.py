from app import repository as repo


async def test_create_thread_defaults(session):
    thread = await repo.create_thread(session)

    assert thread.title == "New chat"
    assert thread.user_id is None


async def test_owner_sees_own_thread(session):
    await repo.create_thread(session, user_id="user-a", title="A's chat")

    threads = await repo.list_threads(session, user_id="user-a")

    assert [t.title for t in threads] == ["A's chat"]


async def test_other_user_cannot_list_thread(session):
    await repo.create_thread(session, user_id="user-a")

    threads = await repo.list_threads(session, user_id="user-b")

    assert threads == []


async def test_anonymous_and_owned_threads_are_separate(session):
    await repo.create_thread(session, user_id=None, title="Anonymous")
    await repo.create_thread(session, user_id="user-a", title="Owned")

    anonymous = await repo.list_threads(session, user_id=None)
    owned = await repo.list_threads(session, user_id="user-a")

    assert [t.title for t in anonymous] == ["Anonymous"]
    assert [t.title for t in owned] == ["Owned"]


async def test_other_user_cannot_get_rename_or_delete(session):
    thread = await repo.create_thread(session, user_id="user-a", title="Private")

    assert await repo.get_thread(session, thread.id, user_id="user-b") is None
    assert (
        await repo.rename_thread(session, thread.id, "Hacked", user_id="user-b")
        is None
    )
    assert await repo.delete_thread(session, thread.id, user_id="user-b") is False

    # The owner's data must be untouched by all of that
    still_there = await repo.get_thread(session, thread.id, user_id="user-a")
    assert still_there is not None
    assert still_there.title == "Private"


async def test_owner_can_rename(session):
    thread = await repo.create_thread(session, user_id="user-a", title="Old")

    renamed = await repo.rename_thread(session, thread.id, "New", user_id="user-a")

    assert renamed is not None
    assert renamed.title == "New"
    fetched = await repo.get_thread(session, thread.id, user_id="user-a")
    assert fetched.title == "New"


async def test_owner_can_delete(session):
    thread = await repo.create_thread(session, user_id="user-a")

    assert await repo.delete_thread(session, thread.id, user_id="user-a") is True

    assert await repo.get_thread(session, thread.id, user_id="user-a") is None
    assert await repo.list_threads(session, user_id="user-a") == []


async def test_get_missing_thread_returns_none(session):
    assert await repo.get_thread(session, "does-not-exist") is None


async def test_touch_moves_thread_to_top(session):
    older = await repo.create_thread(session, user_id="user-a", title="Older")
    await repo.create_thread(session, user_id="user-a", title="Newer")

    before = await repo.list_threads(session, user_id="user-a")
    assert [t.title for t in before] == ["Newer", "Older"]

    await repo.touch_thread(session, older.id, user_id="user-a")

    after = await repo.list_threads(session, user_id="user-a")
    assert [t.title for t in after] == ["Older", "Newer"]


async def test_archived_threads_hidden_by_default(session):
    thread = await repo.create_thread(session, user_id="user-a")
    thread.archived = True
    await session.commit()

    default = await repo.list_threads(session, user_id="user-a")
    with_archived = await repo.list_threads(
        session, user_id="user-a", include_archived=True
    )

    assert default == []
    assert [t.id for t in with_archived] == [thread.id]