from datetime import date

from sqlalchemy import and_, or_
from sqlmodel import Session, select

from app.models.connection_request import ConnectionRequest


class ConnectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_between_users(self, first_user_id: int, second_user_id: int):
        statement = select(ConnectionRequest).where(
            or_(
                and_(
                    ConnectionRequest.sender_id == first_user_id,
                    ConnectionRequest.recipient_id == second_user_id,
                ),
                and_(
                    ConnectionRequest.sender_id == second_user_id,
                    ConnectionRequest.recipient_id == first_user_id,
                ),
            )
        )
        return self.db.exec(statement).first()

    def get_for_user(self, user_id: int):
        statement = select(ConnectionRequest).where(
            or_(
                ConnectionRequest.sender_id == user_id,
                ConnectionRequest.recipient_id == user_id,
            )
        )
        return self.db.exec(statement).all()

    def get_by_id(self, request_id: int):
        return self.db.get(ConnectionRequest, request_id)

    def create(self, request: ConnectionRequest):
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def update_status(self, request: ConnectionRequest, new_status: str):
        request.status = new_status
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def resend_rejected(self, request: ConnectionRequest, sender_id: int, recipient_id: int):
        request.sender_id = sender_id
        request.recipient_id = recipient_id
        request.sent_date = date.today()
        request.status = "pending"
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def delete(self, request: ConnectionRequest):
        self.db.delete(request)
        self.db.commit()