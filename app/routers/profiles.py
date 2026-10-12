
from fastapi import HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.services.connection_service import ConnectionService
from app.services.profile_service import ProfileService
from app.utilities.flash import flash
from . import router, templates


@router.get("/network", response_class=HTMLResponse, name="network_view")
async def network_view(
    request: Request,
    current_user: AuthDep,
    db: SessionDep,
    q: str = "",
):
    profiles = ConnectionService(db).get_global_network(current_user.id, q)
    return templates.TemplateResponse(
        request=request,
        name="network.html",
        context={
            "user": current_user,
            "profiles": profiles,
            "query": q,
        },
    )


@router.get("/profiles/edit", response_class=HTMLResponse, name="profile_edit_view")
async def profile_edit_view(
    request: Request,
    current_user: AuthDep,
    db: SessionDep,
):
    profile = ProfileService(db).get_profile(current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    return templates.TemplateResponse(
        request=request,
        name="profile_edit.html",
        context={
            "profile": profile,
            "user": current_user,
        },
    )


@router.get("/profiles/{user_id}", response_class=HTMLResponse, name="profile_view")
async def view_profile(
    request: Request,
    user_id: int,
    current_user: AuthDep,
    db: SessionDep,
):
    profile = ProfileService(db).get_profile(user_id)

    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    referer = (request.headers.get("referer") or "").lower()
    show_back_to_network = (
        user_id != current_user.id and (
            "/network" in referer or "/profiles/" in referer
        )
    )

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "profile": profile,
            "user": current_user,
            "show_back_to_network": show_back_to_network,
            "connection_state": "self" if user_id == current_user.id else ConnectionService(db).get_connection_state(
                current_user.id,
                user_id,
            ),
        },
    )


@router.post("/profiles/edit", name="profile_edit_action")
async def profile_edit_action(
    request: Request,
    current_user: AuthDep,
    db: SessionDep,
):
    form = await request.form()
    form_data = {}
    for key, value in form.multi_items():
        form_data.setdefault(key, []).append(value)

    result = ProfileService(db).update_profile(
        user_id=current_user.id,
        form_data=form_data,
    )

    flash(request, result["message"], result["category"])

    return RedirectResponse(
        url=f"/profiles/{current_user.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )