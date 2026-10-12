from pathlib import Path
from uuid import uuid4

from fastapi import File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import FacultyDep
from app.dependencies.session import SessionDep
from app.services.event_service import EventService
from app.utilities.flash import flash
from . import router, templates


@router.get("/events", response_class=HTMLResponse, name="event_list_view")
async def event_list_view(request: Request, db: SessionDep):
    from app.dependencies.auth import get_current_user

    user = await get_current_user(request, db)
    service = EventService(db)
    events = service.get_public_events()
    return templates.TemplateResponse(
        request=request,
        name="events.html",
        context={
            "user": user,
            "events": events,
        },
    )


@router.get("/events/mine", response_class=HTMLResponse, name="my_events_view")
async def my_events_view(request: Request, db: SessionDep):
    from app.dependencies.auth import get_current_user

    user = await get_current_user(request, db)
    service = EventService(db)
    events = service.get_events_for_user(user.id)
    return templates.TemplateResponse(
        request=request,
        name="my_events.html",
        context={
            "user": user,
            "events": events,
        },
    )


@router.get("/events/new", response_class=HTMLResponse, name="event_new_view")
async def event_new_view(request: Request, user: FacultyDep, db: SessionDep):
    return templates.TemplateResponse(
        request=request,
        name="event_form.html",
        context={
            "user": user,
            "event_types": EventService.EVENT_TYPES,
            "venue_types": EventService.VENUE_TYPES,
            "event": None,
        },
    )


@router.get("/events/{event_id}/edit", response_class=HTMLResponse, name="event_edit_view")
async def event_edit_view(request: Request, event_id: int, user: FacultyDep, db: SessionDep):
    service = EventService(db)
    event = service.get_event_by_id(event_id)
    if event is None or event.faculty_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="event_form.html",
        context={
            "user": user,
            "event_types": EventService.EVENT_TYPES,
            "venue_types": EventService.VENUE_TYPES,
            "event": event,
        },
    )


@router.post("/events", response_class=HTMLResponse, status_code=status.HTTP_201_CREATED, name="event_create_action")
async def event_create_action(
    request: Request,
    db: SessionDep,
    user: FacultyDep,
    title: str = Form(...),
    description: str = Form(""),
    event_type: str = Form("Social"),
    event_status: str = Form("tentative"),
    start_datetime: str = Form(""),
    end_datetime: str = Form(""),
    venue_type: str = Form("in-person"),
    location: str = Form(""),
    meeting_link: str = Form(""),
    capacity: str = Form(""),
    save_as_draft: str = Form("false"),
    event_logo: UploadFile | None = File(default=None),
):
    try:
        service = EventService(db)

        logo_path = None
        if event_logo and event_logo.filename:
            upload_dir = Path("app/static/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{uuid4()}_{event_logo.filename}"
            destination = upload_dir / filename
            destination.write_bytes(await event_logo.read())
            logo_path = f"/static/uploads/{filename}"

        created = service.create_event(
            faculty_user_id=user.id,
            title=title,
            description=description,
            start_datetime=start_datetime or None,
            end_datetime=end_datetime or None,
            location=location,
            status=event_status,
            event_type=event_type,
            venue_type=venue_type,
            meeting_link=meeting_link or None,
            capacity=capacity or None,
            event_logo=logo_path,
            save_as_draft=str(save_as_draft).lower() == "true" or str(save_as_draft).lower() == "1",
        )
        flash(request, "Event saved as draft." if created.is_draft else "Event created successfully.", "success")
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(url=request.url_for("event_new_view"), status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse(url=request.url_for("my_events_view"), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/events/{event_id}/edit", response_class=HTMLResponse, name="event_edit_action")
async def event_edit_action(
    request: Request,
    event_id: int,
    db: SessionDep,
    user: FacultyDep,
    title: str = Form(...),
    description: str = Form(""),
    event_type: str = Form("Social"),
    event_status: str = Form("tentative"),
    start_datetime: str = Form(""),
    end_datetime: str = Form(""),
    venue_type: str = Form("in-person"),
    location: str = Form(""),
    meeting_link: str = Form(""),
    capacity: str = Form(""),
    save_as_draft: str = Form("false"),
    event_logo: UploadFile | None = File(default=None),
):
    service = EventService(db)
    event = service.get_event_by_id(event_id)
    if event is None or event.faculty_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        logo_path = event.event_logo
        if event_logo and event_logo.filename:
            upload_dir = Path("app/static/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{uuid4()}_{event_logo.filename}"
            destination = upload_dir / filename
            destination.write_bytes(await event_logo.read())
            logo_path = f"/static/uploads/{filename}"

        updated = service.update_event(
            event_id=event_id,
            title=title,
            description=description,
            start_datetime=start_datetime or None,
            end_datetime=end_datetime or None,
            location=location,
            status=event_status,
            event_type=event_type,
            venue_type=venue_type,
            meeting_link=meeting_link or None,
            capacity=capacity or None,
            event_logo=logo_path,
            save_as_draft=str(save_as_draft).lower() == "true" or str(save_as_draft).lower() == "1",
        )
        flash(request, "Event saved as draft." if updated.is_draft else "Event updated successfully.", "success")
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(url=request.url_for("event_edit_view", event_id=event_id), status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse(url=request.url_for("my_events_view"), status_code=status.HTTP_303_SEE_OTHER)
