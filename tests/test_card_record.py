import math

from pipeline.schemas.card_record import CardRecord, Category, Condition


def test_alias_and_normalisation():
    record = CardRecord(
        sku="  SKU-001  ",
        cat="Sports Cards",
        brand=" ",
        set="Legends",
        year="1999",
        player="  Ken Griffey Jr.  ",
        character="Spider-Man",
        num=15,
        subset=" ",
        variant="",
        serial=" ",
        auto="yes",
        mem="no",
        grade="",
        cond="Near Mint",
        notes="  Great card  ",
        price_est="12.5",
        conf="0.82",
    )

    assert record.sku == "SKU-001"
    assert record.cat is Category.SPORTS
    assert record.cond is Condition.NM
    assert record.year == 1999
    assert record.player == "Ken Griffey Jr."
    assert record.character is None
    assert record.num == "15"
    assert record.subset is None
    assert record.variant is None
    assert record.serial is None
    assert record.auto is True
    assert record.mem is False
    assert record.grade == "raw"
    assert record.notes == "Great card"
    assert math.isclose(record.price_est or 0.0, 12.5)
    assert math.isclose(record.conf, 0.82)


def test_character_retained_for_non_sports():
    record = CardRecord(
        sku="XYZ",
        cat="Pokémon",
        player="Ash",
        character="Pikachu",
        cond="raw",
        conf=0.5,
    )

    assert record.cat is Category.POKEMON
    assert record.character == "Pikachu"
    assert record.player is None
    assert record.cond is Condition.RAW
