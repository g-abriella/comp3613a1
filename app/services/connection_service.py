from sqlmodel import Session

from app.models.connection_request import ConnectionRequest
from app.models.user import User
from app.repositories.connection import ConnectionRepository
from app.repositories.profile import ProfileRepository


class ConnectionService:
    def __init__(self, db: Session):
        self.db = db
        self.connection_repository = ConnectionRepository(db)
        self.profile_repository = ProfileRepository(db)

    def get_global_network(self, user_id: int, query: str = ""):
        profiles = self.profile_repository.search_profiles(query, exclude_user_id=user_id)
        for profile in profiles:
            request = self.connection_repository.get_between_users(
                user_id,
                profile["user"].id,
            )
            profile["connection_state"] = self._connection_state(request, user_id)
            profile["request_id"] = request.id if request else None
        return profiles

    def get_my_network(self, user_id: int):
        connections = []
        incoming_requests = []
        outgoing_requests = []

        for request in self.connection_repository.get_for_user(user_id):
            if request.status not in {"pending", "accepted"}:
                continue
            other_user_id = (
                request.recipient_id
                if request.sender_id == user_id
                else request.sender_id
            )
            profile = self.profile_repository.get_profile(other_user_id)
            if profile is None:
                continue
            entry = {"profile": profile, "request": request}
            if request.status == "accepted":
                connections.append(entry)
            elif request.recipient_id == user_id:
                incoming_requests.append(entry)
            else:
                outgoing_requests.append(entry)

        return {
            "connections": connections,
            "incoming_requests": incoming_requests,
            "outgoing_requests": outgoing_requests,
        }

    def get_connection_state(self, user_id: int, other_user_id: int):
        request = self.connection_repository.get_between_users(user_id, other_user_id)
        return self._connection_state(request, user_id)

    def send_request(self, sender_id: int, recipient_id: int):
        if sender_id == recipient_id:
            return {"message": "You cannot connect with your own account.", "category": "danger"}

        recipient = self.db.get(User, recipient_id)
        if recipient is None or recipient.role not in {"alumni", "faculty"}:
            return {"message": "That profile is not available.", "category": "danger"}

        existing = self.connection_repository.get_between_users(sender_id, recipient_id)
        if existing is not None:
            if existing.status == "rejected":
                self.connection_repository.resend_rejected(existing, sender_id, recipient_id)
                return {"message": "Connection request sent again.", "category": "success"}
            return {
                "message": self._existing_request_message(existing, sender_id),
                "category": "info",
            }

        request = ConnectionRequest(sender_id=sender_id, recipient_id=recipient_id)
        self.connection_repository.create(request)
        return {"message": "Connection request sent.", "category": "success"}

    def respond_to_request(self, request_id: int, recipient_id: int, decision: str):
        request = self.connection_repository.get_by_id(request_id)
        if (
            request is None
            or request.recipient_id != recipient_id
            or request.status != "pending"
        ):
            return {"message": "That request is no longer available.", "category": "danger"}

        if decision not in {"accepted", "rejected"}:
            return {"message": "Choose accept or reject for this request.", "category": "danger"}

        self.connection_repository.update_status(request, decision)
        message = "Connection accepted." if decision == "accepted" else "Request rejected."
        return {"message": message, "category": "success"}

    def disconnect(self, user_id: int, other_user_id: int):
        request = self.connection_repository.get_between_users(user_id, other_user_id)
        if request is None or request.status != "accepted":
            return {"message": "That connection is no longer available.", "category": "danger"}

        self.connection_repository.delete(request)
        return {"message": "You are no longer connected.", "category": "success"}

    @staticmethod
    def _connection_state(request: ConnectionRequest | None, user_id: int):
        if request is None:
            return "available"
        if request.status == "accepted":
            return "connected"
        if request.status == "rejected":
            return "rejected"
        if request.sender_id == user_id:
            return "outgoing_pending"
        return "incoming_pending"

    @staticmethod
    def _existing_request_message(request: ConnectionRequest, user_id: int):
        state = ConnectionService._connection_state(request, user_id)
        messages = {
            "connected": "You are already connected.",
            "outgoing_pending": "Your connection request is still pending.",
            "incoming_pending": "You already have an incoming request from this member.",
            "rejected": "A request between these members was already rejected.",
        }
        return messages[state]