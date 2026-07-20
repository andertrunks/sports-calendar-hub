from src.privacy_scan import scan_payload, scan_text


def test_uid_publico_nao_e_tratado_como_email() -> None:
    assert not scan_text("abc@sports-calendar-hub")


def test_email_privado_e_detectado() -> None:
    assert scan_text("pessoa@example.com")


def test_meet_e_detectado() -> None:
    assert scan_text("https://meet.google.com/abc-defg-hij")


def test_payload_sem_attendees_e_seguro() -> None:
    assert not scan_payload({"uid": "abc@sports-calendar-hub", "transparency": "TRANSPARENT"})


def test_id_bruto_do_google_calendar_e_detectado() -> None:
    assert scan_text("abcdef1234567890@google.com")
