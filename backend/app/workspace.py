from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError

from .db import Audit, Notification, Product, Project, ProjectMember, User, timestamp
from .schemas import MemberInput, ProductDetails, ProductInput, ProjectInput
from .security import Actor, DB

router = APIRouter(tags=["workspace"])


def pagination(limit: Annotated[int, Query(ge=1, le=100)] = 50, offset: Annotated[int, Query(ge=0)] = 0):
    return limit, offset


Page = Annotated[tuple[int, int], Depends(pagination)]


def listing(db, query, entity, page):
    return db.scalars(query.order_by(entity.created.desc(), entity.id).limit(page[0]).offset(page[1])).all()


def accessible_projects(user):
    return select(Project.id).where(or_(
        Project.owner_id == user.id,
        Project.id.in_(select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)),
    ))


def project_for(db, key, user, owner_only=False):
    row = db.get(Project, str(key))
    member = row is not None and db.scalar(select(ProjectMember.id).where(
        ProjectMember.project_id == row.id, ProjectMember.user_id == user.id,
    ))
    if row is None or (row.owner_id != user.id and (owner_only or not member)):
        raise HTTPException(404, "Project not found")
    return row


def owned(db, entity, key, user):
    row = db.get(entity, str(key))
    if row is None:
        raise HTTPException(404, "Resource not found")
    project_for(db, row.project_id, user)
    return row


def audit(db, user, action, resource):
    db.add(Audit(user_id=user.id, action=action, resource=resource))


def add(db, user, action, row):
    db.add(row)
    db.flush()
    audit(db, user, action, row.id)
    if action in {"experiment.create", "simulation.create", "report.create"}:
        notify(db, row.project_id, {
            "experiment.create": "A new choice study is ready to configure.",
            "simulation.create": "A market scenario has been saved.",
            "report.create": "A PDF report is ready to download.",
        }[action])
    db.commit()
    db.refresh(row)
    return row


def notify(db, project_id, message):
    project = db.get(Project, project_id)
    if project is None:
        return
    recipients = {project.owner_id, *db.scalars(select(ProjectMember.user_id).where(ProjectMember.project_id == project_id))}
    db.add_all(Notification(user_id=key, project_id=project_id, message=message) for key in recipients)


def project_view(row, user):
    return {"id": row.id, "name": row.name, "description": row.description,
            "created": timestamp(row.created), "is_owner": row.owner_id == user.id}


@router.post("/projects", status_code=201)
def create_project(body: ProjectInput, db: DB, user: Actor):
    return project_view(add(db, user, "project.create", Project(owner_id=user.id, **body.model_dump())), user)


@router.get("/projects")
def projects(db: DB, user: Actor, page: Page):
    return [project_view(row, user) for row in listing(db, select(Project).where(Project.id.in_(accessible_projects(user))), Project, page)]


@router.get("/projects/{key}")
def get_project(key: UUID, db: DB, user: Actor):
    return project_view(project_for(db, key, user), user)


@router.patch("/projects/{key}")
def edit_project(key: UUID, body: ProjectInput, db: DB, user: Actor):
    row = project_for(db, key, user)
    row.name, row.description = body.name, body.description
    audit(db, user, "project.edit", row.id)
    db.commit()
    return project_view(row, user)


@router.delete("/projects/{key}", status_code=204)
def delete_project(key: UUID, db: DB, user: Actor):
    row = project_for(db, key, user, owner_only=True)
    audit(db, user, "project.delete", row.id)
    db.delete(row)
    db.commit()


def product_view(row):
    return {"id": row.id, "project_id": row.project_id, "parent_id": row.parent_id, "name": row.name, **row.attributes}


def new_product(body, project_id, parent_id=None):
    return Product(project_id=project_id, name=body.name, parent_id=parent_id, attributes=body.model_dump(exclude={"project_id", "name"}))


@router.post("/products", status_code=201)
def create_product(body: ProductInput, db: DB, user: Actor):
    project = project_for(db, body.project_id, user)
    return product_view(add(db, user, "product.create", new_product(body, project.id)))


@router.get("/products")
def products(db: DB, user: Actor, page: Page, project_id: UUID | None = None):
    query = select(Product).where(Product.project_id.in_(accessible_projects(user)))
    if project_id is not None:
        query = query.where(Product.project_id == str(project_id))
    return [product_view(row) for row in listing(db, query, Product, page)]


@router.get("/products/{key}")
def get_product(key: UUID, db: DB, user: Actor):
    return product_view(owned(db, Product, key, user))


@router.patch("/products/{key}")
def edit_product(key: UUID, body: ProductDetails, db: DB, user: Actor):
    row = owned(db, Product, key, user)
    row.name, row.attributes = body.name, body.model_dump(exclude={"name"})
    audit(db, user, "product.edit", row.id)
    db.commit()
    return product_view(row)


@router.post("/products/{key}/variants", status_code=201)
def variant(key: UUID, body: ProductDetails, db: DB, user: Actor):
    parent = owned(db, Product, key, user)
    return product_view(add(db, user, "product.variant", new_product(body, parent.project_id, parent.id)))


@router.get("/projects/{key}/members")
def members(key: UUID, db: DB, user: Actor):
    project = project_for(db, key, user, owner_only=True)
    owner = db.get(User, project.owner_id)
    rows = db.execute(select(ProjectMember, User).join(User).where(ProjectMember.project_id == project.id)).all()
    return [{"id": owner.id, "email": owner.email, "role": "owner"},
            *[{"id": member.user_id, "email": person.email, "role": "editor"} for member, person in rows]]


@router.post("/projects/{key}/members", status_code=201)
def add_member(key: UUID, body: MemberInput, db: DB, user: Actor):
    project = project_for(db, key, user, owner_only=True)
    person = db.scalar(select(User).where(User.email == body.email))
    if person is None:
        raise HTTPException(404, "Ask the collaborator to register before adding them")
    if person.id == project.owner_id:
        raise HTTPException(409, "This account already owns the project")
    db.add(ProjectMember(project_id=project.id, user_id=person.id))
    audit(db, user, "project.member.add", project.id)
    db.add(Notification(user_id=person.id, project_id=project.id, message="You have been added as a project editor."))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This account already belongs to the project") from None
    return {"id": person.id, "email": person.email, "role": "editor"}


@router.delete("/projects/{key}/members/{person}", status_code=204)
def remove_member(key: UUID, person: UUID, db: DB, user: Actor):
    project = project_for(db, key, user, owner_only=True)
    db.execute(delete(ProjectMember).where(ProjectMember.project_id == project.id, ProjectMember.user_id == str(person)))
    db.execute(delete(Notification).where(Notification.project_id == project.id, Notification.user_id == str(person)))
    audit(db, user, "project.member.remove", project.id)
    db.commit()


@router.get("/notifications")
def notifications(db: DB, user: Actor, page: Page):
    rows = listing(db, select(Notification).where(Notification.user_id == user.id,
                                                  Notification.project_id.in_(accessible_projects(user))), Notification, page)
    return [{"id": row.id, "message": row.message, "read": row.read, "created": timestamp(row.created)} for row in rows]


@router.post("/notifications/{key}/read")
def read_notification(key: UUID, db: DB, user: Actor):
    row = db.get(Notification, str(key))
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    project_for(db, row.project_id, user)
    row.read = True
    db.commit()
    return {"read": True}
