
from fastapi import Form, Request
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.services.connection_service import ConnectionService
from app.utilities.flash import flash
from . import router, templates


@router.get("/network/mine", response_class=HTMLResponse, name="my_network_view")
async def my_network_view(
    request: Request,
    current_user: AuthDep,
    db: SessionDep,
):
    network = ConnectionService(db).get_my_network(current_user.id)
    return templates.TemplateResponse(
        request=request,
        name="my_network.html",
        context={"user": current_user, **network},
    )


@router.post("/network/requests", name="connection_request_action")
async def connection_request_action(
    request: Request,
    current_user: AuthDep,
    db: SessionDep,
    recipient_id: int = Form(...),
    return_to: str | None = Form(None),
):
    connection_service = ConnectionService(db)

    result = connection_service.send_request(
        sender_id=current_user.id,
        recipient_id=recipient_id,
    )

    flash(request, result["message"], result["category"])

    profile_path = f"/profiles/{recipient_id}"
    if return_to == profile_path:
        redirect_url = profile_path
    elif return_to and (return_to == "/network" or return_to.startswith("/network?")):
        redirect_url = return_to
    else:
        redirect_url = "/network"
    return RedirectResponse(url=redirect_url, status_code=303)


@router.post("/network/requests/{request_id}/respond", name="connection_request_response")
async def connection_request_response(
    request: Request,
    request_id: int,
    current_user: AuthDep,
    db: SessionDep,
    decision: str = Form(...),
):
    result = ConnectionService(db).respond_to_request(
        request_id=request_id,
        recipient_id=current_user.id,
        decision=decision,
    )
    flash(request, result["message"], result["category"])
    return RedirectResponse(url="/network/mine", status_code=303)


@router.post("/network/connections/{other_user_id}/disconnect", name="disconnect_connection_action")
async def disconnect_connection_action(
    request: Request,
    other_user_id: int,
    current_user: AuthDep,
    db: SessionDep,
):
    result = ConnectionService(db).disconnect(current_user.id, other_user_id)
    flash(request, result["message"], result["category"])
    return RedirectResponse(url=f"/profiles/{other_user_id}", status_code=303)
