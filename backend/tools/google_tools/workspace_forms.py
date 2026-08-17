from typing import Any

from backend.tools.google_tools.workspace_core import google_resource_id, workspace_preview, workspace_request


FORMS_API = "https://forms.googleapis.com/v1/forms"


async def workspace_forms_create_form(title: str, document_title: str | None = None) -> dict[str, Any]:
    """Create a Google Form."""
    result = await workspace_request(
        "POST",
        FORMS_API,
        json={"info": {"title": title, "documentTitle": document_title or title}},
    )
    form_id = result.get("formId")
    return {
        "form_id": form_id,
        "title": result.get("info", {}).get("title"),
        "responder_uri": result.get("responderUri"),
        "edit_url": f"https://docs.google.com/forms/d/{form_id}/edit",
        "preview": workspace_preview(form_id, title, "application/vnd.google-apps.form") if form_id else None,
    }


async def workspace_forms_get_form(form: str) -> dict[str, Any]:
    """Read a Google Form's questions, settings, and responder URL."""
    form_id = google_resource_id(form)
    result = await workspace_request("GET", f"{FORMS_API}/{form_id}")
    result["preview"] = workspace_preview(form_id, result.get("info", {}).get("title"), "application/vnd.google-apps.form")
    return {"form": result}


async def workspace_forms_batch_update(form: str, requests: list[dict[str, Any]]) -> dict[str, Any]:
    """Add or update Google Form questions, quiz settings, and form structure."""
    form_id = google_resource_id(form)
    result = await workspace_request(
        "POST",
        f"{FORMS_API}/{form_id}:batchUpdate",
        json={"requests": requests},
    )
    return {
        "form_id": form_id,
        "replies": result.get("replies", []),
        "write_control": result.get("writeControl"),
        "preview": workspace_preview(form_id, mime_type="application/vnd.google-apps.form"),
    }


async def workspace_forms_set_published(
    form: str,
    published: bool = True,
    accepting_responses: bool = True,
) -> dict[str, Any]:
    """Publish or unpublish a Google Form and control whether it accepts responses."""
    form_id = google_resource_id(form)
    accepting = accepting_responses if published else False
    result = await workspace_request(
        "POST",
        f"{FORMS_API}/{form_id}:setPublishSettings",
        json={
            "publishSettings": {
                "publishState": {
                    "isPublished": published,
                    "isAcceptingResponses": accepting,
                },
            },
            "updateMask": "publishState",
        },
    )
    return {"form_id": form_id, "publish_settings": result.get("publishSettings")}


async def workspace_forms_list_responses(
    form: str,
    filter_query: str | None = None,
    page_size: int = 100,
) -> dict[str, Any]:
    """List responses submitted to a Google Form."""
    form_id = google_resource_id(form)
    params: dict[str, Any] = {"pageSize": max(1, min(5000, page_size))}
    if filter_query:
        params["filter"] = filter_query
    result = await workspace_request("GET", f"{FORMS_API}/{form_id}/responses", params=params)
    return {"responses": result.get("responses", []), "next_page_token": result.get("nextPageToken")}


async def workspace_forms_get_response(form: str, response_id: str) -> dict[str, Any]:
    """Read one Google Form response."""
    form_id = google_resource_id(form)
    result = await workspace_request("GET", f"{FORMS_API}/{form_id}/responses/{response_id}")
    return {"response": result}


FORMS_TOOLS = [
    workspace_forms_create_form,
    workspace_forms_get_form,
    workspace_forms_batch_update,
    workspace_forms_set_published,
    workspace_forms_list_responses,
    workspace_forms_get_response,
]
