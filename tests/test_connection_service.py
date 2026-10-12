from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database import drop_all, ensure_db_and_tables, engine
from app.main import app
from app.repositories.user import UserRepository
from app.schemas.user import AlumniCreate, FacultyCreate
from app.services.connection_service import ConnectionService
from app.utilities.security import create_access_token


def _create_member(db: Session, role: str, suffix: str):
    schema = AlumniCreate if role == "alumni" else FacultyCreate
    return UserRepository(db).create(
        schema(
            username=f"{role}{suffix}",
            email=f"{role}{suffix}@example.com",
            password="secret",
            role=role,
        )
    )


def test_connection_request_can_be_accepted_and_cannot_be_duplicated():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        sender = _create_member(db, "alumni", "sender")
        recipient = _create_member(db, "faculty", "recipient")
        service = ConnectionService(db)

        sent = service.send_request(sender.id, recipient.id)
        duplicate = service.send_request(sender.id, recipient.id)
        reverse_duplicate = service.send_request(recipient.id, sender.id)

        assert sent["category"] == "success"
        assert duplicate["category"] == "info"
        assert reverse_duplicate["category"] == "info"
        assert service.get_global_network(sender.id)[0]["connection_state"] == "outgoing_pending"
        assert len(service.get_my_network(recipient.id)["incoming_requests"]) == 1

        request_id = service.get_my_network(recipient.id)["incoming_requests"][0]["request"].id
        accepted = service.respond_to_request(request_id, recipient.id, "accepted")

        assert accepted["category"] == "success"
        assert len(service.get_my_network(sender.id)["connections"]) == 1
        assert service.get_global_network(sender.id)[0]["connection_state"] == "connected"

    drop_all()


def test_rejected_request_can_be_resent():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        sender = _create_member(db, "alumni", "rejectsender")
        recipient = _create_member(db, "faculty", "rejectrecipient")
        service = ConnectionService(db)

        service.send_request(sender.id, recipient.id)
        request = service.get_my_network(recipient.id)["incoming_requests"][0]["request"]
        result = service.respond_to_request(request.id, recipient.id, "rejected")
        repeated = service.send_request(sender.id, recipient.id)

        assert result["message"] == "Request rejected."
        assert repeated["category"] == "success"
        assert service.get_global_network(sender.id)[0]["connection_state"] == "outgoing_pending"
        assert len(service.get_my_network(recipient.id)["incoming_requests"]) == 1

    drop_all()


def test_connected_members_can_disconnect():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        sender = _create_member(db, "alumni", "disconnectsender")
        recipient = _create_member(db, "faculty", "disconnectrecipient")
        service = ConnectionService(db)

        service.send_request(sender.id, recipient.id)
        request = service.get_my_network(recipient.id)["incoming_requests"][0]["request"]
        service.respond_to_request(request.id, recipient.id, "accepted")

        disconnected = service.disconnect(sender.id, recipient.id)

        assert disconnected["category"] == "success"
        assert service.get_connection_state(sender.id, recipient.id) == "available"
        assert service.get_my_network(sender.id)["connections"] == []

    drop_all()


def test_profile_shows_connection_and_disconnects_from_profile():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        sender = _create_member(db, "alumni", "profiledisconnectsender")
        recipient = _create_member(db, "faculty", "profiledisconnectrecipient")
        service = ConnectionService(db)
        service.send_request(sender.id, recipient.id)
        request = service.get_my_network(recipient.id)["incoming_requests"][0]["request"]
        service.respond_to_request(request.id, recipient.id, "accepted")
        token = create_access_token({"sub": str(sender.id), "role": sender.role})

        with TestClient(app) as client:
            profile_response = client.get(
                f"/profiles/{recipient.id}",
                cookies={"access_token": token},
            )
            assert profile_response.status_code == 200
            assert "Connected" in profile_response.text
            assert "disconnectConnectionModal" in profile_response.text

            disconnect_response = client.post(
                f"/network/connections/{recipient.id}/disconnect",
                cookies={"access_token": token},
                follow_redirects=False,
            )
            assert disconnect_response.status_code == 303
            assert disconnect_response.headers["location"] == f"/profiles/{recipient.id}"

        assert ConnectionService(db).get_connection_state(sender.id, recipient.id) == "available"

    drop_all()


def test_rejected_request_can_be_resent_from_profile_and_network():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        sender = _create_member(db, "alumni", "retryprofilesender")
        recipient = _create_member(db, "faculty", "retryprofilerecipient")
        service = ConnectionService(db)
        service.send_request(sender.id, recipient.id)
        request = service.get_my_network(recipient.id)["incoming_requests"][0]["request"]
        service.respond_to_request(request.id, recipient.id, "rejected")
        token = create_access_token({"sub": str(sender.id), "role": sender.role})

        with TestClient(app) as client:
            profile_response = client.get(
                f"/profiles/{recipient.id}",
                cookies={"access_token": token},
            )
            assert profile_response.status_code == 200
            assert "profileConnectModal" in profile_response.text
            assert 'data-bs-target="#profileConnectModal"' in profile_response.text

            network_response = client.get("/network", cookies={"access_token": token})
            assert network_response.status_code == 200
            assert f'data-recipient-id="{recipient.id}"' in network_response.text

            resend_response = client.post(
                "/network/requests",
                data={
                    "recipient_id": str(recipient.id),
                    "return_to": f"/profiles/{recipient.id}",
                },
                cookies={"access_token": token},
                follow_redirects=False,
            )
            assert resend_response.status_code == 303
            assert resend_response.headers["location"] == f"/profiles/{recipient.id}"

        fresh_db = Session(engine)
        try:
            fresh_service = ConnectionService(fresh_db)
            assert fresh_service.get_connection_state(sender.id, recipient.id) == "outgoing_pending"
            assert len(fresh_service.get_my_network(recipient.id)["incoming_requests"]) == 1
        finally:
            fresh_db.close()

    drop_all()