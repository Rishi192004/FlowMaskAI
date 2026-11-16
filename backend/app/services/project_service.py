"""
Project CRUD service.
"""
from __future__ import annotations

import math
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.logging import get_logger
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectUpdate

logger = get_logger(__name__)


def create_project(db: Session, payload: ProjectCreate, owner: User) -> Project:
    project = Project(
        name=payload.name,
        description=payload.description,
        domain=payload.domain,
        owner_id=owner.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    logger.info("Project created", extra={"project_id": str(project.id), "owner_id": str(owner.id)})
    return project


def get_project(db: Session, project_id: uuid.UUID, user: User) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise NotFoundError(f"Project '{project_id}' not found.")
    if project.owner_id != user.id and user.role != "admin":
        raise AuthorizationError("You do not have access to this project.")
    return project


def list_projects(
    db: Session, user: User, page: int = 1, page_size: int = 20
) -> ProjectListResponse:
    query = db.query(Project)
    if user.role != "admin":
        query = query.filter(Project.owner_id == user.id)

    total = query.count()
    items = query.order_by(Project.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    pages = math.ceil(total / page_size) if total > 0 else 0

    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


def update_project(
    db: Session, project_id: uuid.UUID, payload: ProjectUpdate, user: User
) -> Project:
    project = get_project(db, project_id, user)
    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: uuid.UUID, user: User) -> None:
    project = get_project(db, project_id, user)
    db.delete(project)
    db.commit()
    logger.info("Project deleted", extra={"project_id": str(project_id)})
