from seedwork.application.identity import Identity


def test_authenticated_identity():
    identity = Identity(id="user-1", name="Alice", roles=["admin"])

    assert identity.is_authenticated
    assert identity.is_in_role("admin")
    assert not identity.is_in_role("user")


def test_empty_id_is_anonymous():
    identity = Identity(id="", name="Anonymous")

    assert not identity.is_authenticated
