"""Resource-level authorization for folders and reports.

This sits between the route handlers and the data. Two flavours of check:

1. **Query scoping** (`visible_folders`, `can_view_report`): list endpoints
   filter to only the rows a user is entitled to, so they can never over-return.
   Defense in depth — even a buggy handler can't leak another domain's data.

2. **Point checks** (`assert_can_view_folder`, ...): for direct-by-id access we
   re-check authorization. For domain resources the caller is not entitled to,
   we raise **404 (not 403)** so the API does not even confirm the resource
   exists — preventing enumeration of other functions' dashboards via direct
   URLs (a requirement of the brief).
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..auth.rbac import Domain, Principal
from ..models import Folder, FolderType, Report, ReportStatus, User


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _forbidden(msg: str = "Forbidden") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg)


# --------------------------------------------------------------------------- #
# Folder visibility
# --------------------------------------------------------------------------- #
def can_view_folder(principal: Principal, user: User, folder: Folder) -> bool:
    if folder.type == FolderType.SHARED:
        return True
    if folder.type == FolderType.PERSONAL:
        return folder.owner_user_id == user.id
    if folder.type == FolderType.DOMAIN:
        if folder.domain is None:
            return False
        return principal.in_domain(Domain(folder.domain))
    return False


def visible_folders(db: Session, principal: Principal, user: User) -> list[Folder]:
    """All folders the principal may see, scoped at the query level."""
    folders = db.query(Folder).all()
    return [f for f in folders if can_view_folder(principal, user, f)]


def assert_can_view_folder(principal: Principal, user: User, folder: Folder) -> None:
    if not can_view_folder(principal, user, folder):
        # 404 to avoid leaking existence of other domains' folders.
        raise _not_found()


# --------------------------------------------------------------------------- #
# Report visibility / mutation
# --------------------------------------------------------------------------- #
def can_view_report(principal: Principal, user: User, report: Report) -> bool:
    # Drafts and in-review reports are private to their author (+ admins).
    if report.status in (
        ReportStatus.DRAFT,
        ReportStatus.IN_REVIEW,
        ReportStatus.CHANGES_REQUESTED,
    ):
        return principal.is_admin or report.owner_user_id == user.id
    # Published/archived reports inherit the visibility of their folder.
    folder = report.folder
    return can_view_folder(principal, user, folder)


def assert_can_view_report(principal: Principal, user: User, report: Report) -> None:
    if not can_view_report(principal, user, report):
        raise _not_found()


def assert_can_edit_report(principal: Principal, user: User, report: Report) -> None:
    """Only the author may edit a draft; published reports are immutable here
    (a new draft + re-publish is the governed path)."""
    if report.owner_user_id != user.id and not principal.is_admin:
        raise _not_found()
    if report.status == ReportStatus.PUBLISHED and not principal.is_admin:
        raise _forbidden("Published reports cannot be edited directly")


def assert_can_request_publish(
    principal: Principal, user: User, report: Report
) -> Domain:
    """Author requesting to publish their draft into a target domain."""
    if report.owner_user_id != user.id and not principal.is_admin:
        raise _not_found()
    if report.target_domain is None:
        raise _forbidden("Report has no target domain set")
    domain = Domain(report.target_domain)
    if not principal.can_author_in(domain) and not principal.is_admin:
        raise _forbidden(f"You are not a member of {domain.label}")
    if report.status not in (ReportStatus.DRAFT, ReportStatus.CHANGES_REQUESTED):
        raise _forbidden(f"Cannot submit a report in status '{report.status.value}'")
    return domain


def assert_can_decide_publish(principal: Principal, domain: Domain) -> None:
    """Reviewer approving/rejecting a publish request for `domain`."""
    if not principal.can_approve_for(domain):
        raise _forbidden(f"You are not an approver for {domain.label}")
