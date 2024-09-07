from sqlalchemy import text

from engine.domains import EBPFProgram


def test_ebpf_program_model_can_load_from_db(session):
    session.execute(
        text(
            "INSERT INTO ebpf_program (id, name, code, attach_to) VALUES "
            '(1, "order1", "RED-CHAIR", "12"),'
            '(2, "order1", "RED-TABLE", "13"),'
            '(3, "order2", "BLUE-LIPSTICK", "14")'
        )
    )

    expected = [
        EBPFProgram.create(name="order1", code="RED-CHAIR", attach_to="12"),
        EBPFProgram.create(name="order1", code="RED-TABLE", attach_to="13"),
        EBPFProgram.create(name="order2", code="BLUE-LIPSTICK", attach_to="14"),
    ]
    result = session.query(EBPFProgram).all()

    # SQLAlchemy might return results in an undeterministic order
    # So we sort both lists by name before comparing
    # TODO: Investigate why the order is different
    sorted_result = sorted(result, key=lambda x: x.name)
    sorted_expected = sorted(expected, key=lambda x: x.name)

    assert len(sorted_result) == len(sorted_expected)

    for actual, expected_item in zip(sorted_result, sorted_expected, strict=False):
        assert actual.name == expected_item.name
        assert actual.code == expected_item.code
        assert actual.attach_to == expected_item.attach_to
